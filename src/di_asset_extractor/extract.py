"""Main extraction logic for Diablo Immortal sprites."""

import plistlib
import struct
import sys
from pathlib import Path
from typing import Optional

from PIL import Image

from .mpk import (
    read_mpkinfo,
    get_mpk_files,
    extract_file,
    decompress_lz4,
    decompress_lz4_block,
)
from .repository import ResourceRepository, parse_repository
from .texture import decode_texture


def load_repository(mpkinfo_path: Path) -> Optional[ResourceRepository]:
    """Load and parse resource.repository file."""
    entries = read_mpkinfo(mpkinfo_path)
    mpk_files = get_mpk_files(mpkinfo_path)

    repo_data = None
    for entry in entries:
        if "resource.repository" in entry["name"].lower():
            if entry["pak_index"] < len(mpk_files):
                mpk_path = mpk_files[entry["pak_index"]]
                data = extract_file(mpk_path, entry["offset"], entry["length"])

                if data[:4] == b"CCCC":
                    if data[4:8] == b"ZZZ4":
                        uncompressed_size = struct.unpack("<I", data[8:12])[0]
                        compressed_data = data[12:]
                        repo_data = decompress_lz4_block(
                            compressed_data, uncompressed_size
                        )
                    else:
                        repo_data = data[4:]
                elif data[:4] == b"ZZZ4":
                    repo_data = decompress_lz4(data)
                else:
                    repo_data = data
                break

    if not repo_data:
        return None

    try:
        return parse_repository(repo_data)
    except Exception:
        return None


def find_texture_guid(repo: ResourceRepository, texture_name: str) -> Optional[str]:
    """Find the GUID path for a texture by its logical name."""
    if not repo:
        return None

    search_name = texture_name.replace(".png", "")
    matches = repo.find_by_name(search_name)

    for entry in matches:
        entry_info = repo.get_entry_info(entry)
        if entry_info["resource_type"] == "Texture2D":
            return entry_info["guid_path"]

    return None


def parse_frame_string(frame_str: str) -> tuple[int, int, int, int]:
    """Parse Cocos2d frame string like '{{2,2},{80,80}}' -> (x, y, width, height)"""
    clean = frame_str.replace("{", "").replace("}", "")
    parts = [int(x) for x in clean.split(",")]
    return parts[0], parts[1], parts[2], parts[3]


def print_progress(current: int, total: int, prefix: str = ""):
    """Print a simple text progress bar."""
    bar_width = 40
    filled = int(bar_width * current / total)
    bar = "=" * filled + "-" * (bar_width - filled)
    percent = 100.0 * current / total
    sys.stdout.write(f"\r{prefix}[{bar}] {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()


def extract_sprites(mpks_dir: Path, output_dir: Path) -> tuple[int, int]:
    """
    Extract all sprites from Diablo Immortal game files.

    Args:
        mpks_dir: Directory containing Resources.mpkinfo and .mpk files
        output_dir: Directory to save extracted sprite PNGs

    Returns:
        Tuple of (sprites_extracted, sprites_failed)
    """
    mpkinfo_path = mpks_dir / "Resources.mpkinfo"

    if not mpkinfo_path.exists():
        raise FileNotFoundError(f"MPK info file not found: {mpkinfo_path}")

    print(f"Loading resource repository...")
    repo = load_repository(mpkinfo_path)
    if not repo:
        raise RuntimeError("Could not load resource repository")
    print(f"  Loaded {len(repo.entries)} resources")

    print(f"Reading MPK index...")
    entries = read_mpkinfo(mpkinfo_path)
    mpk_files = get_mpk_files(mpkinfo_path)
    print(f"  Found {len(entries)} entries across {len(mpk_files)} MPK files")

    # Find all plist files (sprite atlases)
    plist_entries = [e for e in entries if e["name"].endswith(".plist")]
    print(f"  Found {len(plist_entries)} sprite atlases")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Track sprite names for deduplication
    sprite_names: dict[str, int] = {}
    sprites_extracted = 0
    sprites_failed = 0
    texture_cache: dict[str, Optional[Image.Image]] = {}

    print(f"\nExtracting sprites...")

    for idx, plist_entry in enumerate(plist_entries):
        print_progress(idx + 1, len(plist_entries), "Processing atlases: ")

        try:
            # Extract and parse plist
            mpk_path = mpk_files[plist_entry["pak_index"]]
            plist_data = extract_file(
                mpk_path, plist_entry["offset"], plist_entry["length"]
            )
            if plist_data[:4] == b"ZZZ4":
                plist_data = decompress_lz4(plist_data)

            plist = plistlib.loads(plist_data)
            frames = plist.get("frames", {})
            metadata = plist.get("metadata", {})
            texture_filename = metadata.get("textureFileName", "")

            if not frames or not texture_filename:
                continue

            # Load texture atlas (with caching)
            if texture_filename not in texture_cache:
                guid_path = find_texture_guid(repo, texture_filename)
                atlas = None

                if guid_path:
                    for tex_entry in entries:
                        if (
                            guid_path in tex_entry["name"]
                            or tex_entry["name"].endswith(guid_path)
                        ):
                            tex_mpk = mpk_files[tex_entry["pak_index"]]
                            tex_data = extract_file(
                                tex_mpk, tex_entry["offset"], tex_entry["length"]
                            )
                            if tex_data[:4] == b"ZZZ4":
                                tex_data = decompress_lz4(tex_data)

                            atlas = decode_texture(tex_data)
                            break

                texture_cache[texture_filename] = atlas

            atlas = texture_cache.get(texture_filename)
            if not atlas:
                sprites_failed += len(frames)
                continue

            # Extract each sprite from the atlas
            for sprite_name, sprite_info in frames.items():
                try:
                    frame_str = sprite_info.get("frame", "{{0,0},{0,0}}")
                    x, y, w, h = parse_frame_string(frame_str)
                    rotated = sprite_info.get("rotated", False)

                    if w <= 0 or h <= 0:
                        sprites_failed += 1
                        continue

                    # Crop sprite from atlas
                    if rotated:
                        # When rotated, width and height are swapped in the frame
                        sprite = atlas.crop((x, y, x + h, y + w))
                        sprite = sprite.rotate(90, expand=True)
                    else:
                        sprite = atlas.crop((x, y, x + w, y + h))

                    # Generate unique filename
                    base_name = Path(sprite_name).stem
                    if base_name in sprite_names:
                        sprite_names[base_name] += 1
                        save_name = f"{base_name}_{sprite_names[base_name]}.png"
                    else:
                        sprite_names[base_name] = 0
                        save_name = f"{base_name}.png"

                    # Save sprite
                    sprite.save(output_dir / save_name, "PNG")
                    sprites_extracted += 1

                except Exception:
                    sprites_failed += 1

        except Exception:
            sprites_failed += 1

    print()  # Newline after progress bar
    return sprites_extracted, sprites_failed
