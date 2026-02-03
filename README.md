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

Use the default options during installation.

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
di-extract "C:\Program Files (x86)\Diablo Immortal\Package\MPK" .\sprites
```

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

```
di-extract <MPKS_DIR> <OUTPUT_DIR>

Arguments:
  MPKS_DIR    Directory containing Resources.mpkinfo and .mpk files
  OUTPUT_DIR  Directory to save extracted sprite PNGs

Options:
  --help      Show help message
  --version   Show version number
```

## Examples

```bash
# Windows - outputs to a "sprites" folder in your current directory
di-extract "C:\Program Files (x86)\Diablo Immortal\Package\MPK" .\sprites

# macOS/Linux (if you have the game files copied)
di-extract ~/Games/DiabloImmortal/Package/MPK ./sprites
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
