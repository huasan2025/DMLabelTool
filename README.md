# MatrixTag Studio

Cross-platform industrial `Data Matrix` label generator for macOS and Windows.

This project supports:
- GUI mode for operations users
- CLI mode for batch automation
- Fixed-size industrial label rendering (`40x30 mm`, `300 DPI`)
- Data Matrix + 3-line code layout
- Safe output folder strategy (`PREFIX-YYYYMMDD`, auto suffix `(1)`, `(2)`...)

## Features

- Single-batch GUI workflow:
  - Line 1: prefix (manual input)
  - Line 2: middle code (default `4000`)
  - Line 3: start serial (default `0035`)
  - Quantity as total count
- CLI range workflow:
  - Separate ranges per prefix (`--ld-range`, `--rd-range`, `--fd-range`, `--bd-range`)
- Deterministic file naming:
  - Filename = full code string
  - No silent rename inside one batch
- Persistent GUI settings:
  - Output root and optional font path saved in user config file

## Project Structure

- `src/dm_label_tool/core.py`: label/DM generation and validation
- `src/dm_label_tool/gui.py`: Tkinter GUI
- `src/dm_label_tool/cli.py`: CLI parsing and execution
- `src/dm_label_tool/config.py`: user config persistence
- `dm_label_generator.py`: backward-compatible launcher
- `examples/`: reference images

## Requirements

- Python `3.10+`
- `Pillow`
- `pylibdmtx`
- Runtime `libdmtx` shared library

### macOS runtime dependency

```bash
brew install libdmtx
```

### Windows runtime dependency

Install `libdmtx` DLL and make sure it is available in `PATH` or bundled with the executable.

## Quick Start

### 1) Install

```bash
cd /path/to/Codex
python3 -m pip install -r requirements.txt
```

### 2) Launch GUI

```bash
python3 dm_label_generator.py --gui
```

If you only run `python3 dm_label_generator.py`, GUI is default unless CLI flags are provided.

### 3) Run CLI

```bash
python3 dm_label_generator.py --cli \
  --ld-range 75-80 \
  --rd-range 100-120 \
  --middle-code 4000 \
  --output ./dist_output
```

## Packaging (PyInstaller)

Install build dependency:

```bash
python3 -m pip install pyinstaller
```

Build GUI app:

```bash
pyinstaller packaging/dm_label_tool_gui.spec
```

Build CLI executable:

```bash
pyinstaller --name dm-label-cli --onefile dm_label_generator.py
```

## GitHub Releases (MVP)

The workflow in `.github/workflows/release.yml` builds artifacts on:
- `macos-latest`
- `windows-latest`

Trigger by tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## FAQ

### GUI does not start and shows dependency error

`pylibdmtx` could not load `libdmtx`. Install runtime dependencies first.

### Why new folder name has `(1)` suffix

To avoid mixing multiple runs from the same day.  
Example: `LD-20260311`, then `LD-20260311(1)`.

### Is quantity interpreted as range span or total count?

Total count.  
`start=0035`, `quantity=1000` produces `...0035` through `...1034`.

## License

MIT. See `LICENSE`.
