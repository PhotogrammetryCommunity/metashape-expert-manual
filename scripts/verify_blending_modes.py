#!/usr/bin/env python3
"""Tier 3 reproducer: buildTexture blending mode behaviour.

Builds a synthetic photogrammetry project (one flat textured plane,
four cameras placed near the corners of the plane) and runs
``Chunk.buildTexture`` once per blending mode, capturing the output
textures for comparison.

A single deliberately discriminating test pattern reveals each mode's
behaviour: each of the four cameras photographs a checkerboard whose
"white" squares are a different *colour* (cam0=red, cam1=green,
cam2=blue, cam3=yellow). All four cameras share the same checkerboard
geometry on the model surface; the output texture's centre region is
where all four cameras overlap and is where the blending mode shows
its personality.

Cam3 carries a 12 deg roll around its optical axis, simulating a
real-world failure mode where one camera's roll component is
imperfectly recovered during alignment. The roll is invisible at
cam3's corner (where cam3 is the only contributor and the surface +
image are co-rotated correctly) but produces a visibly tilted
checkerboard in the central overlap region, where cam3's projection
disagrees with the un-rolled cam0/1/2.

Output is written under ``--output-dir`` (default
``corpus/blending_modes_experiment``):

* ``inputs/cam{0..3}.png`` -- the four synthetic camera images.
* ``outputs/<Mode>.png`` -- one blended texture per mode.
* ``summary.json`` -- per-mode pixel statistics.

Run with::

    ~/.pyenv/versions/Metashape-2.2/bin/python \\
        scripts/verify_blending_modes.py

The script does *not* require an active Pro license: ``buildTexture``
and ``Texture.image().save()`` both work in license-free mode in 2.2.3
(the ``No nodelocked license found`` warning is a notice, not an
error).

Tested on Metashape 2.2.3 (5 modes) and 2.3.1 (5 of 6 modes; Natural
requires depth maps from a real alignment plus a Vulkan-capable GPU).
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

try:
    import Metashape as ms
except ImportError:
    sys.stderr.write(
        "Run with the Metashape pyenv:\n"
        "  ~/.pyenv/versions/Metashape-2.2/bin/python "
        "scripts/verify_blending_modes.py\n"
    )
    sys.exit(2)

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    sys.stderr.write(
        "Pillow + numpy required. Install into the Metashape pyenv:\n"
        "  ~/.pyenv/versions/Metashape-2.2/bin/pip install Pillow numpy\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMG_W, IMG_H = 256, 256
TEX_SIZE = 256
SQUARES = 8                       # 8x8 checkerboard
CAMERA_COLOURS = [
    (255,   0,   0),   # cam0: red
    (  0, 255,   0),   # cam1: green
    (  0,   0, 255),   # cam2: blue
    (255, 255,   0),   # cam3: yellow
]


def all_blending_modes() -> list[tuple[str, "ms.BlendingMode"]]:
    """Return the (label, enum) list of blending modes the local
    Metashape exposes. NaturalBlending is 2.3+ only."""
    base = [
        ("Mosaic",   ms.MosaicBlending),
        ("Average",  ms.AverageBlending),
        ("Max",      ms.MaxBlending),
        ("Min",      ms.MinBlending),
        ("Disabled", ms.DisabledBlending),
    ]
    if hasattr(ms, "NaturalBlending"):
        base.append(("Natural", ms.NaturalBlending))
    return base


# ---------------------------------------------------------------------------
# Synthetic image generation
# ---------------------------------------------------------------------------

def make_colored_checkerboard(rgb: tuple[int, int, int]) -> Image.Image:
    """Return an IMG_W x IMG_H checkerboard whose 'on' squares are the
    given RGB colour and whose 'off' squares are black. The geometry
    is identical across all cameras; only the colour varies."""
    sq = IMG_W // SQUARES
    arr = np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8)
    r, g, b = rgb
    for row in range(SQUARES):
        for col in range(SQUARES):
            if (row + col) % 2 == 0:
                arr[row * sq:(row + 1) * sq, col * sq:(col + 1) * sq] = (r, g, b)
    return Image.fromarray(arr, mode="RGB")


def write_inputs(root: Path) -> list[Path]:
    """Generate the four synthetic input images (one per camera).

    Each image is a checkerboard with the camera's distinguishing
    colour on white squares and black on the rest. cam3's image is
    *identical in content* to the others' (just yellow instead of
    red/green/blue) -- the rotation in test cases comes from cam3's
    rolled camera transform, not pre-rotated image content.

    Returns the absolute paths to the four images in cam0..cam3 order.
    """
    out = root / "inputs"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    paths: list[Path] = []
    for i, rgb in enumerate(CAMERA_COLOURS):
        p = out / f"cam{i}.png"
        make_colored_checkerboard(rgb).save(p)
        paths.append(p)
    return [p.resolve() for p in paths]


# ---------------------------------------------------------------------------
# Synthetic Metashape project
# ---------------------------------------------------------------------------

QUAD_OBJ = """\
v -0.5 -0.5 0
v  0.5 -0.5 0
v  0.5  0.5 0
v -0.5  0.5 0
vt 0 0
vt 1 0
vt 1 1
vt 0 1
vn 0 0 1
f 1/1/1 2/2/1 3/3/1 4/4/1
"""

# 4 cameras placed near the corners of the model plane at altitude
# 1.0m, looking nadir. The asymmetric placement plus the camera FOV
# (53.1 deg horizontal, with focal length = sensor width) gives each
# camera a footprint that covers ITS own corner of the plane plus
# overlap into the centre, but NOT the opposite corner. As a result:
# - each corner of the texture is seen by exactly one camera;
# - only the central region is seen by all four cameras.
# This produces a more realistic and visually informative test bed
# than a perfectly symmetric grid above the plane (where every region
# is seen by all four cameras).
CAMERA_POSITIONS = [
    (-0.4, -0.4, 1.0),
    ( 0.4, -0.4, 1.0),
    ( 0.4,  0.4, 1.0),
    (-0.4,  0.4, 1.0),
]

# Roll applied to cam3 around its optical axis. Used in ALL tests, so
# that the camera setup is constant across tests; the differences
# between tests come from the input images alone.
# - In Test C (solid colours) and Test E (uniform-brightness
#   checkerboard), the roll is invisible because the input is
#   rotationally symmetric within each cell.
# - In Test R (uniform checkerboard, all 4 cameras same image), the
#   roll is the SOLE source of cam3's misregistration relative to the
#   other three cameras.
CAMERA_ROLL_DEG = 12.0

R_NADIR = ms.Matrix([
    [1,  0,  0],
    [0, -1,  0],
    [0,  0, -1],
])


def _rolled_R(roll_deg: float) -> "ms.Matrix":
    """Return the rotation part of the camera-to-world transform for a
    nadir camera with the given roll (deg) around its optical axis."""
    theta = math.radians(roll_deg)
    c, s = math.cos(theta), math.sin(theta)
    # R_new = R_nadir @ Rz(theta), where Rz is in the camera frame.
    # Computed analytically:
    return ms.Matrix([
        [ c, -s,  0],
        [-s, -c,  0],
        [ 0,  0, -1],
    ])


def build_chunk(image_paths: list[Path]) -> "ms.Chunk":
    """Construct a fresh Document + Chunk with a flat-quad model and 4
    cameras configured to view it from above."""
    doc = ms.Document()
    chunk = doc.addChunk()

    # Shared sensor: 256x256, focal length 256 px, PP at image centre,
    # no distortion, fixed calibration.
    sensor = chunk.addSensor()
    sensor.label = "synthetic"
    sensor.type = ms.Sensor.Type.Frame
    sensor.width = IMG_W
    sensor.height = IMG_H
    sensor.pixel_height = 1.0
    sensor.pixel_width = 1.0
    sensor.focal_length = float(IMG_W)
    sensor.fixed_calibration = True
    calib = ms.Calibration()
    calib.width = IMG_W
    calib.height = IMG_H
    calib.f = float(IMG_W)
    calib.cx = 0.0
    calib.cy = 0.0
    sensor.user_calib = calib

    chunk.addPhotos([str(p) for p in image_paths])
    assert len(chunk.cameras) == len(CAMERA_POSITIONS), (
        f"expected {len(CAMERA_POSITIONS)} cameras, got {len(chunk.cameras)}"
    )

    R_cam3 = _rolled_R(CAMERA_ROLL_DEG)
    for i, (cam, pos) in enumerate(zip(chunk.cameras, CAMERA_POSITIONS)):
        cam.sensor = sensor
        # cam3 has a rolled rotation; cam0..cam2 are nadir.
        R = R_cam3 if i == 3 else R_NADIR
        cam.transform = ms.Matrix([
            [R[0, 0], R[0, 1], R[0, 2], pos[0]],
            [R[1, 0], R[1, 1], R[1, 2], pos[1]],
            [R[2, 0], R[2, 1], R[2, 2], pos[2]],
            [0, 0, 0, 1.0],
        ])

    # Import the flat textured-UV quad. The OBJ is written into the
    # experiment's --output-dir so it is gitignored alongside the
    # other experiment artefacts.
    obj_path = image_paths[0].parent.parent / "quad.obj"
    obj_path.write_text(QUAD_OBJ)
    chunk.importModel(str(obj_path))

    return chunk


def run_blending(chunk: "ms.Chunk", mode_enum) -> Image.Image:
    """Run buildTexture with the given mode and return the resulting
    texture as a Pillow image."""
    chunk.buildTexture(blending_mode=mode_enum, texture_size=TEX_SIZE)
    if not chunk.model.textures:
        raise RuntimeError("buildTexture produced no texture")
    ms_img = chunk.model.textures[0].image()
    # Texture.image() supports .save(path); to convert to PIL we save
    # to a BytesIO via tmpfile and re-read.
    import tempfile, os as _os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        ms_img.save(tmp.name)
        return Image.open(tmp.name).convert("RGB").copy()
    finally:
        _os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Comparison + reporting
# ---------------------------------------------------------------------------

def sample_pixels(im: Image.Image) -> dict[str, list[int]]:
    """Sample a small grid of pixel locations and return their RGB
    values for use in the article's results table."""
    arr = np.array(im)
    H, W, _ = arr.shape
    samples = {
        "centre": arr[H // 2, W // 2].tolist(),
        "top-left":     arr[H // 4, W // 4].tolist(),
        "top-right":    arr[H // 4, 3 * W // 4].tolist(),
        "bottom-left":  arr[3 * H // 4, W // 4].tolist(),
        "bottom-right": arr[3 * H // 4, 3 * W // 4].tolist(),
    }
    return {k: [int(c) for c in v] for k, v in samples.items()}


def summary_stats(im: Image.Image) -> dict:
    """Return a dict of summary stats for the texture image."""
    arr = np.array(im)
    return {
        "samples": sample_pixels(im),
        "mean_rgb":   [int(round(c)) for c in arr.reshape(-1, 3).mean(axis=0)],
        "median_rgb": [int(c) for c in np.median(arr.reshape(-1, 3), axis=0)],
        "unique_colours": int(len(np.unique(arr.reshape(-1, 3), axis=0))),
        "size": [arr.shape[1], arr.shape[0]],
    }


# ---------------------------------------------------------------------------
# Article figure generation (deterministic JPEGs)
# ---------------------------------------------------------------------------

CELL_PX   = 128      # thumbnail size for each cell
LABEL_PX  = 20       # height of the per-cell label strip
TITLE_PX  = 22       # height of the row title strip
PAD_PX    = 8
BG        = (245, 245, 245)
FG        = (32, 32, 32)
LABEL_FONT_SIZE = 13
TITLE_FONT_SIZE = 14


def _label_font():
    return ImageFont.load_default(size=LABEL_FONT_SIZE)


def _title_font():
    return ImageFont.load_default(size=TITLE_FONT_SIZE)


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font=None) -> None:
    """Draw text using the size-aware default Pillow font (DejaVu Sans
    Mono), bundled with Pillow >= 10. Deterministic across runs."""
    draw.text(xy, text, fill=FG, font=font)


def _row_image(images_and_labels: list[tuple[Image.Image, str]], title: str) -> Image.Image:
    """Compose a labelled row of cells: title strip, label strip, cell row."""
    n = len(images_and_labels)
    W = n * CELL_PX + (n + 1) * PAD_PX
    H = TITLE_PX + LABEL_PX + CELL_PX + PAD_PX
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _draw_text(d, (PAD_PX, 3), title, font=_title_font())
    lf = _label_font()
    for i, (cell_im, lbl) in enumerate(images_and_labels):
        x = PAD_PX + i * (CELL_PX + PAD_PX)
        _draw_text(d, (x + 4, TITLE_PX + 2), lbl, font=lf)
        thumb = cell_im.resize((CELL_PX, CELL_PX), Image.NEAREST)
        img.paste(thumb, (x, TITLE_PX + LABEL_PX))
    return img


def make_test_figure(
    input_paths: list[Path],
    output_paths: dict[str, Path],
    figure_path: Path,
) -> None:
    """Compose the article figure: inputs row + outputs row.

    Deterministic JPEG output suitable for embedding in the article.
    PIL's JPEG encoder emits only the JFIF APP0 marker (no EXIF, no
    Software field), so re-saving the same pixel buffer with the same
    parameters produces byte-identical output.
    """
    inputs = [(Image.open(p).convert("RGB"), p.stem) for p in input_paths]
    in_row = _row_image(inputs, "Inputs (one image per camera; cam3 has 12 deg roll)")

    output_order = ["Mosaic", "Average", "Max", "Min", "Disabled"]
    outputs = []
    for mode in output_order:
        if mode in output_paths:
            outputs.append((Image.open(output_paths[mode]).convert("RGB"), mode))
    out_row = _row_image(outputs, "Outputs by blending mode")

    W = max(in_row.width, out_row.width)
    H = in_row.height + out_row.height
    composite = Image.new("RGB", (W, H), BG)
    composite.paste(in_row, ((W - in_row.width) // 2, 0))
    composite.paste(out_row, ((W - out_row.width) // 2, in_row.height))

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    composite.save(
        figure_path,
        format="JPEG",
        quality=82,
        optimize=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tier 3 reproducer for buildTexture blending modes",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("corpus/blending_modes_experiment"),
        help="root for inputs/outputs/summary.json",
    )
    parser.add_argument(
        "--docs-img-dir",
        type=Path,
        default=Path("docs/workflow/texture/img"),
        help=(
            "destination for the article's composite JPEG figure. "
            "Set to '' to skip figure generation."
        ),
    )
    parser.add_argument(
        "--regenerate-figures",
        action="store_true",
        help=(
            "force overwrite of the existing JPEG figure in --docs-img-dir. "
            "Default is to leave existing files untouched, because "
            "Metashape's tie-breaking in Disabled / Max / Min modes is "
            "non-deterministic across runs and would produce spurious "
            "byte diffs even though the qualitative behaviour is "
            "stable. Use this flag when intentionally refreshing the "
            "article's figure."
        ),
    )
    args = parser.parse_args()

    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    modes = all_blending_modes()

    print(f"# Metashape buildTexture blending-mode reproducer")
    print(f"# Output:    {args.output_dir}")
    print(f"# Modes:     {[m for m, _ in modes]}")
    print(f"# Metashape: {ms.app.version}")

    summary: dict = {
        "metashape_version": ms.app.version,
        "modes": {},
    }

    image_paths = write_inputs(args.output_dir)
    print(f"\nWrote {len(image_paths)} input images to {args.output_dir / 'inputs'}")
    out_dir = args.output_dir / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    for mode_label, mode_enum in modes:
        chunk = build_chunk(image_paths)
        try:
            tex = run_blending(chunk, mode_enum)
        except Exception as e:
            # Natural blending requires depth maps (which require
            # alignment with real tie points) AND a Vulkan-capable
            # GPU. Both are out of scope for the synthetic test bed.
            summary["modes"][mode_label] = {
                "skipped": True,
                "error": f"{type(e).__name__}: {e}",
            }
            print(f"  {mode_label:8s} -> SKIPPED ({type(e).__name__}: {e})")
            continue
        out_path = out_dir / f"{mode_label}.png"
        tex.save(out_path)
        stats = summary_stats(tex)
        summary["modes"][mode_label] = stats
        centre = stats["samples"]["centre"]
        print(
            f"  {mode_label:8s} -> "
            f"centre RGB=({centre[0]:3d},{centre[1]:3d},{centre[2]:3d})  "
            f"mean=({stats['mean_rgb'][0]:3d},{stats['mean_rgb'][1]:3d},{stats['mean_rgb'][2]:3d})  "
            f"unique={stats['unique_colours']:5d}"
        )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary -> {summary_path}")

    # Generate the article's composite figure.
    docs_img_dir = args.docs_img_dir if str(args.docs_img_dir) else None
    if docs_img_dir is not None:
        output_paths: dict[str, Path] = {}
        for mode_label, _ in modes:
            p = out_dir / f"{mode_label}.png"
            if p.exists():
                output_paths[mode_label] = p
        fig = docs_img_dir / "blending-modes.jpg"
        if fig.exists() and not args.regenerate_figures:
            print(
                f"\nFigure {fig} already exists; skipped "
                f"(use --regenerate-figures to refresh)."
            )
        else:
            make_test_figure(image_paths, output_paths, fig)
            print(f"\nFigure -> {fig}  ({fig.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
