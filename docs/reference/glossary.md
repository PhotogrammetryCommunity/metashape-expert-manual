# Glossary

Short, neutral definitions of Metashape-specific terms as they are used in
this manual. Where Metashape's terminology has changed across versions, the
current (2.x) term is the entry head and the historical term is noted.

This glossary is a stub. Entries are added as articles introduce terminology
that needs a precise shared definition.

## Tie point cloud
The sparse point cloud produced by photo alignment, before depth-map
computation. Each tie point is observed in multiple cameras.

## Point cloud
A dense point cloud computed from depth maps. **Renamed in 2.x.** In 1.x this
was called *dense cloud*; the GUI command was *Build Dense Cloud*.

## Depth maps
Per-camera distance images produced from a set of overlapping photos. The
intermediate product between alignment and a point cloud or mesh in the
default 2.x pipeline.

## Chunk
A self-contained block of cameras, markers, and reconstructed products
within a Metashape *document*. Multiple chunks can be aligned together and
merged.

## Marker
A user-placed control point referenced in the project. Can be a Ground
Control Point (GCP), a check point, or simply a feature reference.

## Optimization (camera)
The bundle-adjustment step that refines camera poses and intrinsics after
alignment, typically combined with *Gradual Selection* of tie points.
