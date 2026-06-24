"""Compare alignment with/without stationary-point filtering.

Dataset: Agisoft 'Witcher' sample (239 turntable images).
Download: https://download.agisoft.com/datasets/the_witcher.zip

Usage:
    python scripts/verify_stationary_filter.py /path/to/the_witcher/

Requires an activated Metashape Python module.

Expected outcome:
    - With filter (default): fewer tie points, cleaner alignment.
    - Without filter: more tie points (including background matches),
      potentially degraded or unchanged alignment depending on the
      strength of the background texture.
"""
import sys, pathlib
import Metashape


def run_alignment(image_dir: pathlib.Path, filter_stationary: bool,
                  tiepoint_limit: int) -> dict:
    """Run matchPhotos + alignCameras and return statistics."""
    doc = Metashape.Document()
    chunk = doc.addChunk()

    images = sorted(str(p) for p in image_dir.glob("*.jpg"))
    if not images:
        images = sorted(str(p) for p in image_dir.glob("*.JPG"))
    if not images:
        raise FileNotFoundError(f"No .jpg/.JPG images in {image_dir}")
    chunk.addPhotos(images)
    print(f"  Cameras loaded: {len(chunk.cameras)}")

    chunk.matchPhotos(
        downscale=1,
        generic_preselection=True,
        reference_preselection=False,
        filter_stationary_points=filter_stationary,
        keypoint_limit=40000,
        tiepoint_limit=tiepoint_limit,
    )
    chunk.alignCameras()

    aligned = sum(1 for c in chunk.cameras if c.transform is not None)
    n_points = len(chunk.tie_points.points) if chunk.tie_points else 0

    return {
        "filter_stationary": filter_stationary,
        "tiepoint_limit": tiepoint_limit,
        "cameras_total": len(chunk.cameras),
        "cameras_aligned": aligned,
        "tie_points": n_points,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_stationary_filter.py <path/to/witcher/images>")
        sys.exit(1)

    image_dir = pathlib.Path(sys.argv[1])
    if not image_dir.is_dir():
        print(f"ERROR: {image_dir} is not a directory")
        sys.exit(1)

    # Use tiepoint_limit=10000 for both runs so the cap does not mask
    # the difference.  10000 matches the canonical diagnostic recipe.
    TPL = 10000

    print(f"=== Run 1: filter_stationary_points=True  (tiepoint_limit={TPL}) ===")
    r1 = run_alignment(image_dir, filter_stationary=True, tiepoint_limit=TPL)

    print(f"\n=== Run 2: filter_stationary_points=False (tiepoint_limit={TPL}) ===")
    r2 = run_alignment(image_dir, filter_stationary=False, tiepoint_limit=TPL)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"{'Metric':<25} {'Filter ON':<15} {'Filter OFF':<15}")
    print(f"{'-'*25} {'-'*15} {'-'*15}")
    print(f"{'Cameras aligned':<25} {r1['cameras_aligned']:>6}/{r1['cameras_total']:<7} {r2['cameras_aligned']:>6}/{r2['cameras_total']:<7}")
    print(f"{'Tie points':<25} {r1['tie_points']:>12,} {r2['tie_points']:>12,}")

    delta = r2["tie_points"] - r1["tie_points"]
    pct = (delta / r1["tie_points"] * 100) if r1["tie_points"] > 0 else 0
    print(f"\nDelta (OFF - ON): {delta:+,} tie points ({pct:+.1f}%)")

    aligned_delta = r2["cameras_aligned"] - r1["cameras_aligned"]
    print("\nInterpretation:")
    if aligned_delta < 0:
        print(f"  Disabling the filter caused {-aligned_delta} cameras to FAIL alignment.")
        print("  The stationary background tracks corrupt the bundle adjustment.")
        print("  On this dataset the filter is ESSENTIAL, not cosmetic.")
    elif delta > 0:
        print(f"  The filter removed ~{delta:,} stationary/background points.")
        print("  These are likely false matches from the static background or")
        print("  lens artefacts that would degrade bundle adjustment.")
    elif delta < 0:
        print(f"  Filter OFF produced {-delta:,} FEWER tie points — alignment degraded.")
        print("  The unfiltered background matches likely corrupted the bundle.")
    else:
        print("  No significant difference — the dataset may not have strong")
        print("  stationary features, or the tie-point limit capped both runs.")


if __name__ == "__main__":
    main()
