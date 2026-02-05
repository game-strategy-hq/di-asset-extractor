# Diablo Immortal Asset Extractor

Extract sprite images from Diablo Immortal game files. This tool reads the game's MPK archives and exports individual sprite PNGs.

## What This Does

- Extracts ~50,000+ sprite images from the Windows version of Diablo Immortal
- Outputs individual PNG files with transparency
- Handles texture decompression (LZ4, BC7, ASTC)
- Parses Cocos2d sprite atlas definitions

## Quick Start (Windows)

### 1. Install Git

Download and install Git from: https://git-scm.com/download/win

Click "Next" through all the options (defaults are fine).

**Close and reopen PowerShell after installing Git.**

### 2. Install uv

uv is a fast Python package manager that automatically handles Python for you - no need to install Python separately.

Open **PowerShell** and run:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Close and reopen PowerShell after installing.**

### 3. Install the extractor

```powershell
uv tool install git+https://github.com/game-strategy-hq/di-asset-extractor
```

## Quick Start (macOS/Linux)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal, then install the extractor
uv tool install git+https://github.com/game-strategy-hq/di-asset-extractor
```

### 4. Run the extraction

```powershell
di-extract "C:\Program Files (x86)\Diablo Immortal\Package\MPK"
```

This creates a `sprites` folder in your current directory with all the extracted images.

## Finding Your Game Files

The tool needs the `Package\MPK` folder inside your Diablo Immortal installation.

**Typical Windows path:**
```
C:\Program Files (x86)\Diablo Immortal\Package\MPK
```

This folder should contain:
- `Resources.mpkinfo`
- `Resources.mpk`
- `Resources1.mpk`, `Resources2.mpk`, etc.

## Usage

### Extracting Sprites

```
di-extract <MPKS_DIR> [OUTPUT_DIR]

Arguments:
  MPKS_DIR    Directory containing Resources.mpkinfo and .mpk files
  OUTPUT_DIR  Directory to save extracted sprite PNGs (default: ./sprites)

Options:
  --help      Show help message
  --version   Show version number
```

### Searching for Sprites

Find similar sprites by providing a screenshot or image:

```
di-search <SCREENSHOT> [SPRITES_DIR] [--top N] [--rebuild]

Arguments:
  SCREENSHOT   Path to screenshot/image to search for
  SPRITES_DIR  Directory containing extracted sprites (default: ./sprites)

Options:
  --top N      Number of results to return (default: 30)
  --rebuild    Force rebuild the search index
  --help       Show help message
  --version    Show version number
```

Results are copied to a `search-results/` folder next to your sprites directory, named with rank prefixes (e.g., `01_sprite.png`, `02_sprite.png`).

## Examples

```bash
# Extract to ./sprites (default)
di-extract "C:\Program Files (x86)\Diablo Immortal\Package\MPK"

# Extract to a custom folder
di-extract "C:\Program Files (x86)\Diablo Immortal\Package\MPK" .\my-sprites

# Search for a sprite using a screenshot
di-search screenshot.png ./sprites

# Search with more results
di-search screenshot.png ./sprites --top 50
```

## Output

The tool creates a flat directory of PNG files:
```
sprites/
  Skillicon_barbarian_1.png
  Skillicon_barbarian_2.png
  Itemicon_weapon_sword.png
  ...
```

Duplicate names are handled by appending `_1`, `_2`, etc.

## Troubleshooting

**"Resources.mpkinfo not found"**
- Make sure you're pointing to the correct game directory
- The directory should contain `Resources.mpkinfo` and `.mpk` files

**"texture2ddecoder not available"**
- The tool should install this automatically
- If issues persist, try: `uv tool install --reinstall git+https://github.com/game-strategy-hq/di-asset-extractor`

**Extraction is slow**
- Normal! There are tens of thousands of sprites
- Progress is shown as a percentage

## Development

```bash
# Clone the repo
git clone https://github.com/game-strategy-hq/di-asset-extractor
cd di-asset-extractor

# Run locally
uv run di-extract --help

# Install locally for testing
uv tool install .
```

## License

MIT
