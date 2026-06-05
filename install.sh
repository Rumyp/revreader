#!/usr/bin/env bash
set -euo pipefail

# Simple cross-platform installer wrapper (Linux / macOS).
# Strategy: prefer pip (user install), fall back to platform package manager (Arch AUR),
# and provide guidance if neither available. This script is safe to run via:
# curl -sL https://github.com/Rumyp/revreader/raw/main/install.sh | sh

info(){ printf "[revreader] %s\n" "$*" >&2; }

OS=$(uname -s)
ARCH=$(uname -m)

# Try pip3 first
if command -v pip3 >/dev/null 2>&1; then
  info "Installing revreader via pip (user install)..."
  pip3 install --user --upgrade revreader || {
    info "pip install failed; attempting --break-system-packages fallback..."
    pip3 install --upgrade revreader || true
  }
  BIN_DIR="$(python3 -m site --user-base 2>/dev/null)/bin"
  if [ -x "$BIN_DIR/revreader" ]; then
    info "Installed to $BIN_DIR/revreader"
    info "Ensure $BIN_DIR is in your PATH (export PATH=\"$BIN_DIR:\$PATH\")"
    exit 0
  fi
fi

# Arch Linux (AUR) via paru/pamac
if [ -f /etc/arch-release ] || grep -qi arch /etc/os-release 2>/dev/null; then
  if command -v paru >/dev/null 2>&1; then
    info "Installing revreader from AUR with paru..."
    paru -S --noconfirm revreader
    exit 0
  fi
  if command -v yay >/dev/null 2>&1; then
    info "Installing revreader from AUR with yay..."
    yay -S --noconfirm revreader
    exit 0
  fi
fi

# macOS: try Homebrew if available
if [ "$OS" = "Darwin" ]; then
  if command -v brew >/dev/null 2>&1; then
    info "If a Homebrew formula exists, you can: brew install revreader"
    info "Falling back to pip..."
    if command -v pip3 >/dev/null 2>&1; then
      pip3 install --user --upgrade revreader
      exit 0
    fi
  fi
fi

info "Automatic installer couldn't find a suitable method.\nOptions:\n - Install via pip: python3 -m pip install --user revreader\n - Arch: use paru -S revreader (AUR)\n - Windows: use the PowerShell installer (install.ps1) or winget if available"
exit 1
