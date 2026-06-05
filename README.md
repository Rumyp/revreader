![revreader](https://img.shields.io/badge/revreader-EPUB%20reader-000000?style=for-the-badge&logo=readthedocs&logoColor=00ff00) ![python](https://img.shields.io/badge/python-3.11+-000000?style=for-the-badge&logo=python&logoColor=00ff00) ![license](https://img.shields.io/github/license/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![stars](https://img.shields.io/github/stars/Rumyp/revreader?style=for-the-badge&color=000000&logoColor=00ff00) ![linux](https://img.shields.io/badge/Linux-AUR-000000?style=for-the-badge&logo=linux&logoColor=00ff00) ![windows](https://img.shields.io/badge/Windows-winget-000000?style=for-the-badge&logo=windows&logoColor=00ff00)

revreader — compact terminal + GUI EPUB reader.

Installation

- AUR (Arch Linux):
  - paru (recommended): paru -S revreader
  - yay: yay -S revreader

- pip (cross-platform):
  python3 -m pip install --user revreader

- Quick installer (curl) — Linux / macOS:
  curl -sL https://github.com/Rumyp/revreader/raw/main/install.sh | sh

- Quick installer (PowerShell) — Windows:
  iwr -useb https://github.com/Rumyp/revreader/raw/main/install.ps1 | iex

- winget (Windows):
  winget install --id revreader

Manual Windows installer

- If a signed installer is provided in Releases, download it and run.
- Verify SHA256 before running: sha256sum revreader-setup.exe

CI / Releases

- Recommended: GitHub Actions builds Windows EXE (PyInstaller + NSIS) and attaches artifacts to Releases. Add PYPI_API_TOKEN to repo secrets to enable PyPI publishing.

Usage

- GUI: revreader mybook.epub
- Terminal: revreader -t mybook.epub

Verify installation

- Which binary: command -v revreader (Linux/macOS) or Get-Command revreader (PowerShell).

Security

- Inspect install.sh / install.ps1 before running. The curl|sh and iwr|iex patterns execute remote code — use only from trusted sources.

License

MIT — see LICENSE

Author

rumyp — v1.0.1 (revreader)

