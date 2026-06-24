---
title: "Custom vertical datums: adding a geoid undulation grid"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same geoids folder mechanism
edition: "Pro / Standard"
last_reviewed: 2026-06-04
diataxis: how-to
confidence: high
---

# Custom vertical datums: adding a geoid undulation grid

> **Confidence:** *high.* The official freshdesk tutorial covers
> the workflow; the additions in this article (the `DESC` name
> collision pitfall, the file-format gotchas) come from forum
> threads with permalinks.

## Problem

Your project's vertical reference is a national geoid that is
not bundled with Metashape (e.g., a regional German `DHHN2016`
variant, a national French `RAF20`, or any sub-national
authority's geoid grid). You have the official undulation grid
file, but Metashape does not show it in the *Coordinate System*
dialog's vertical-datum list.

## Context

Metashape's bundled geoids cover the major national datums
(EGM96 / EGM2008, WGS84-based regional offsets, etc.) but not
every sub-national or specialised geoid. Custom geoids are
loaded from TIFF undulation grids placed in the user's `geoids/`
folder, with the geoid name carried in the TIFF's `DESC` metadata
field.

## Solution

### 1. Obtain the undulation grid

Download the official TIFF from the relevant national mapping
authority (e.g., Germany's *Bundesamt für Kartographie und
Geodäsie*; France's *IGN*; the US *NGS*).

The file must be a **GeoTIFF in geographic coordinates** (lat /
lon) where each pixel value is the geoid–ellipsoid offset in
metres.

> **Other grid formats:** the drop-in `geoids/` folder method
> here expects a GeoTIFF. If your undulation grid is in another
> format (ASCII Grid `.grd`, AUSGeoid `.dat`/`.txt`, NGS `.bin`,
> NRCan `.byn`, Trimble `.ggf`, Carlson `.gsf`, ISG, French
> `.mnt`, Sideris, or a lat/lon/alt table), load it instead
> through the *Coordinate System* dialog's *Vertical CS → Custom
> → Add…* datum option, which accepts all of these — see the
> [*Reference links and description for supported Geoids formats* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000155544).

### 2. Verify the `DESC` metadata field

Metashape uses the TIFF's `DESC` (description) field as the
geoid name in the *Coordinate System* dialog. Inspect with:

```bash
# Using GDAL command-line tools
gdalinfo /path/to/your_geoid.tif | grep -i "tiff_desc\|description"
```

If the `DESC` field is empty or wrong, set it:

```bash
gdal_edit.py -mo TIFF_DESC="MyCountry National Geoid 2024" /path/to/your_geoid.tif
```

The name you set will appear in Metashape's CRS picker.

### 3. Place the file in the geoids folder

The folder location depends on the operating system:

| OS | Path |
|----|------|
| **macOS** | `~/Library/Application Support/Agisoft/Metashape Pro/geoids/` |
| **Linux** | `~/.local/share/Agisoft/Metashape Pro/geoids/` |
| **Windows** | `%LOCALAPPDATA%\Agisoft\Metashape Pro\geoids\` |

Create the directory if it does not exist. Copy the TIFF in.

### 4. Restart Metashape

Metashape scans the `geoids/` folder at startup. Any new files
become available in the *Coordinate System* dialog as vertical
datums.

### 5. Create a compound CRS

In *Reference → Reference Settings → Coordinate System*, build a
compound CRS combining your horizontal datum (e.g., ETRS89 / UTM
zone 32N, EPSG:25832) with the new geoid as the vertical datum.

The compound system is selectable from the *More…* tab of the
CRS dialog after the geoid file is detected.

## Common pitfalls

### `DESC` name collision

If two undulation files in the geoids folder share the **same
`DESC` name** (e.g., one downloaded from Agisoft and one created
locally with a generic name), Metashape silently uses the first
one it scans. The result: the geoid you intended to use is
shadowed by another file with identical metadata.

**Symptom.** Your custom geoid appears in the CRS picker, but
exported elevations differ from what your reference data
predicts.

**Fix.** Ensure each TIFF in `geoids/` has a unique `DESC` name
via `gdal_edit.py -mo TIFF_DESC="..."`. List existing names with:

```bash
for f in ~/Library/Application\ Support/Agisoft/Metashape\ Pro/geoids/*.tif; do
    echo -n "$(basename $f): "
    gdalinfo "$f" | grep -i "tiff_desc" | head -1
done
```

### Wrong coordinate reference

The TIFF must be in **geographic coordinates** matching the
horizontal datum's coverage area. A projected-coordinate TIFF
(e.g., UTM-zone-projected pixels) will load but produce wrong
offsets — Metashape interpolates between cells assuming
geographic axes.

### Missing pixels at extremes

If your geoid file does not cover the full project extent (a
national-grid TIFF used at coastal or border areas), Metashape
silently uses zero offset for points outside the TIFF coverage.
Verify by sampling the corners of your project area against the
TIFF in QGIS.

## Caveats

- **Resolution determines accuracy.** A 1° × 1° geoid grid
  interpolates over ~110 km cells, which produces ±10–30 cm
  vertical accuracy in lowland areas. Sub-degree grids (e.g., 1′
  × 1′) deliver sub-cm accuracy.
- **Sign convention.** Metashape expects pixel values in
  metres, with positive values where the geoid is above the
  ellipsoid. Some national grids ship with the opposite sign;
  check your authority's documentation and flip if needed.
- **Compound CRS persistence.** The compound CRS you create is
  stored in the project file. Sharing a project with a custom
  geoid requires the recipient to also have the geoid file in
  their `geoids/` folder, or the project's vertical datum will
  be unavailable.

## References

- [*How to use height above geoid for the coordinate system* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148332)
  — the official tutorial.
- *Metashape Pro User Manual* (2.3) §
  *Coordinate Systems → Vertical Datum* — describes the compound
  CRS workflow.
- Forum thread, [*Can't load local geoid model into metashape*, 2020](https://www.agisoft.com/forum/index.php?topic=12602.msg66936#msg66936)
  — community-attested origin of the `DESC` name-collision
  warning (2020-10-12).

## See also

- [*What to do if you need to use an existing geoid on another datum* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161533)
  — datum-shifting an undulation grid (e.g. GDA94 → GDA2020) via
  *Transform DEM* before building a compound CRS.
- [Drone metadata: DJI altitude semantics and RTK XMP accuracy tags](dji-drone-metadata.md)
- [Change Path: swapping image format / resolution after alignment](change-path-and-export-coords.md)
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../../topics/crs/chunk-frame-vs-camera-frame.md)

