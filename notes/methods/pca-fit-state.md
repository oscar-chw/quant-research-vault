id: quant-pca-fit-state-v1
title: PCA fitted on training observations only

PCA is a fitted transform. Missing-value imputation, centering, scaling and component directions must be estimated from the training rows, then reused unchanged when transforming validation or later observations. Fitting the transform on the complete evaluation dataset leaks information about its distribution.

Retain training-row identity, cutoff, input version, fitted medians, means, scales, component vectors, retained rank and numeric precision. A code hash alone does not identify learned state. Constant features, missing values and rank-deficient inputs need an explicit policy rather than silent division by zero.

Orthogonal components and high explained variance do not establish useful forecasts. Compare the downstream model with an appropriate baseline on later observations. The cited fold implementation and its training-only test provide a concrete example, with its own dtype and numerical limits.
