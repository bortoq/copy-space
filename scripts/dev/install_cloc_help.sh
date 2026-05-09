#!/bin/sh
set -eu

if command -v cloc >/dev/null 2>&1; then
  echo "OK: cloc found: $(command -v cloc)"
  cloc --version
  exit 0
fi

echo "cloc is not installed."
echo ""
echo "Install options:"
echo ""
echo "Ubuntu/Debian:"
echo "  sudo apt-get update && sudo apt-get install -y cloc"
echo ""
echo "Fedora:"
echo "  sudo dnf install -y cloc"
echo ""
echo "Arch:"
echo "  sudo pacman -S cloc"
echo ""
echo "macOS (Homebrew):"
echo "  brew install cloc"
echo ""
echo "Windows (Chocolatey):"
echo "  choco install cloc"
echo ""
echo "If you cannot install packages:"
echo "  cloc is a single Perl script; you can run it via perl if available."
echo "  See: https://github.com/AlDanial/cloc"
exit 1
