# Texture

Articles in this cluster cover Metashape's texture-generation
behaviour: the algorithms behind `Chunk.buildTexture`, the
parameters and modes that affect output, and the version
transitions that have changed default behaviour over time.

## Articles

- [Color calibration: when to use it, what it does, and the white-balance / vignetting knobs](color-calibration.md)
- [Texture in Metashape 2.3 — what changed and why your scripts may need updating](texture-in-2-3-changes.md)
- [Texture blending modes — what each one actually does](blending-modes.md)

## Cluster contents

- [**Texture in Metashape 2.3 — what changed and why your
  scripts may need updating**](texture-in-2-3-changes.md) —
  the 2.3 API additions (Natural blending, new kwargs,
  changed defaults) and the script-compatibility implications.
- [**Texture blending modes — what each one actually does**](blending-modes.md) —
  Tier 3 empirical comparison of the five `BlendingMode` values
  available on 2.2.x (and 2.3.x without Natural). Reveals that
  `MaxBlending` and `MinBlending` select *whole images* by
  intensity rather than computing per-channel max / min, and
  that the Average mode's histogram is a useful registration-
  quality diagnostic.

## See also

- The Mesh cluster ([Vertex normal computation](../mesh/vertex-normal-computation.md))
  for another Tier 3 reproducer using the same single-script
  experimental pattern.
- The three-tier verification model these articles follow:
  Tier 1 (scripts) → Tier 2 (automated review) → Tier 3 (a human
  on a real install).
