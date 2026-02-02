"""Resource repository parser for Diablo Immortal game files."""

import struct


class ResourceEntry:
    """Represents a single resource in the repository."""

    def __init__(
        self,
        logical_name: str,
        hash_bytes: bytes,
        folder_index: int,
        type_index: int,
    ):
        self.logical_name = logical_name
        self.hash_bytes = hash_bytes
        self.folder_index = folder_index
        self.type_index = type_index

    def get_guid_path(self) -> str:
        """
        Convert the 16-byte hash to a GUID path.

        The first byte appears twice - once as the directory name,
        and again at the start of the GUID filename.

        Example: [0c, 36, 39, 8b, ...] -> "0c/0c36398b-90f9-47cb-b98f-6e469a788c2e"
        """
        h = self.hash_bytes
        return (
            f"{h[0]:02x}/"
            f"{h[0]:02x}{h[1]:02x}{h[2]:02x}{h[3]:02x}-"
            f"{h[4]:02x}{h[5]:02x}-"
            f"{h[6]:02x}{h[7]:02x}-"
            f"{h[8]:02x}{h[9]:02x}-"
            f"{h[10]:02x}{h[11]:02x}{h[12]:02x}{h[13]:02x}{h[14]:02x}{h[15]:02x}"
        )


class ResourceRepository:
    """Parser for resource.repository files."""

    def __init__(self, data: bytes):
        """Initialize repository from decompressed data."""
        self.data = data
        self.resource_types: list[str] = []
        self.folder_paths: list[str] = []
        self.entries: list[ResourceEntry] = []
        self._parse()

    def _parse(self):
        """Parse the repository binary format."""
        offset = 0

        # Read header
        version = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4

        unknown_flag1 = struct.unpack_from("<H", self.data, offset)[0]
        offset += 2

        unknown_flag2 = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4

        # Read resource types string
        types_length = struct.unpack_from("<H", self.data, offset)[0]
        offset += 2

        types_bytes = self.data[offset : offset + types_length]
        offset += types_length

        types_str = types_bytes.decode("utf-8", errors="replace")
        self.resource_types = types_str.split(";")

        # Read folder paths string
        paths_length = struct.unpack_from("<H", self.data, offset)[0]
        offset += 2

        paths_bytes = self.data[offset : offset + paths_length]
        offset += paths_length

        paths_str = paths_bytes.decode("utf-8", errors="replace")
        self.folder_paths = paths_str.split(";")

        # Read file entries until EOF
        while offset < len(self.data):
            try:
                # Read entry header
                unknown1 = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                unknown2 = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                flag = self.data[offset]
                offset += 1

                # Read 16-byte hash
                hash_bytes = self.data[offset : offset + 16]
                offset += 16

                # Read logical name
                name_length = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                name_bytes = self.data[offset : offset + name_length]
                offset += name_length

                logical_name = name_bytes.decode("utf-8", errors="replace")

                # Read folder and type indices
                folder_index = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                type_index = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                # Read related hashes (and skip them)
                related_count = struct.unpack_from("<H", self.data, offset)[0]
                offset += 2

                # Skip related hashes (16 bytes each)
                offset += related_count * 16

                # Create entry
                entry = ResourceEntry(
                    logical_name=logical_name,
                    hash_bytes=hash_bytes,
                    folder_index=folder_index,
                    type_index=type_index,
                )
                self.entries.append(entry)

            except (struct.error, IndexError):
                # Reached end of file or corrupt data
                break

    def find_by_name(self, name: str, exact: bool = False) -> list[ResourceEntry]:
        """Find entries by logical name."""
        if exact:
            return [e for e in self.entries if e.logical_name == name]
        else:
            name_lower = name.lower()
            return [e for e in self.entries if name_lower in e.logical_name.lower()]

    def find_by_type(self, type_name: str) -> list[ResourceEntry]:
        """Find all entries of a specific resource type."""
        try:
            type_index = self.resource_types.index(type_name)
            return [e for e in self.entries if e.type_index == type_index]
        except ValueError:
            return []

    def get_entry_info(self, entry: ResourceEntry) -> dict:
        """Get detailed information about an entry."""
        resource_type = (
            self.resource_types[entry.type_index]
            if entry.type_index < len(self.resource_types)
            else f"Unknown({entry.type_index})"
        )

        folder_path = (
            self.folder_paths[entry.folder_index]
            if entry.folder_index < len(self.folder_paths)
            else f"Unknown({entry.folder_index})"
        )

        return {
            "logical_name": entry.logical_name,
            "guid_path": entry.get_guid_path(),
            "resource_type": resource_type,
            "folder_path": folder_path,
            "hash_hex": entry.hash_bytes.hex(),
        }


def parse_repository(data: bytes) -> ResourceRepository:
    """Parse a resource.repository file."""
    return ResourceRepository(data)
