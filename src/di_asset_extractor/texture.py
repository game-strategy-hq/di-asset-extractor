"""MESSIAH texture decoder for Diablo Immortal game files."""

import struct
from typing import Optional

import lz4.block
from PIL import Image

try:
    import texture2ddecoder

    HAS_TEXTURE_DECODER = True
except ImportError:
    HAS_TEXTURE_DECODER = False


# Pixel format constants
PIXEL_FORMAT_R8G8B8A8 = 5
PIXEL_FORMAT_BC1 = 18
PIXEL_FORMAT_BC7 = 25
PIXEL_FORMAT_ASTC_4x4 = 36
PIXEL_FORMAT_ASTC_6x6 = 40
PIXEL_FORMAT_ASTC_8x8 = 43

PIXEL_FORMAT_NAMES = {
    5: "R8G8B8A8",
    18: "BC1",
    25: "BC7",
    36: "ASTC_4x4",
    40: "ASTC_6x6",
    43: "ASTC_8x8",
}


class Texture2DInfo:
    """Header information for a MESSIAH texture."""

    def __init__(self, data: bytes):
        """Parse 40-byte Texture2DInfo header."""
        self.mag_filter = data[0x00]
        self.min_filter = data[0x01]
        self.mip_filter = data[0x02]
        self.address_u = data[0x03]
        self.address_v = data[0x04]
        self.format = data[0x05]  # Pixel format
        self.mip_level = data[0x06]
        self.flags = data[0x07]
        self.compression_preset = data[0x08]
        self.lod_group = data[0x09]
        self.mip_gen_preset = data[0x0A]
        self.texture_type = data[0x0B]

        self.width = struct.unpack_from("<H", data, 0x0C)[0]
        self.height = struct.unpack_from("<H", data, 0x0E)[0]

        # Default color (4 floats)
        self.default_color = struct.unpack_from("<ffff", data, 0x10)

        self.size = struct.unpack_from("<I", data, 0x20)[0]
        self.unknown = struct.unpack_from("<H", data, 0x24)[0]
        self.slice_count = struct.unpack_from("<H", data, 0x26)[0]

    def get_format_name(self) -> str:
        """Get human-readable format name."""
        return PIXEL_FORMAT_NAMES.get(self.format, f"Unknown({self.format})")


class TextureSliceInfo:
    """Information about a single texture slice/mipmap level."""

    def __init__(self, data: bytes):
        """Parse 16-byte TextureSliceInfo."""
        self.size = struct.unpack_from("<I", data, 0x00)[0]
        self.width = struct.unpack_from("<H", data, 0x04)[0]
        self.height = struct.unpack_from("<H", data, 0x06)[0]
        self.depth = struct.unpack_from("<H", data, 0x08)[0]
        self.pitch_in_byte = struct.unpack_from("<H", data, 0x0A)[0]
        self.slice_in_byte = struct.unpack_from("<I", data, 0x0C)[0]

    def is_compressed(self) -> bool:
        """Check if this slice uses compression."""
        return self.slice_in_byte != 0


def decompress_slice_data(data: bytes, marker: bytes) -> bytes:
    """Decompress slice data based on marker."""
    if marker == b"NNNN":
        # Raw data - skip marker
        return data[4:]
    elif marker == b"ZZZ4":
        # LZ4 compressed
        uncompressed_size = struct.unpack_from("<I", data, 4)[0]
        compressed_data = data[8:]  # Skip marker (4) + size (4)
        return lz4.block.decompress(
            compressed_data, uncompressed_size=uncompressed_size
        )
    else:
        # Unknown marker - return as-is
        return data


def decode_bc7(data: bytes, width: int, height: int) -> bytes:
    """Decode BC7 compressed texture data."""
    if not HAS_TEXTURE_DECODER:
        raise ImportError("texture2ddecoder not available")
    return texture2ddecoder.decode_bc7(data, width, height)


def decode_astc(
    data: bytes, width: int, height: int, block_width: int, block_height: int
) -> bytes:
    """Decode ASTC compressed texture data."""
    if not HAS_TEXTURE_DECODER:
        raise ImportError("texture2ddecoder not available")
    return texture2ddecoder.decode_astc(data, width, height, block_width, block_height)


def get_astc_block_size(pixel_format: int) -> tuple[int, int]:
    """Get ASTC block dimensions for a pixel format."""
    if pixel_format == PIXEL_FORMAT_ASTC_4x4:
        return (4, 4)
    elif pixel_format == PIXEL_FORMAT_ASTC_6x6:
        return (6, 6)
    elif pixel_format == PIXEL_FORMAT_ASTC_8x8:
        return (8, 8)
    else:
        raise ValueError(f"Not an ASTC format: {pixel_format}")


class MessiahTexture:
    """MESSIAH texture file parser and decoder."""

    def __init__(self, data: bytes):
        """Initialize from texture file data."""
        self.data = data
        self.info: Optional[Texture2DInfo] = None
        self.slices: list[TextureSliceInfo] = []
        self._parse_header()

    def _parse_header(self):
        """Parse texture header and slice info."""
        if len(self.data) < 40:
            raise ValueError("Data too small for Texture2DInfo header")

        self.info = Texture2DInfo(self.data[:40])

        # Parse slice headers
        offset = 40
        for i in range(self.info.slice_count):
            if offset + 16 > len(self.data):
                break

            slice_info = TextureSliceInfo(self.data[offset : offset + 16])
            self.slices.append(slice_info)
            offset += 16

            # Skip slice data to get to next slice header
            data_size = slice_info.size - 16
            offset += data_size

    def decode(self, mip_level: int = 0) -> Image.Image:
        """Decode texture to PIL Image."""
        if not self.info:
            raise ValueError("Texture not initialized")

        if mip_level >= len(self.slices):
            raise ValueError(
                f"Mip level {mip_level} not available (have {len(self.slices)} slices)"
            )

        slice_info = self.slices[mip_level]

        # Calculate offset to slice data
        offset = 40  # Skip Texture2DInfo
        for i in range(mip_level):
            offset += self.slices[i].size

        # Read slice data (including header)
        slice_data = self.data[offset : offset + slice_info.size]

        # Skip the 16-byte slice header to get to marker and data
        marker = slice_data[16:20]
        payload = slice_data[16:]

        # Decompress if needed
        raw_data = decompress_slice_data(payload, marker)

        # Decode based on pixel format
        width = slice_info.width
        height = slice_info.height

        if self.info.format == PIXEL_FORMAT_R8G8B8A8:
            # Raw RGBA8
            return Image.frombytes("RGBA", (width, height), raw_data, "raw", "RGBA")

        elif self.info.format == PIXEL_FORMAT_BC7:
            # BC7 compression (PC)
            decoded = decode_bc7(raw_data, width, height)
            return Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")

        elif self.info.format in [
            PIXEL_FORMAT_ASTC_4x4,
            PIXEL_FORMAT_ASTC_6x6,
            PIXEL_FORMAT_ASTC_8x8,
        ]:
            # ASTC compression (mobile)
            block_w, block_h = get_astc_block_size(self.info.format)
            decoded = decode_astc(raw_data, width, height, block_w, block_h)
            return Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")

        elif self.info.format == PIXEL_FORMAT_BC1:
            # BC1/DXT1 compression
            if not HAS_TEXTURE_DECODER:
                raise ImportError("texture2ddecoder not available")
            decoded = texture2ddecoder.decode_bc1(raw_data, width, height)
            return Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")

        else:
            raise NotImplementedError(
                f"Pixel format {self.info.get_format_name()} not supported"
            )


def load_texture(data: bytes) -> Optional[MessiahTexture]:
    """Load a MESSIAH texture from data."""
    try:
        return MessiahTexture(data)
    except Exception:
        return None


def decode_texture(data: bytes, mip_level: int = -1) -> Optional[Image.Image]:
    """
    Decode texture data to PIL Image.

    Args:
        data: Raw texture file bytes
        mip_level: Which mipmap level to decode. Use -1 (default) to auto-select
                   the highest resolution slice.

    Returns:
        PIL Image or None if decoding fails
    """
    texture = load_texture(data)
    if texture:
        try:
            if mip_level == -1:
                # Auto-select highest resolution: use last slice (largest dimensions)
                mip_level = len(texture.slices) - 1
            return texture.decode(mip_level)
        except Exception:
            return None
    return None
