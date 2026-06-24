# Photo alignment

Articles on the *Align Photos* step of the photogrammetry pipeline —
how to diagnose alignment failures, choose the right preselection mode,
clean up tie points, and recover from common failure patterns.

For Metashape's own definition of alignment terms, see
[the glossary](../../reference/glossary.md).

## Articles

- [Pair preselection: Disabled, Generic, or Reference?](pair-preselection-modes.md)
- [Helping alignment when photos don't align: markers, references, and what to use when](helping-alignment.md)
- [Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md)
- [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md)
- [Adding cameras to an aligned chunk: the `keep_keypoints` workflow](incremental-matching-keep-keypoints.md)
- [AI-assisted mask generation](ai-mask-generation.md)
- [Automatic sky masking with ONNX: pre-clean for sky-prone aerial captures](automatic-sky-masking.md)
- [`mask_tiepoints` cross-view propagation and the foreground-occluder case](mask-tiepoints-cross-view.md)
- [`filter_mask=True` starves matchPhotos when masks cover most of the image](filter-mask-starvation.md)
- [Exclude stationary tie points: when and why](stationary-point-filter.md)
- [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
- [`alignChunks(method=point)` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md)

## Related feature pages

- [Gradual selection](../../reference/features/gradual-selection.md)
- [Guided matching](../../reference/features/guided-matching.md)

## Coverage

This section is being built incrementally.
