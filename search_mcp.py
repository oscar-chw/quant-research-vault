#!/usr/bin/env python3
"""
search_mcp.py — MCP server for semantic search over the quant research vault.

Exposes eight tools:
  - search_papers(query, n_results)         semantic search over summaries
  - list_recent_papers(days)                papers added in last N days
  - get_paper(arxiv_id)                     full summary for a specific paper
  - generate_alpha_ideas(topic, n_papers)   AI-generated alpha ideas from vault
  - get_vault_stats()                       total papers, date range, index size
  - search_shared_notes(query, limit)       legacy pinned method-note envelopes
  - search_shared_notes_report(query, limit) traceable lexical evidence/status
  - verify_shared_notes_report(report)      saved response/source consistency

The ChromaDB index is built/updated by sync.py. This server is read-only.

Usage (as MCP server — Claude Code calls this automatically):
    python search_mcp.py

Usage (test):
    python search_mcp.py --test "momentum crypto"
"""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import chromadb
import yaml
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

import shared_notes

CONFIG_PATH = Path(__file__).parent / "config.yaml"

# ── Single-instance lock ──────────────────────────────────────────────────────
# Prevents Claude Code's retry loop from spawning hundreds of server processes.
_LOCK_FILE = Path(tempfile.gettempdir()) / "quant_research_mcp.lock"


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform liveness check. Uses psutil when available."""
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:
        pass
    # Unix fallback: signal 0 = check only, no signal sent
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    # Windows without psutil — assume stale
    return False


def _acquire_lock() -> bool:
    """Return True if we are the only running instance. Exit-safe."""
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            if _is_pid_alive(pid):
                # Another instance is running
                return False
            # Stale lock
            _LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            _LOCK_FILE.unlink(missing_ok=True)
    try:
        _LOCK_FILE.write_text(str(os.getpid()))
    except Exception:
        pass
    return True


def _release_lock() -> None:
    _LOCK_FILE.unlink(missing_ok=True)


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["vault_path"] = str(Path(cfg["vault_path"]).expanduser())
    # Claude Code starts this server from the user's project folder, so ".db/..." must be
    # anchored to the config file, not the cwd, or the search runs on an empty index.
    for key in ("db_path", "chroma_path"):
        cfg[key] = str(CONFIG_PATH.parent / Path(cfg[key]).expanduser())
    return cfg


def get_collection(cfg: dict) -> chromadb.Collection:
    """Open ChromaDB with retry on transient lock errors."""
    chroma_path = cfg["chroma_path"]
    for attempt in range(3):
        try:
            client = chromadb.PersistentClient(path=chroma_path)
            return client.get_or_create_collection(
                name="quant_papers",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(
                    f"ChromaDB unavailable after 3 attempts: {exc}"
                ) from exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("ChromaDB unavailable")  # unreachable


def get_db(cfg: dict) -> sqlite3.Connection:
    conn = sqlite3.connect(cfg["db_path"], timeout=10)
    return conn


# ── Tool implementations ──────────────────────────────────────────────────────


class SearchBackendError(RuntimeError):
    """A safe failure when the paper vector-search backend is unavailable."""


def search_papers(
    collection: chromadb.Collection, query: str, n_results: int = 5
) -> list[dict]:
    if not isinstance(query, str):
        raise ValueError("query must be text")
    if type(n_results) is not int or n_results < 1:
        raise ValueError("n_results must be a positive integer")
    n_results = min(n_results, 10)
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        raise SearchBackendError(
            "paper search failed: vector backend unavailable"
        ) from None

    papers = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        papers.append(
            {
                "arxiv_id": meta.get("arxiv_id"),
                "title": meta.get("title"),
                "categories": meta.get("categories"),
                "published": meta.get("published"),
                "relevance_score": round(1 - dist, 3),
                "vault_path": meta.get("vault_path"),
                "summary_excerpt": doc[:500] + "..." if len(doc) > 500 else doc,
            }
        )
    return papers


def list_recent_papers(conn: sqlite3.Connection, days: int = 7) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT arxiv_id, title, categories, published, vault_path
        FROM papers
        WHERE processed = 1 AND fetched_at > ?
        ORDER BY published DESC
        LIMIT 20
    """,
        (cutoff,),
    ).fetchall()
    return [
        {
            "arxiv_id": r[0],
            "title": r[1],
            "categories": json.loads(r[2]) if r[2] else [],
            "published": r[3][:10],
            "vault_path": r[4],
        }
        for r in rows
    ]


def get_paper_summary(cfg: dict, arxiv_id: str) -> str | None:
    conn = get_db(cfg)
    row = conn.execute(
        "SELECT vault_path FROM papers WHERE arxiv_id = ? AND processed = 1",
        (arxiv_id,),
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return None
    path = Path(row[0])
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def generate_alpha_ideas_text(
    collection: chromadb.Collection,
    cfg: dict,
    topic: str,
    n_papers: int = 6,
) -> str:
    """Return relevant paper excerpts for alpha idea generation.

    NOTE: We deliberately do NOT spawn a claude subprocess here.
    The MCP caller (Claude Code) is already an LLM — return the raw
    context and let it synthesize alpha ideas directly. Spawning a
    child claude process from inside the MCP server would create
    uncontrolled node.js process accumulation.
    """
    count = collection.count()
    if count == 0:
        return "ChromaDB index is empty. Run `python run.py` to build it first."

    results = collection.query(
        query_texts=[topic],
        n_results=min(n_papers, count),
        include=["documents", "metadatas"],
    )

    lines = [
        f"## Vault Context for Alpha Ideas: '{topic}'\n",
        f"Found {len(results['documents'][0])} relevant papers. "
        f"Synthesize 3 specific alpha ideas from this context:\n",
    ]

    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        arxiv_id = meta.get("arxiv_id", "")
        title = meta.get("title", "")
        vault_path = meta.get("vault_path", "")
        content = doc[:2000]

        if vault_path:
            vp = Path(vault_path)
            if vp.exists():
                content = vp.read_text(encoding="utf-8")[:2000]

        lines.append(f"### {title} ({arxiv_id})\n{content}\n")

    return "\n---\n".join(lines)


def get_vault_stats_text(cfg: dict, collection: chromadb.Collection) -> str:
    """Return vault statistics as a formatted string."""
    conn = get_db(cfg)
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    processed = conn.execute(
        "SELECT COUNT(*) FROM papers WHERE processed = 1"
    ).fetchone()[0]
    date_range = conn.execute(
        "SELECT MIN(published), MAX(published) FROM papers"
    ).fetchone()
    conn.close()

    min_date = (date_range[0] or "")[:10]
    max_date = (date_range[1] or "")[:10]
    index_size = collection.count()

    return (
        f"Quant Research Vault Statistics\n"
        f"================================\n"
        f"Total papers in DB    : {total:,}\n"
        f"Processed papers      : {processed:,}\n"
        f"ChromaDB index size   : {index_size:,}\n"
        f"Date range            : {min_date} to {max_date}\n"
    )


# ── MCP server ────────────────────────────────────────────────────────────────


def build_server() -> Server:
    cfg = load_config()
    collection = get_collection(cfg)
    conn = get_db(cfg)

    async def list_tools(_context, _params) -> types.ListToolsResult:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name="verify_shared_notes_report",
                    description=(
                        "Verify a saved method-note retrieval response against its pinned sources and "
                        "current v1 lexical policy. This checks consistency, not author identity or relevance."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {"report": {"type": "object"}},
                        "required": ["report"],
                    },
                ),
                types.Tool(
                    name="search_shared_notes_report",
                    description=(
                        "Trace literal shared-note matches to exact source excerpts and pinned citations. "
                        "Reports matched, partial, no_match, stale or error; term coverage is not semantic confidence."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 20,
                                "default": 5,
                            },
                            "manifest_sha256": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="search_shared_notes",
                    description=(
                        "Search the vault's separately curated, hash-verified original method notes. "
                        "These are method notes, not arXiv papers."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Terms to find in method notes.",
                            },
                            "limit": {"type": "integer", "default": 5},
                            "manifest_sha256": {
                                "type": "string",
                                "description": "Optional exact SHA256 pin for notes/manifest.json.",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="search_papers",
                    description=(
                        "Semantic search over quant finance research papers in the vault. "
                        "Returns the most relevant papers for a given query. "
                        "Use for: finding papers on a specific alpha factor, technique, or market, "
                        "before engineering features or designing strategies."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query, e.g. 'momentum factor in crypto', 'volatility prediction LSTM'",
                            },
                            "n_results": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5, max: 10)",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="list_recent_papers",
                    description="List quant finance papers added to the vault in the last N days.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "How many days back to look (default: 7)",
                                "default": 7,
                            },
                        },
                    },
                ),
                types.Tool(
                    name="get_paper",
                    description="Get the full structured summary for a specific paper by arXiv ID.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "arxiv_id": {
                                "type": "string",
                                "description": "arXiv paper ID, e.g. '2601.12345' or '2601.12345v2'",
                            },
                        },
                        "required": ["arxiv_id"],
                    },
                ),
                types.Tool(
                    name="generate_alpha_ideas",
                    description=(
                        "Search the vault for research papers relevant to a topic and return their "
                        "excerpts as context for drafting alpha ideas. This server calls no model; "
                        "the calling assistant drafts the ideas."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The trading topic to generate ideas for, e.g. 'crypto momentum', 'volatility arbitrage'",
                            },
                            "n_papers": {
                                "type": "integer",
                                "description": "Number of vault papers to use as context (default: 6, max: 10)",
                                "default": 6,
                            },
                        },
                        "required": ["topic"],
                    },
                ),
                types.Tool(
                    name="get_vault_stats",
                    description=(
                        "Get statistics about the quant research vault: total papers, "
                        "processed count, date range covered, and ChromaDB index size."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]
        )

    async def call_tool(_context, params: types.CallToolRequestParams):
        name = params.name
        arguments = params.arguments or {}
        if name == "search_papers":
            query = arguments["query"]
            n = arguments.get("n_results", 5)
            try:
                results = search_papers(collection, query, n)
            except ValueError as exc:
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Error: {exc}.")],
                    isError=True,
                )
            except SearchBackendError:
                text = "Error: paper search backend unavailable."
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=text)], isError=True
                )
            if not results:
                text = f"No papers found matching '{query}'. Run `python run.py` to fetch and index papers first."
            else:
                lines = [f"Found {len(results)} papers matching '{query}':\n"]
                for r in results:
                    lines.append(
                        f"**[{r['relevance_score']:.2f}] {r['title']}**\n"
                        f"arXiv: {r['arxiv_id']} | {r['published'][:10]} | {r['categories']}\n"
                        f"{r['summary_excerpt']}\n"
                    )
                text = "\n---\n".join(lines)

        elif name == "verify_shared_notes_report":
            verification = shared_notes.verify_shared_notes_report(
                arguments.get("report")
            )
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(verification, ensure_ascii=False, indent=2),
                    )
                ],
                isError=verification["status"] != "verified",
            )

        elif name == "search_shared_notes_report":
            report = shared_notes.search_shared_notes_report(
                arguments.get("query"),
                limit=arguments.get("limit", 5),
                expected_manifest_sha256=arguments.get("manifest_sha256"),
            )
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(report, ensure_ascii=False, indent=2),
                    )
                ],
                isError=report["status"] in {"stale", "error"},
            )

        elif name == "search_shared_notes":
            try:
                notes = shared_notes.search_shared_notes(
                    arguments["query"],
                    limit=arguments.get("limit", 5),
                    expected_manifest_sha256=arguments.get("manifest_sha256"),
                )
            except shared_notes.SharedNotesError as exc:
                text = f"Error: shared-note {exc}."
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=text)], isError=True
                )
            else:
                text = json.dumps(notes, ensure_ascii=False, indent=2)

        elif name == "list_recent_papers":
            days = int(arguments.get("days", 7))
            papers = list_recent_papers(conn, days)
            if not papers:
                text = f"No papers processed in the last {days} days."
            else:
                lines = [f"{len(papers)} papers added in the last {days} days:\n"]
                for p in papers:
                    lines.append(
                        f"- **{p['title']}** ({p['arxiv_id']}) — {p['published']}"
                    )
                text = "\n".join(lines)

        elif name == "get_paper":
            arxiv_id = arguments["arxiv_id"]
            summary = get_paper_summary(cfg, arxiv_id)
            text = (
                summary
                if summary
                else f"Paper {arxiv_id} not found or not yet processed."
            )

        elif name == "generate_alpha_ideas":
            topic = arguments["topic"]
            n_papers = min(int(arguments.get("n_papers", 6)), 10)
            text = generate_alpha_ideas_text(collection, cfg, topic, n_papers)

        elif name == "get_vault_stats":
            text = get_vault_stats_text(cfg, collection)

        else:
            text = f"Unknown tool: {name}"

        return types.CallToolResult(content=[types.TextContent(type="text", text=text)])

    return Server("quant-research", on_list_tools=list_tools, on_call_tool=call_tool)


async def run_server() -> None:
    server = build_server()
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    finally:
        _release_lock()


# ── CLI test mode ─────────────────────────────────────────────────────────────


def test_search(query: str) -> None:
    cfg = load_config()
    collection = get_collection(cfg)
    try:
        results = search_papers(collection, query)
    except SearchBackendError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if not results:
        print("No results. Have you run `python run.py` yet?")
        return
    for r in results:
        print(f"\n[{r['relevance_score']:.2f}] {r['title']}")
        print(f"  arXiv: {r['arxiv_id']} | {r['published'][:10]}")
        print(f"  {r['summary_excerpt'][:200]}...")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", metavar="QUERY", help="Test search without MCP")
    parser.add_argument(
        "--shared-note",
        metavar="ID",
        help="Print one verified shared method note as JSON",
    )
    parser.add_argument(
        "--shared-query",
        metavar="QUERY",
        help="Search the separately curated method notes",
    )
    parser.add_argument(
        "--shared-root",
        type=Path,
        default=shared_notes.DEFAULT_SHARED_NOTES_ROOT,
        help="Notes directory containing manifest.json (default: this checkout's notes/)",
    )
    parser.add_argument(
        "--manifest-sha256", help="Require this exact shared manifest SHA256"
    )
    args = parser.parse_args()

    if args.shared_note or args.shared_query:
        try:
            if args.shared_note:
                notes = shared_notes.load_shared_notes(
                    args.shared_root,
                    expected_manifest_sha256=args.manifest_sha256,
                )
                notes = [
                    note for note in notes if note["document_id"] == args.shared_note
                ]
            else:
                notes = shared_notes.search_shared_notes(
                    args.shared_query,
                    root=args.shared_root,
                    expected_manifest_sha256=args.manifest_sha256,
                )
        except shared_notes.SharedNotesError as exc:
            parser.exit(1, f"shared-note error: {exc}\n")
        if args.shared_note and not notes:
            parser.exit(
                1, f"shared-note error: document id not found: {args.shared_note}\n"
            )
        output = notes[0] if args.shared_note else notes
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.test:
        test_search(args.test)
    else:
        # Refuse to start if another instance is already running.
        # This stops Claude Code's retry loop from creating process storms.
        if not _acquire_lock():
            sys.stderr.write(
                "quant-research MCP: another instance already running, exiting.\n"
            )
            sys.exit(0)  # exit 0 so Claude Code does NOT retry
        try:
            asyncio.run(run_server())
        except Exception as exc:
            sys.stderr.write(f"quant-research MCP fatal: {exc}\n")
            _release_lock()
            sys.exit(0)  # exit 0, not 1 — prevents infinite retry loop
