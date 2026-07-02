#!/usr/bin/env bash
# ==========================================================
#  rain's launcher — Linux Installer
#
#  Usage (from a cloned repo):
#      ./install.sh
#
#  Usage (one-liner, no clone needed):
#      curl -fsSL https://raw.githubusercontent.com/robinvinconneau-ship-it/Rain-Launcher/main/install.sh | bash
#
#  This installer will:
#    - detect your Linux distro / package manager
#    - install python3, tkinter, Pillow and Wine if missing
#    - install the app into ~/.local/share/rains-launcher
#    - create a `rain` command in ~/.local/bin
#    - add a desktop entry so it shows up in your app menu
#    - launch the app, detached from the terminal
#
#  Do NOT run this script with sudo. It will ask for sudo itself
#  only when it needs to install system packages.
# ==========================================================
set -euo pipefail

REPO_RAW_URL="https://raw.githubusercontent.com/robinvinconneau-ship-it/Rain-Launcher/main"
APP_PY_NAME="RainLauncher.py"

BOLD="\033[1m"; DIM="\033[2m"; RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; RESET="\033[0m"
info()  { echo -e "${BOLD}==>${RESET} $1"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $1"; }
ok()    { echo -e "${GREEN}✔${RESET} $1"; }
fail()  { echo -e "${RED}✘ $1${RESET}"; exit 1; }

# ---------------------------------------------------------------------------
# 0. Safety: never run as root
# ---------------------------------------------------------------------------
if [ "${EUID}" -eq 0 ]; then
    fail "Don't run this installer with sudo/root. It must install into your own \$HOME.
      Just run: ./install.sh
      (It will call sudo itself, only for package installation.)"
fi

PY="python3"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

INSTALL_DIR="$HOME/.local/share/rains-launcher"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
APP_FILE="$INSTALL_DIR/$APP_PY_NAME"
CMD_FILE="$BIN_DIR/rain"
DESKTOP_FILE="$DESKTOP_DIR/rains-launcher.desktop"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"

# ---------------------------------------------------------------------------
# 1. Detect package manager from /etc/os-release
# ---------------------------------------------------------------------------
info "Detecting your Linux distribution..."
PKG_MANAGER=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "${ID:-}${ID_LIKE:-}" in
        *arch*)             PKG_MANAGER="pacman" ;;
        *debian*|*ubuntu*)  PKG_MANAGER="apt"     ;;
        *fedora*|*rhel*)    PKG_MANAGER="dnf"     ;;
        *suse*)             PKG_MANAGER="zypper"  ;;
    esac
fi
if [ -z "$PKG_MANAGER" ]; then
    if command -v pacman &> /dev/null; then PKG_MANAGER="pacman"
    elif command -v dnf &> /dev/null;    then PKG_MANAGER="dnf"
    elif command -v zypper &> /dev/null; then PKG_MANAGER="zypper"
    elif command -v apt &> /dev/null;    then PKG_MANAGER="apt"
    fi
fi
ok "Package manager: ${PKG_MANAGER:-unknown}"

pkg_install() {
    # usage: pkg_install pacman-pkg apt-pkg dnf-pkg zypper-pkg
    local p_pacman="$1" p_apt="$2" p_dnf="$3" p_zypper="$4"
    case "$PKG_MANAGER" in
        pacman) sudo pacman -Sy --noconfirm $p_pacman ;;
        apt)    sudo apt-get update -qq && sudo apt-get install -y $p_apt ;;
        dnf)    sudo dnf install -y $p_dnf ;;
        zypper) sudo zypper install -y $p_zypper ;;
        *) warn "Unknown package manager, please install manually: $p_pacman / $p_apt / $p_dnf / $p_zypper"; return 1 ;;
    esac
}

# ---------------------------------------------------------------------------
# 2. python3
# ---------------------------------------------------------------------------
info "Checking python3..."
if ! command -v "$PY" &> /dev/null; then
    warn "python3 not found, installing..."
    pkg_install "python" "python3" "python3" "python3" || fail "Could not install python3 automatically."
fi
ok "python3 found: $($PY --version)"

# ---------------------------------------------------------------------------
# 3. tkinter
# ---------------------------------------------------------------------------
info "Checking tkinter..."
if ! $PY -c "import tkinter" &> /dev/null; then
    warn "tkinter missing, installing..."
    pkg_install "tk" "python3-tk" "python3-tkinter" "python3-tk" \
        || fail "Could not install tkinter automatically. Install it manually then re-run this script."
fi
ok "tkinter available"

# ---------------------------------------------------------------------------
# 4. Pillow
# ---------------------------------------------------------------------------
info "Checking Pillow..."
if ! $PY -c "import PIL" &> /dev/null; then
    warn "Pillow missing, installing..."
    pkg_install "python-pillow" "python3-pil python3-pil.imagetk" "python3-pillow" "python3-Pillow" || true
    if ! $PY -c "import PIL" &> /dev/null; then
        $PY -m pip install --user --break-system-packages Pillow 2>/dev/null \
            || $PY -m pip install --user Pillow \
            || pip3 install --user Pillow \
            || fail "Could not install Pillow automatically."
    fi
fi
ok "Pillow available"

# ---------------------------------------------------------------------------
# 5. Wine (needed to launch .exe games on Linux)
# ---------------------------------------------------------------------------
info "Checking Wine..."
if ! command -v wine &> /dev/null; then
    warn "Wine missing, installing (this can take a while)..."
    if [ "$PKG_MANAGER" = "pacman" ]; then
        sudo pacman -Sy --noconfirm wine winetricks 2>/dev/null \
            || warn "Could not install wine automatically. On Arch-based systems you may need to enable the [multilib] repo in /etc/pacman.conf, then run: sudo pacman -S wine winetricks"
    else
        pkg_install "wine winetricks" "wine winetricks" "wine winetricks" "wine winetricks" \
            || warn "Could not install wine automatically. Install it manually: https://www.winehq.org"
    fi
fi
if command -v wine &> /dev/null; then
    ok "Wine available"
else
    warn "Wine still not available. .exe games won't launch until it's installed."
fi

# ---------------------------------------------------------------------------
# 6. Fetch the app itself (RainLauncher.py)
#    Uses the local copy if run from a cloned repo, otherwise downloads it.
# ---------------------------------------------------------------------------
info "Installing rain's launcher into $INSTALL_DIR ..."
if [ -f "$SCRIPT_DIR/$APP_PY_NAME" ]; then
    cp "$SCRIPT_DIR/$APP_PY_NAME" "$APP_FILE"
else
    info "Local $APP_PY_NAME not found next to this script, downloading from GitHub..."
    if command -v curl &> /dev/null; then
        curl -fsSL "$REPO_RAW_URL/$APP_PY_NAME" -o "$APP_FILE"
    elif command -v wget &> /dev/null; then
        wget -q "$REPO_RAW_URL/$APP_PY_NAME" -O "$APP_FILE"
    else
        fail "Neither curl nor wget is available to download $APP_PY_NAME."
    fi
fi
$PY -m py_compile "$APP_FILE" || fail "Downloaded/copied $APP_PY_NAME failed to compile."
ok "App installed"

# ---------------------------------------------------------------------------
# 7. Create the `rain` command
# ---------------------------------------------------------------------------
info "Creating the 'rain' command..."
cat > "$CMD_FILE" << CMDEOF
#!/usr/bin/env bash
# Launches rain's launcher in the background, detached from the terminal.
setsid "$PY" "$APP_FILE" >/dev/null 2>&1 < /dev/null &
disown
CMDEOF
chmod +x "$CMD_FILE"
ok "Command installed at $CMD_FILE"

# ---------------------------------------------------------------------------
# 8. Desktop entry (app menu)
# ---------------------------------------------------------------------------
info "Creating application menu entry..."
cat > "$DESKTOP_FILE" << DESKEOF
[Desktop Entry]
Type=Application
Name=rain's launcher
Comment=Game launcher
Exec=$CMD_FILE
Icon=applications-games
Terminal=false
Categories=Game;
DESKEOF
chmod +x "$DESKTOP_FILE"
ok "Desktop entry created"

# ---------------------------------------------------------------------------
# 9. Make sure ~/.local/bin is on PATH (bash / zsh / fish)
# ---------------------------------------------------------------------------
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR is not on your PATH."
    SHELL_NAME="$(basename "${SHELL:-bash}")"
    case "$SHELL_NAME" in
        fish)
            FISH_CONF="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$FISH_CONF")"
            if ! grep -q '.local/bin' "$FISH_CONF" 2>/dev/null; then
                echo 'set -gx PATH $HOME/.local/bin $PATH' >> "$FISH_CONF"
                info "Added to $FISH_CONF (fish). Open a new terminal for the 'rain' command to work."
            fi
            ;;
        zsh)
            SHELL_RC="$HOME/.zshrc"
            if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
                info "Added to $SHELL_RC. Open a new terminal (or run: source $SHELL_RC)."
            fi
            ;;
        *)
            SHELL_RC="$HOME/.bashrc"
            if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
                info "Added to $SHELL_RC. Open a new terminal (or run: source $SHELL_RC)."
            fi
            ;;
    esac
fi

# ---------------------------------------------------------------------------
# 10. Done — launch once, detached
# ---------------------------------------------------------------------------
echo ""
ok "Installed! Next time, just run:  rain"
echo -e "${DIM}  (or search for \"rain's launcher\" in your application menu)${RESET}"
echo ""
info "Launching rain's launcher now (terminal will be freed)..."
setsid "$PY" "$APP_FILE" >/dev/null 2>&1 < /dev/null &
disown
sleep 1
exit 0
