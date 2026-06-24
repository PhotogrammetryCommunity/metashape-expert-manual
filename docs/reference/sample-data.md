# Agisoft sample datasets

Agisoft hosts ten free sample datasets at
<https://www.agisoft.com/downloads/sample-data/>. Each ships as a `.zip`
on `download.agisoft.com`. They cover representative capture scenarios
and are the canonical material to validate procedures against and to
illustrate articles in this manual.

Use them when you can. Hand-rolled or contributor-private datasets are
fine if a sample doesn't fit the article, but a sample-data validation
is reproducible by any reader.

## Quick reference

| Dataset | Volume | Best illustrates |
|---------|--------|------------------|
| [Witcher](#witcher) | 239 images | Close-range / turntable, background-mask workflows |
| [Building](#building) | 50 images | Terrestrial facade modelling, planar orthomosaic |
| [Coded targets](#coded-targets) | 6 images, 3 targets | Marker-based scaling, *Detect Markers* |
| [Aerial images (with GCPs)](#aerial-images-with-gcps) | 444 images, 18 GCPs | UAV workflow, georeferencing, GNSS offset, GCP optimisation |
| [Aerial LiDAR](#aerial-lidar) | 148M points + trajectory | Aerial LiDAR + photogrammetry fusion, classification |
| [Terrestrial LiDAR](#terrestrial-lidar) | 9 E57 scans + panoramas | Terrestrial laser-scan workflows, scan registration |
| [Spherical panorama (single)](#spherical-panorama) | 73 images | Single-station panorama generation |
| [Spherical panoramas (interior)](#spherical-panoramas-interior) | 9 panoramas | Interior modelling from panoramas |
| [Depth images](#depth-images) | 29 images | iPad-Pro depth-sensor capture, RGB+depth fusion |
| [Interior](#interior) | 391 images | Indoor capture, low-feature surfaces |

## Naming this manual uses

- "the Witcher dataset" → the close-range turntable set
- "the Building dataset" → the terrestrial facade set
- "the Coded targets dataset" → the markers/scaling set
- "the Aerial-with-GCPs dataset" → the 444-image UAV set
- "the Aerial LiDAR dataset" → the airborne lidar set
- "the Terrestrial LiDAR dataset" → the ground-based lidar set
- "the Spherical-panorama dataset" → the single-station 73-image set
- "the Spherical-panoramas dataset" → the 9-panorama interior set
- "the Depth-images dataset" → the iPad Pro set
- "the Interior dataset" → the 391-image indoor set

When citing a dataset for the first time in an article, link to the
section anchor below; subsequent references can use the short name.

---

## Witcher {#witcher}

> Close-range images taken with a turntable with a background image for
> masks generation. **239 images.**
> Download: <https://download.agisoft.com/datasets/the_witcher.zip>

**Best illustrates**

- Turntable / close-range object capture
- Masks generated from a background image (*Tools → Import Masks → From Background*)
- Aligning images that share a moving foreground over a static background

**Used by**

- [Exclude stationary tie points: when and why](../workflow/alignment/stationary-point-filter.md)
- Scale-bar-free workflows where measurement matters less than topology

**Articles in this manual**

- *(none yet — link from the next article that uses it.)*

## Building {#building}

> Terrestrial images for facade 3D model and planar orthomosaic
> generation. **50 images.**
> Download: <https://download.agisoft.com/datasets/building.zip>

**Best illustrates**

- Terrestrial / non-aerial photogrammetry
- Planar (vertical-projection) orthomosaic generation
- Mesh quality on man-made flat surfaces
- A small, fast-converging alignment for tooling smoke tests

**Articles in this manual**

- *(none yet)*

## Coded targets {#coded-targets}

> Images with coded targets to scale a model. **6 images, 3 targets.**
> Download: <https://download.agisoft.com/datasets/coded.zip>

**Best illustrates**

- *Detect Markers* with coded targets
- Scale-bar definition and measurement
- Marker-based georeferencing without GCPs
- The minimum useful project size (6 images)

**Articles in this manual**

- [Removing "blue flag" marker projections cleanly](../workflow/markers-gcps/removing-blue-flag-marker-projections.md)
  — uses the Coded targets dataset to demonstrate the bulk-removal
  pattern after `chunk.detectMarkers()`.
- [Programmatic marker placement and pinning](../workflow/markers-gcps/programmatic-marker-placement.md)
  — uses the Coded targets dataset to demonstrate that all three
  `Marker.Projection` constructor input forms (`Vector`, list,
  tuple) produce equivalent projections.

## Aerial images (with GCPs) {#aerial-images-with-gcps}

> Aerial images with GCPs and GNSS offset, including separate CSV file
> with camera coordinates. **444 images, 18 GCPs.**
> Download: <https://download.agisoft.com/datasets/aerial_images_with_gcps.zip>

**Best illustrates**

- UAV photogrammetry pipeline end-to-end
- Reference Preselection with geotagged photos
- GCP import, marker placement, and Optimize Cameras after GCPs
- GNSS antenna offset handling
- Reference-pane CRS configuration

**Articles in this manual**

- [The Clean Tie Points → Optimize Cameras loop](../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — uses Aerial-with-GCPs (or Building as a faster alternative) to
  demonstrate the alignment + cleanup-loop scripted end-to-end.
- [Reproducing chunk-info statistics in Python](../topics/repeatability-qa/reproducing-chunk-info-statistics-python.md)
  — uses Aerial-with-GCPs (georeferenced, has 18 GCPs) to
  demonstrate all three chunk-info formulae and verify them against
  the GUI display.
- [Setting `chunk.region` to bound the tie-point cloud](../workflow/project-setup/setting-the-chunk-region.md)
  — uses Aerial-with-GCPs to demonstrate the simple internal-
  coordinates region resize after alignment.
- [Exporting depth maps from Python (32-bit, scaled)](../workflow/depth-maps/exporting-depth-maps-python.md)
  — uses Aerial-with-GCPs to demonstrate the float32 export with
  `chunk.transform.scale` applied.

## Aerial LiDAR {#aerial-lidar}

> Aerial LiDAR point cloud with trajectory data. **148 million points,
> 1 trajectory file.**
> Download: <https://download.agisoft.com/datasets/aerial_lidar.zip>

**Best illustrates**

- LiDAR import and trajectory alignment
- Point cloud classification (*Tools → Classify Points…*)
- Filter by Class / Filter by Return / Filter by Confidence
- Memory-bound workflows (148 M points is non-trivial on consumer hardware)

**Articles in this manual**

- *(none yet)*

## Terrestrial LiDAR {#terrestrial-lidar}

> Terrestrial laser scans with built-in panoramas. **9 scans in E57
> format.**
> Download: <https://download.agisoft.com/datasets/terrestrial_lidar.zip>

**Best illustrates**

- E57 import workflows
- Laser-scan registration and *Align Laser Scans*
- Panorama-from-scan colourisation
- Scan-vs-photo hybrid alignment

**Articles in this manual**

- *(none yet)*

## Spherical panorama {#spherical-panorama}

> Images taken from single point for panorama generation. **73 images.**
> Download: <https://download.agisoft.com/datasets/pano.zip>

**Best illustrates**

- Single-station panorama generation
- Stitching from a non-spherical capture rig
- *Workflow → Build Panorama*

**Articles in this manual**

- *(none yet)*

## Spherical panoramas (interior) {#spherical-panoramas-interior}

> Spherical panoramas for interior modeling. **9 spherical panoramas.**
> Download: <https://download.agisoft.com/datasets/spherical_panoramas.zip>

**Best illustrates**

- Interior reconstruction from spherical panoramas
- Spherical camera type configuration
- Multi-station alignment in a confined space

**Articles in this manual**

- *(none yet)*

## Depth images {#depth-images}

> Images from front camera of iPad pro with a depth sensor. **29
> images.**
> Download: <https://download.agisoft.com/datasets/depth_images.zip>

**Best illustrates**

- Depth-sensor + RGB fusion
- iPad / mobile capture pipelines
- Pre-existing depth maps fed into the photogrammetry pipeline

**Articles in this manual**

- *(none yet)*

## Interior {#interior}

> Terrestrial images for interior modeling. **391 images.**
> Download: <https://download.agisoft.com/datasets/interior.zip>

**Best illustrates**

- Indoor capture with low-feature surfaces (walls, floors)
- Multi-room alignment without GPS
- Lighting variation across rooms

**Articles in this manual**

- *(none yet)*

---

## Maintenance

This page is hand-maintained. When you write an article that uses one
of these datasets:

1. Add a one-line entry under that dataset's *Articles in this manual*
   section linking to the article.
2. In the article, link the dataset by its anchor here on first
   mention.
3. Captions on dataset-derived screenshots should name the dataset and
   the Metashape version (per [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md)).

Adding a new dataset (if Agisoft publishes more): copy the section
template above, add a row to the *Quick reference* table, and add the
short name to the *Naming this manual uses* list.
