# Rain-Launcher

Im a bit new in the world of tech, so i wanted to do a little project called
"rain launcher" — it's basically a launcher of `.exe` games with a simple gui.

- **Windows**: fully supported, see [Releases](https://github.com/robinvinconneau-ship-it/Rain-Launcher/releases)
  for a ready-to-use build, or just run `RainLauncher.py` with Python.
- **Linux**: supported via the installer below — `.exe` games are launched
  automatically through [Wine](https://www.winehq.org).
- There's also a **Lite version** (`Launcher Lite.py`) for a faster startup,
  for people who don't care about a clean and beautiful gui.

## Linux install

```bash
git clone https://github.com/robinvinconneau-ship-it/-Rain-s-Launcher-.git
cd -Rain-s-Launcher-
chmod +x install.sh
./install.sh
```

Or, one-liner (no clone needed):

```bash
curl -fsSL https://raw.githubusercontent.com/robinvinconneau-ship-it/Rain-Launcher/main/install.sh | bash
```

**Do not run the installer with `sudo`.** It installs into your own `$HOME`
and calls `sudo` itself only when it needs to install system packages.

The installer will:
- Detect your distro (`apt`, `pacman`, `dnf`, `zypper`) and install
  `python3`, `tkinter`, `Pillow` and `Wine` if missing.
- Install the app into `~/.local/share/rains-launcher`.
- Create a `rain` command in `~/.local/bin`.
- Add a desktop entry so it shows up in your application menu.
- Launch it once, detached from the terminal.

After installing, open a new terminal and just run:

```bash
rain
```

or launch it from your application menu.

## Windows

Grab the `.exe` from the [Releases](https://github.com/robinvinconneau-ship-it/Rain-Launcher/releases)
page, or run `RainLauncher.py` directly with Python 3 + `pip install pillow`.

## Notes

- On Linux, `.exe` games are launched through Wine automatically.
- On Arch-based distros, Wine may need the `[multilib]` repo enabled in
  `/etc/pacman.conf` for full functionality.
- Data is stored in `~/.rains_games.json`, `~/.rains_config.json` and
  `~/.rains_icons/` (or the Windows equivalents under your user profile).

## THANKS AGAIN USING MY SHII
