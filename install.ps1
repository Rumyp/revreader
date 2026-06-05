<#
PowerShell installer for Windows.
Usage (PowerShell admin recommended):
  iwr -useb https://github.com/Rumyp/revreader/raw/main/install.ps1 | iex

Strategy: try winget, then pip, then download installer from GitHub Releases if present.
#>

function Info($msg){ Write-Host "[revreader] $msg" }

try {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Info "Attempting install with winget..."
    winget install --id revreader --accept-source-agreements --accept-package-agreements
    exit 0
  }
} catch {}

# Try pip
try {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    Info "Installing via pip..."
    python -m pip install --user --upgrade revreader
    exit 0
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    Info "Installing via py -m pip..."
    py -m pip install --user --upgrade revreader
    exit 0
  }
} catch {}

# Fallback: download installer from GitHub Releases (if one exists)
$assetUrl = "https://github.com/Rumyp/revreader/releases/latest/download/revreader-windows-x86_64-installer.exe"
$dest = "$env:TEMP\revreader-installer.exe"
try {
  Info "Attempting to download installer from $assetUrl"
  Invoke-WebRequest -Uri $assetUrl -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Info "Running installer..."
  Start-Process -FilePath $dest -Wait -Verb RunAs
  exit 0
} catch {
  Info "Could not download or run installer. Please install manually (winget or pip)."
  exit 1
}
