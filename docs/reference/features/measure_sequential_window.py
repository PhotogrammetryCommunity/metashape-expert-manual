#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Part of the Metashape Expert Manual. MIT-licensed (see README "License").
# © Metashape Expert Manual contributors.
"""
Determine Metashape's sequential reference preselection window size.

This script uses binary search to find the value k such that:
- For pattern sequences of length <= k, sequential matching finds matches
  (because identical patterns fall within the matching window)
- For pattern sequences of length > k, no matches are found
  (because identical patterns are too far apart)

The script creates random noise images as unique patterns, then builds
sequences of repeating patterns and runs Metashape's matchPhotos with
sequential reference preselection to detect matches.

Usage:
    python measure_sequential_window.py

Requirements:
    - Metashape Python API
    - PIL/Pillow
    - numpy
"""

import tempfile
from pathlib import Path

import Metashape
import numpy as np
from PIL import Image


def create_pattern_images(patterns_dir: Path, num_patterns: int, size: tuple[int, int] = (640, 480)) -> None:
    """Create unique random noise images as patterns."""
    patterns_dir.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    for i in range(num_patterns):
        noise = rng.integers(0, 256, (*size[::-1], 3), dtype=np.uint8)
        img = Image.fromarray(noise)
        img.save(patterns_dir / f"pat{i:02d}.jpg", quality=95)


def create_image_sequence(images_dir: Path, patterns_dir: Path, k: int, total_images: int = 60) -> int:
    """
    Create a sequence of images by repeating k patterns.

    Returns the actual number of images created (k * floor(total_images / k)).
    """
    images_dir.mkdir(exist_ok=True)
    num_images = k * (total_images // k)
    for i in range(num_images):
        pattern_idx = i % k
        src = patterns_dir / f"pat{pattern_idx:02d}.jpg"
        dst = images_dir / f"img_{i:03d}.jpg"
        if dst.exists():
            dst.unlink()
        dst.hardlink_to(src)
    return num_images


def run_sequential_matching(images_dir: Path) -> float:
    """
    Run Metashape sequential matching and return average projections per image.

    Returns 0.0 if no matches found, >0 otherwise.
    """
    doc = Metashape.Document()
    chunk = doc.addChunk()

    image_files = sorted(images_dir.glob("img_*.jpg"))
    chunk.addPhotos([str(f) for f in image_files])

    chunk.matchPhotos(
        generic_preselection=False,
        reference_preselection=True,
        reference_preselection_mode=Metashape.ReferencePreselectionMode.ReferencePreselectionSequential,
        filter_stationary_points=False,
    )

    if not chunk.tie_points or not chunk.cameras:
        return 0.0

    total = sum(len(chunk.tie_points.projections[cam]) for cam in chunk.cameras)
    return total / len(chunk.cameras)


def has_matches(patterns_dir: Path, images_dir: Path, k: int) -> bool:
    """Test if pattern sequence of length k produces matches."""
    # Clean up previous images
    for f in images_dir.glob("img_*.jpg"):
        f.unlink()

    create_image_sequence(images_dir, patterns_dir, k)
    avg_proj = run_sequential_matching(images_dir)
    print(f"  k={k}: avg_projections={avg_proj:.2f}")
    return avg_proj > 0


def find_sequential_window(patterns_dir: Path, images_dir: Path, low: int = 5, high: int = 50) -> int:
    """
    Binary search to find the sequential matching window size.

    Returns k where:
    - k is the largest value where matches are found
    - k+1 is the smallest value where no matches are found
    """
    print(f"Binary search for sequential window size in range [{low}, {high}]")

    # First verify boundaries
    if not has_matches(patterns_dir, images_dir, low):
        print(f"ERROR: No matches at k={low}, increase pattern count or lower bound")
        return -1

    if has_matches(patterns_dir, images_dir, high):
        print(f"WARNING: Matches found at k={high}, window may be larger than {high}")
        return high

    # Binary search: find largest k with matches
    while low < high - 1:
        mid = (low + high) // 2
        if has_matches(patterns_dir, images_dir, mid):
            low = mid
        else:
            high = mid

    return low


def main() -> None:
    print("Metashape Sequential Reference Preselection Window Size Finder")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        patterns_dir = tmppath / "patterns"
        images_dir = tmppath / "images"

        print("\nCreating 50 unique pattern images...")
        create_pattern_images(patterns_dir, num_patterns=50)

        print("\nSearching for window size...\n")
        window = find_sequential_window(patterns_dir, images_dir, low=5, high=50)

        print("\n" + "=" * 60)
        if window > 0:
            print(f"Sequential reference preselection window size: {window}")
            print(f"(Metashape matches image i with images i+1 to i+{window})")
        else:
            print("Could not determine window size")


if __name__ == "__main__":
    main()
