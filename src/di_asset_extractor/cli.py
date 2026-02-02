"""Command-line interface for Diablo Immortal asset extractor."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .extract import extract_sprites


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="di-extract",
        description="Extract sprite images from Diablo Immortal game files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  di-extract "C:\\Program Files (x86)\\Diablo Immortal" C:\\Users\\You\\sprites
  di-extract /path/to/game/files ./output

Finding your game files:
  Look for the folder containing Resources.mpkinfo and Resources.mpk files.
  Common Windows locations:
    C:\\Program Files (x86)\\Diablo Immortal\\
    C:\\ProgramData\\Battle.net\\Agent\\data\\cache\\...
""",
    )

    parser.add_argument(
        "mpks_dir",
        metavar="MPKS_DIR",
        type=Path,
        help="Directory containing Resources.mpkinfo and .mpk files",
    )

    parser.add_argument(
        "output_dir",
        metavar="OUTPUT_DIR",
        type=Path,
        help="Directory to save extracted sprite PNGs",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Validate input directory
    mpkinfo_path = args.mpks_dir / "Resources.mpkinfo"
    if not mpkinfo_path.exists():
        print(f"Error: Resources.mpkinfo not found in {args.mpks_dir}", file=sys.stderr)
        print(
            "\nMake sure the directory contains Resources.mpkinfo and .mpk files.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Diablo Immortal Asset Extractor v{__version__}")
    print(f"Source: {args.mpks_dir}")
    print(f"Output: {args.output_dir}")
    print()

    try:
        extracted, failed = extract_sprites(args.mpks_dir, args.output_dir)

        print()
        print("Extraction complete!")
        print(f"  Sprites extracted: {extracted}")
        if failed > 0:
            print(f"  Failed: {failed}")
        print(f"  Output: {args.output_dir}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)


if __name__ == "__main__":
    main()
