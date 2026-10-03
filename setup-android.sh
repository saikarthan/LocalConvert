#!/usr/bin/env bash
# =============================================================
#  localconvert — Android / Termux setup  (run once)
#  Tested on: Termux from F-Droid, Android 10+
# =============================================================
set -e

BOLD=$(tput bold 2>/dev/null || true)
RESET=$(tput sgr0 2>/dev/null || true)
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}${BOLD}[+]${RESET} $*"; }
warn()  { echo -e "${YELLOW}${BOLD}[!]${RESET} $*"; }
error() { echo -e "${RED}${BOLD}[x]${RESET} $*"; }
step()  { echo; echo -e "${BOLD}─── $* ───${RESET}"; }

# ── Guard: must be inside Termux ──────────────────────────────
if [[ ! -d "/data/data/com.termux" ]]; then
    error "This script must be run inside Termux."
    error "Install Termux from F-Droid: https://f-droid.org/packages/com.termux/"
    exit 1
fi

echo
echo "  ██╗      ██████╗  ██████╗ █████╗ ██╗      ██████╗ ██████╗ "
echo "  ██║     ██╔═══██╗██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗"
echo "  ██║     ██║   ██║██║     ███████║██║     ██║     ██║   ██║"
echo "  ██║     ██║   ██║██║     ██╔══██║██║     ██║     ██║   ██║"
echo "  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗╚██████╗╚██████╔╝"
echo "  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ "
echo "         Android setup — everything runs on this phone"
echo

# ── 1. Package manager update ─────────────────────────────────
step "Updating Termux packages"
pkg update -y && pkg upgrade -y

# ── 2. System-level dependencies ──────────────────────────────
step "Installing system libraries"
pkg install -y \
    python \
    git \
    ffmpeg \
    tesseract \
    clang \
    make \
    pkg-config \
    libffi \
    openssl \
    libjpeg-turbo \
    libpng \
    libtiff \
    libwebp \
    zlib

# tesseract English data (other langs: tesseract-lang-fra, tesseract-lang-deu, etc.)
pkg install -y tesseract-lang || warn "tesseract language packs not found — English should still work"

# optional HEIC support
pkg install -y libheif || warn "libheif not available — HEIC tool will be skipped"

# ── 3. pip upgrade ────────────────────────────────────────────
step "Upgrading pip"
pip install --upgrade pip setuptools wheel

# ── 4. Python packages ────────────────────────────────────────
step "Installing Python packages (may take a few minutes)"

PKGS=(
    "flask"
    "pypdf>=4.0"
    "pymupdf>=1.24"
    "pillow>=10.0"
    "reportlab>=4.0"
    "python-pptx"
    "qrcode[pil]"
    "cryptography"
    "pytesseract"
    "pdf2docx>=0.5.8"
)

for pkg in "${PKGS[@]}"; do
    info "Installing $pkg"
    pip install "$pkg" || warn "  Failed: $pkg — that tool may be unavailable"
done

# Optional / may not build on all devices
for pkg in "pillow-heif" "imageio-ffmpeg"; do
    pip install "$pkg" 2>/dev/null && info "Installed $pkg" || warn "Optional $pkg not available — skipping"
done

# ── 5. Termux widget shortcut ─────────────────────────────────
step "Creating Termux widget shortcut"

SHORTCUTS_DIR="$HOME/.shortcuts"
mkdir -p "$SHORTCUTS_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat > "$SHORTCUTS_DIR/localconvert" << SHORTCUT
#!/usr/bin/env bash
# LocalConvert — tap to start
cd "$SCRIPT_DIR"
python app.py &
SERVER_PID=\$!
sleep 2
# Open in browser (requires Termux:API app from F-Droid)
termux-open-url http://127.0.0.1:5001 2>/dev/null || true
echo
echo "LocalConvert running at http://127.0.0.1:5001"
echo "Open Chrome/Firefox and go to that address if the browser did not open."
echo "Press Ctrl+C to stop the server."
wait \$SERVER_PID
SHORTCUT

chmod +x "$SHORTCUTS_DIR/localconvert"
info "Shortcut created at $SHORTCUTS_DIR/localconvert"

# ── 6. run-android.sh ─────────────────────────────────────────
step "Done!"
echo
echo "  ✅  Setup complete."
echo
echo "  ▶  To start now:          bash run-android.sh"
echo "  ▶  One-tap after restart: install 'Termux:Widget' from F-Droid,"
echo "     add the widget to your home screen, tap 'localconvert'."
echo
echo "  🌐  Then open Chrome and go to:  http://127.0.0.1:5001"
echo
warn "  Tip: install 'Termux:API' from F-Droid so the browser"
warn "  opens automatically when you start the server."
echo
