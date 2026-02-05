"""Image similarity search for extracted sprites using perceptual hashing."""

import argparse
import json
import shutil
import sys
from pathlib import Path

import imagehash
from PIL import Image

from . import __version__

INDEX_FILENAME = ".sprite-index.json"
INDEX_VERSION = 4


def compute_hash(image_path: Path) -> str:
    """Compute color hash for an image (better for matching items by color)."""
    with Image.open(image_path) as img:
        return str(imagehash.colorhash(img))


def build_index(sprites_dir: Path) -> dict:
    """Build hash index for all PNG files in sprites directory."""
    hashes: dict[str, list[str]] = {}
    png_files = list(sprites_dir.glob("*.png"))
    total = len(png_files)

    print(f"Building index for {total} sprites...")

    for i, png_path in enumerate(png_files, 1):
        if i % 1000 == 0 or i == total:
            print(f"  Indexed {i}/{total} sprites...", end="\r")
        try:
            h = compute_hash(png_path)
            if h not in hashes:
                hashes[h] = []
            hashes[h].append(png_path.name)
        except Exception:
            # Skip files that can't be hashed
            pass

    print()  # Clear the progress line

    index = {"version": INDEX_VERSION, "hashes": hashes}

    # Save index
    index_path = sprites_dir / INDEX_FILENAME
    with open(index_path, "w") as f:
        json.dump(index, f)

    print(f"Index saved: {len(hashes)} unique hashes")
    return index


def load_or_build_index(sprites_dir: Path, force_rebuild: bool = False) -> dict:
    """Load existing index or build a new one if stale/missing."""
    index_path = sprites_dir / INDEX_FILENAME

    if force_rebuild:
        print("Forcing index rebuild...")
        return build_index(sprites_dir)

    if not index_path.exists():
        print("No index found, building...")
        return build_index(sprites_dir)

    # Check if index is stale (older than newest sprite)
    index_mtime = index_path.stat().st_mtime
    png_files = list(sprites_dir.glob("*.png"))
    if png_files:
        newest_sprite = max(f.stat().st_mtime for f in png_files)
        if newest_sprite > index_mtime:
            print("Index is stale, rebuilding...")
            return build_index(sprites_dir)

    # Load existing index
    with open(index_path) as f:
        index = json.load(f)

    if index.get("version") != INDEX_VERSION:
        print("Index version mismatch, rebuilding...")
        return build_index(sprites_dir)

    print(f"Loaded existing index ({len(index['hashes'])} unique hashes)")
    return index


def search(
    query_path: Path, sprites_dir: Path, top_n: int, force_rebuild: bool = False
) -> list[tuple[str, int]]:
    """Find top N most similar sprites to query image."""
    index = load_or_build_index(sprites_dir, force_rebuild)

    print("Computing query hash...")
    query_hash = imagehash.hex_to_hash(compute_hash(query_path))

    print("Searching for matches...")
    results: list[tuple[str, int]] = []

    for hash_str, filenames in index["hashes"].items():
        distance = query_hash - imagehash.hex_to_hash(hash_str)
        for filename in filenames:
            results.append((filename, distance))

    # Sort by distance (lower = more similar)
    results.sort(key=lambda x: (x[1], x[0]))
    return results[:top_n]


def main():
    """Main entry point for the search CLI."""
    parser = argparse.ArgumentParser(
        prog="di-search",
        description="Find similar sprites using perceptual image hashing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  di-search screenshot.png
  di-search screenshot.png ./sprites --top 20
  di-search icon.png ./my-sprites --rebuild

The search results are copied to search-results/ next to the sprites folder.
""",
    )

    parser.add_argument(
        "screenshot",
        metavar="SCREENSHOT",
        type=Path,
        help="Path to screenshot/image to search for",
    )

    parser.add_argument(
        "sprites_dir",
        metavar="SPRITES_DIR",
        type=Path,
        nargs="?",
        default=Path("./sprites"),
        help="Directory containing extracted sprites (default: ./sprites)",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of results to return (default: 10)",
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild the search index",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.screenshot.exists():
        print(f"Error: Screenshot not found: {args.screenshot}", file=sys.stderr)
        sys.exit(1)

    if not args.sprites_dir.exists():
        print(f"Error: Sprites directory not found: {args.sprites_dir}", file=sys.stderr)
        sys.exit(1)

    if not list(args.sprites_dir.glob("*.png")):
        print(f"Error: No PNG files found in {args.sprites_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Diablo Immortal Sprite Search v{__version__}")
    print(f"Query: {args.screenshot}")
    print(f"Sprites: {args.sprites_dir}")
    print()

    try:
        results = search(args.screenshot, args.sprites_dir, args.top, args.rebuild)

        print()
        print(f"Top {len(results)} matches:")
        for i, (filename, distance) in enumerate(results, 1):
            match_note = " <- exact match" if distance == 0 else ""
            print(f"  {i:2}. {filename} (distance: {distance}){match_note}")

        # Copy results to search-results folder next to sprites
        results_dir = args.sprites_dir.resolve().parent / "search-results"
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir()

        for i, (filename, _) in enumerate(results, 1):
            src = args.sprites_dir / filename
            dst = results_dir / f"{i:02}_{filename}"
            shutil.copy2(src, dst)

        print()
        print(f"Results saved to: {results_dir}/")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)


if __name__ == "__main__":
    main()
