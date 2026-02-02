"""MPK archive handling for Diablo Immortal game files."""

import struct
from pathlib import Path

import lz4.block


def read_mpkinfo(mpkinfo_path: Path) -> list[dict]:
    """
    Parse a .mpkinfo file and return list of file entries.

    MPKInfo format:
    - 4 bytes: header/magic
    - 4 bytes: number of files (little endian)
    - For each file:
      - 2 bytes: name length
      - N bytes: filename
      - 4 bytes: file offset
      - 4 bytes: file length
      - 4 bytes: pak index (divided by 2 to get actual index)
    """
    entries = []

    with open(mpkinfo_path, "rb") as f:
        f.read(4)  # Skip header
        num_files = struct.unpack("<I", f.read(4))[0]

        for _ in range(num_files):
            name_length = struct.unpack("<H", f.read(2))[0]
            name_bytes = f.read(name_length)
            name = name_bytes.decode("utf-8", errors="replace")

            file_offset = struct.unpack("<I", f.read(4))[0]
            file_length = struct.unpack("<I", f.read(4))[0]
            pak_index = struct.unpack("<I", f.read(4))[0] // 2

            if file_length > 0:
                entries.append(
                    {
                        "name": name,
                        "offset": file_offset,
                        "length": file_length,
                        "pak_index": pak_index,
                    }
                )

    return entries


def get_mpk_files(mpkinfo_path: Path) -> list[Path]:
    """Get list of .mpk files associated with an .mpkinfo file."""
    basename = mpkinfo_path.stem
    parent = mpkinfo_path.parent

    if basename.lower().startswith("resource"):
        basename = "Resources"

    mpk_files = [parent / f"{basename}.mpk"]

    for i in range(1, 1000):
        numbered = parent / f"{basename}{i}.mpk"
        if numbered.exists():
            mpk_files.append(numbered)
        else:
            break

    return mpk_files


def extract_file(mpk_path: Path, offset: int, length: int) -> bytes:
    """Extract raw bytes from an MPK file at given offset."""
    with open(mpk_path, "rb") as f:
        f.seek(offset)
        return f.read(length)


def decompress_lz4_block(data: bytes, uncompressed_size: int) -> bytes:
    """
    Custom LZ4 block decoder for Netease format.

    The standard lz4.block library sometimes fails on Netease LZ4 data,
    so we implement a manual decoder following the LZ4 block format spec.
    """
    result = bytearray(uncompressed_size)
    src_pos = 0
    dst_pos = 0

    while src_pos < len(data) and dst_pos < uncompressed_size:
        # Read token byte
        token = data[src_pos]
        src_pos += 1

        # Literal length (high 4 bits of token)
        literal_length = (token >> 4) & 0x0F
        if literal_length == 15:
            while src_pos < len(data):
                extra = data[src_pos]
                src_pos += 1
                literal_length += extra
                if extra != 255:
                    break

        # Copy literals
        copy_len = min(literal_length, len(data) - src_pos, uncompressed_size - dst_pos)
        result[dst_pos : dst_pos + copy_len] = data[src_pos : src_pos + copy_len]
        src_pos += copy_len
        dst_pos += copy_len

        if dst_pos >= uncompressed_size or src_pos + 2 > len(data):
            break

        # Read match offset (2 bytes, little-endian)
        offset = struct.unpack_from("<H", data, src_pos)[0]
        src_pos += 2

        if offset == 0:
            break

        # Match length (low 4 bits of token + 4)
        match_length = (token & 0x0F) + 4
        if match_length == 19:  # 15 + 4 means extended length
            while src_pos < len(data):
                extra = data[src_pos]
                src_pos += 1
                match_length += extra
                if extra != 255:
                    break

        # Copy match (handle overlapping copies)
        match_pos = dst_pos - offset
        if match_pos < 0:
            break

        for i in range(match_length):
            if dst_pos >= uncompressed_size:
                break
            result[dst_pos] = result[match_pos + (i % offset)]
            dst_pos += 1

    return bytes(result[:dst_pos])


def decompress_lz4(data: bytes) -> bytes:
    """Decompress LZ4 compressed data (ZZZ4 format)."""
    if data[:4] == b"ZZZ4":
        uncompressed_size = struct.unpack("<I", data[4:8])[0]
        compressed_data = data[8:]

        # Try standard library first
        try:
            return lz4.block.decompress(
                compressed_data, uncompressed_size=uncompressed_size
            )
        except Exception:
            # Fall back to custom decoder
            return decompress_lz4_block(compressed_data, uncompressed_size)

    try:
        return lz4.block.decompress(data)
    except Exception:
        return data
