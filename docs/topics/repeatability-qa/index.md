# Repeatability and QA

Cross-cutting topic: making Metashape projects reproducible and
auditable — same dataset, same parameters, same numbers — and
extracting from them the metrics a quality-assurance process can
gate on.

## Articles

- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md)
- [Keypoint-size-normalised reprojection error: the kps metric](keypoint-size-error-metric.md)
- [Tie-point multiplicity: track length, distribution, and what it tells you](tie-point-multiplicity.md)
- [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md)
- [Marker projection statistics: counts, per-marker errors, metres vs pixels](marker-projection-statistics.md)
- [Scalebar distance error: per-scalebar values and RMS aggregation](scalebar-error-statistics.md)
- [Camera reference error: per-camera location & orientation in Python](camera-reference-error-python.md)
- [Sensor and camera shared-tie-point graphs: detecting isolated groups](shared-tie-point-graphs.md)
- [DSM ridge-line artefacts: alignment-quality diagnosis](dsm-ridge-lines-diagnosis.md)
- [Saving estimated reference values to file: location, rotation, error, and sigma](save-estimated-reference.md)
- [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](bundle-adjustment-quality.md)

## Coverage

This section reproduces every chunk-info statistic the GUI
displays plus several derived QA metrics that aren't shown
directly. Together they let a Python script reproduce the
*Survey Data* / *Cameras* / *Reference* pages of a Metashape
PDF report and compute additional quality gates beyond it.
