![revreader](https://img.shields.io/badge/revreader-EPUB%20reader-000000?style=for-the-badge&logo=readthedocs&logoColor=00ff00) ![python](https://img.shields.io/badge/python-3.11+-000000?style=for-the-badge&logo=python&logoColor=00ff00) ![license](https://img.shields.io/github/license/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![stars](https://img.shields.io/github/stars/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![linux](https://img.shields.io/badge/Linux-AUR-000000?style=for-the-badge&logo=linux&logoColor=00ff00) ![windows](https://img.shields.io/badge/Windows-winget-000000?style=for-the-badge&logo=windows&logoColor=00ff00)

![revreader](https://img.shields.io/badge/revreader-EPUB%20reader-000000?style=for-the-badge&logo=readthedocs&logoColor=00ff00) ![python](https://img.shields.io/badge/python-3.11+-000000?style=for-the-badge&logo=python&logoColor=00ff00) ![license](https://img.shields.io/github/license/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![stars](https://img.shields.io/github/stars/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![linux](https://img.shields.io/badge/Linux-AUR-000000?style=for-the-badge&logo=linux&logoColor=00ff00) ![windows](https://img.shields.io/badge/Windows-winget-000000?style=for-the-badge&logo=windows&logoColor=00ff00)

# revreader

Compact terminal + GUI EPUB reader.

## Installation

### AUR (Arch Linux)

- paru (recommended):

```bash
paru -S revreader
```

- yay:

```bash
yay -S revreader
```

### pip (cross-platform)

```bash
python3 -m pip install --user revreader
```

### Quick installer (curl) — Linux / macOS

```bash
curl -sL https://github.com/Rumyp/revreader/raw/main/install.sh | sh
```

### Quick installer (PowerShell) — Windows

```powershell
iwr -useb https://github.com/Rumyp/revreader/raw/main/install.ps1 | iex
```

### winget (Windows)

```powershell
winget install --id revreader
```

## Manual Windows installer

If a signed installer is attached to Releases, download and run it.

Verify SHA256 before running:

```bash
sha256sum revreader-setup.exe
```

## CI / Releases

Recommended: use GitHub Actions (windows-latest) to build a PyInstaller EXE and NSIS installer, upload artifacts to Releases, and publish to PyPI (add PYPI_API_TOKEN to repo secrets).

## Usage

- GUI:

```bash
revreader mybook.epub
```

- Terminal:

```bash
revreader -t mybook.epub
```

## Verify installation

- Linux/macOS:

```bash
command -v revreader
```

- PowerShell:

```powershell
Get-Command revreader
```

## Security

Inspect install.sh and install.ps1 before executing. Running remote scripts with curl|sh or iwr|iex runs code from the network—use only trusted sources.

## License

MIT — see LICENSE

## Author

rumyp — v1.0.1 (revreader)

