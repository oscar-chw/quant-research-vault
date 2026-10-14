id: quant-pit-cutoffs-v1
title: Point-in-time availability and causal evaluation

A timestamp describing the market event is not necessarily the time a researcher could use it. A historical view must apply the declared availability cutoff, retain source identity and preserve later corrections as separate versions. A decision made at time t may use only observations available by t.

Freeze the dataset version, decision clock, label interval and cost assumptions before evaluation. Inspect boundary cases at the cutoff, missing observations and revisions. History reused by multiple estimators is not automatically future leakage; fitting on unavailable information or selecting with later evaluation outcomes is the problem.

A reproducible result names its inputs and clock conventions. Passing these data checks supports causal access, not predictive skill or profitable trading. The cited public implementation and tests illustrate the boundary on their stated data scope.
