#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, os, sys, stat, subprocess, hashlib, threading, queue
import urllib.request, urllib.parse, io
from PIL import Image, ImageTk, ImageDraw, ImageFont


HOME       = os.path.expanduser("~")
DATA_FILE  = os.path.join(HOME, ".rains_games.json")
ICON_CACHE = os.path.join(HOME, ".rains_icons")
CFG_FILE   = os.path.join(HOME, ".rains_config.json")
os.makedirs(ICON_CACHE, exist_ok=True)


BG      = "#090909"
BG2     = "#0f0f0f"
BG3     = "#161616"
CARD    = "#121212"
CARD_H  = "#1c1c1c"
ACCENT  = "#4a9eff"
ACCENT2 = "#1d4ed8"
TEXT    = "#e0e0e0"
TEXT2   = "#666666"
TEXT3   = "#333333"
OK      = "#3ecf8e"
ERR     = "#e55353"
SEP     = "#1e1e1e"

def _ease_out(t):
    """Courbe ease-out cubique [0..1] -> [0..1]"""
    return 1 - (1 - t) ** 3

def _ease_in_out(t):
    if t < 0.5: return 4 * t * t * t
    return 1 - (-2*t + 2)**3 / 2

def lerp_color(c1, c2, t):
    """Interpolation lineaire entre deux couleurs hex."""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"

class Anim:
    FPS = 60
    _INTERVAL = 1000 // FPS  # ~16ms

    def __init__(self, root, duration, on_tick, on_done=None, ease=_ease_out, delay=0):
        self._root     = root
        self._dur      = duration
        self._tick     = on_tick
        self._done     = on_done
        self._ease     = ease
        self._elapsed  = 0
        self._running  = False
        self._after_id = None
        if delay:
            root.after(delay, self.start)
        else:
            self.start()

    def start(self):
        self._running  = True
        self._elapsed  = 0
        self._step()

    def stop(self):
        self._running = False
        if self._after_id:
            try: self._root.after_cancel(self._after_id)
            except: pass

    def _step(self):
        if not self._running: return
        try:
            self._root.winfo_exists()
        except:
            return
        self._elapsed += self._INTERVAL
        raw = min(self._elapsed / self._dur, 1.0)
        t   = self._ease(raw)
        try:
            self._tick(t)
        except tk.TclError:
            return
        if raw < 1.0:
            self._after_id = self._root.after(self._INTERVAL, self._step)
        else:
            self._running = False
            if self._done:
                try: self._done()
                except: pass

STRINGS = {
    "en": {
        "app_title":"rain's launcher","library":"Library","search":"Search",
        "settings":"Settings","add_game":"+ Add a game","launch":"\u25b6  Launch",
        "search_ph":"Search...","no_games":"No games yet",
        "no_games_sub":"Add your first game with the + button",
        "add_title":"Add a game","name_lbl":"Game name","exe_lbl":"Executable / script",
        "browse":"Browse","icon_lbl":"Custom icon (optional)","pick_img":"Pick an image",
        "cancel":"Cancel","add_btn":"Add","err_name":"Please enter a game name.",
        "err_path":"Please select an executable file.","added":"\u2714  {} added",
        "launched":"\u25b6  {} launched","removed":"Removed: {}","delete_title":"Remove",
        "delete_msg":"Remove \"{}\" from the library?","clear_title":"Confirm",
        "clear_msg":"Delete ALL games from the list?",
        "cache_cleared":"Cache cleared - covers will be re-downloaded",
        "settings_title":"Settings","data_file":"Data file","icon_cache":"Icon cache",
        "clear_cache_btn":"Clear icon cache","clear_all_btn":"Delete all games",
        "language_lbl":"Language","restart_note":"Restart the app to apply the language change.",
        "not_found_title":"File not found","not_found_msg":"The file no longer exists:\n{}",
        "not_exec_title":"Not executable","not_exec_msg":"The file is not executable.\nMake it executable now?",
        "wine_missing_title":"Wine not found","wine_missing_msg":"This is a .exe file but Wine isn't installed.\nInstall it with: sudo pacman -S wine (or apt/dnf equivalent), then restart the launcher.",
        "games_count":"{} game","games_count_pl":"{} games","v":"v1.3 (linux)",
    },
    "fr": {
        "app_title":"rain's launcher","library":"Biblioth\u00e8que","search":"Rechercher",
        "settings":"Param\u00e8tres","add_game":"\uff0b  Ajouter un jeu","launch":"\u25b6  Lancer",
        "search_ph":"Rechercher...","no_games":"Aucun jeu pour l'instant",
        "no_games_sub":"Ajoute ton premier jeu avec le bouton +",
        "add_title":"Ajouter un jeu","name_lbl":"Nom du jeu","exe_lbl":"Ex\u00e9cutable / script",
        "browse":"Parcourir","icon_lbl":"Ic\u00f4ne personnalis\u00e9e (optionnel)",
        "pick_img":"Choisir une image","cancel":"Annuler","add_btn":"Ajouter",
        "err_name":"Donne un nom au jeu.","err_path":"S\u00e9lectionne un fichier ex\u00e9cutable.",
        "added":"\u2714  {} ajout\u00e9","launched":"\u25b6  {} lanc\u00e9","removed":"Retir\u00e9 : {}",
        "delete_title":"Supprimer","delete_msg":"Retirer \u00ab {} \u00bb de la biblioth\u00e8que ?",
        "clear_title":"Confirmer","clear_msg":"Supprimer tous les jeux de la liste ?",
        "cache_cleared":"Cache vid\u00e9 - les covers seront re-t\u00e9l\u00e9charg\u00e9es",
        "settings_title":"Param\u00e8tres","data_file":"Fichier de donn\u00e9es",
        "icon_cache":"Cache des ic\u00f4nes","clear_cache_btn":"Vider le cache d'ic\u00f4nes",
        "clear_all_btn":"Supprimer tous les jeux","language_lbl":"Langue",
        "restart_note":"Red\u00e9marre l'application pour appliquer le changement.",
        "not_found_title":"Introuvable","not_found_msg":"Le fichier n'existe plus :\n{}",
        "not_exec_title":"Non ex\u00e9cutable","not_exec_msg":"Le fichier n'a pas les droits d'ex\u00e9cution.\nLes ajouter maintenant ?",
        "wine_missing_title":"Wine introuvable","wine_missing_msg":"Ce fichier est un .exe mais Wine n'est pas install\u00e9.\nInstalle-le avec : sudo pacman -S wine (ou l'\u00e9quivalent apt/dnf), puis red\u00e9marre le launcher.",
        "games_count":"{} jeu","games_count_pl":"{} jeux","v":"v1.3 (linux)",
    },
    "ru": {
        "app_title":"rain's launcher","library":"\u0411\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0430","search":"\u041f\u043e\u0438\u0441\u043a",
        "settings":"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438","add_game":"\uff0b  \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0438\u0433\u0440\u0443","launch":"\u25b6  \u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c",
        "search_ph":"\u041f\u043e\u0438\u0441\u043a...","no_games":"\u0418\u0433\u0440 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442",
        "no_games_sub":"\u0414\u043e\u0431\u0430\u0432\u044c \u043f\u0435\u0440\u0432\u0443\u044e \u0438\u0433\u0440\u0443 \u043a\u043d\u043e\u043f\u043a\u043e\u0439 +",
        "add_title":"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0438\u0433\u0440\u0443","name_lbl":"\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0438\u0433\u0440\u044b","exe_lbl":"\u0424\u0430\u0439\u043b / \u0441\u043a\u0440\u0438\u043f\u0442",
        "browse":"\u041e\u0431\u0437\u043e\u0440","icon_lbl":"\u0421\u0432\u043e\u044f \u0438\u043a\u043e\u043d\u043a\u0430 (\u043d\u0435\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e)",
        "pick_img":"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435","cancel":"\u041e\u0442\u043c\u0435\u043d\u0430","add_btn":"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c",
        "err_name":"\u0412\u0432\u0435\u0434\u0438 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0438\u0433\u0440\u044b.","err_path":"\u0412\u044b\u0431\u0435\u0440\u0438 \u0438\u0441\u043f\u043e\u043b\u043d\u044f\u0435\u043c\u044b\u0439 \u0444\u0430\u0439\u043b.",
        "added":"\u2714  {} \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0430","launched":"\u25b6  {} \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u0430","removed":"\u0423\u0434\u0430\u043b\u0435\u043d\u0430: {}",
        "delete_title":"\u0423\u0434\u0430\u043b\u0438\u0442\u044c","delete_msg":"\u0423\u0431\u0440\u0430\u0442\u044c \u00ab{}\u00bb \u0438\u0437 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0438?",
        "clear_title":"\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435","clear_msg":"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0412\u0421\u0415 \u0438\u0433\u0440\u044b \u0438\u0437 \u0441\u043f\u0438\u0441\u043a\u0430?",
        "cache_cleared":"\u041a\u044d\u0448 \u043e\u0447\u0438\u0449\u0435\u043d - \u043e\u0431\u043b\u043e\u0436\u043a\u0438 \u0431\u0443\u0434\u0443\u0442 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b \u0437\u0430\u043d\u043e\u0432\u043e",
        "settings_title":"\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438","data_file":"\u0424\u0430\u0439\u043b \u0434\u0430\u043d\u043d\u044b\u0445","icon_cache":"\u041a\u044d\u0448 \u0438\u043a\u043e\u043d\u043e\u043a",
        "clear_cache_btn":"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u043a\u044d\u0448 \u0438\u043a\u043e\u043d\u043e\u043a","clear_all_btn":"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u0441\u0435 \u0438\u0433\u0440\u044b",
        "language_lbl":"\u042f\u0437\u044b\u043a","restart_note":"\u041f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435, \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f.",
        "not_found_title":"\u0424\u0430\u0439\u043b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d","not_found_msg":"\u0424\u0430\u0439\u043b \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0435 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442:\n{}",
        "not_exec_title":"\u041d\u0435 \u0438\u0441\u043f\u043e\u043b\u043d\u044f\u0435\u043c\u044b\u0439","not_exec_msg":"\u0423 \u0444\u0430\u0439\u043b\u0430 \u043d\u0435\u0442 \u043f\u0440\u0430\u0432 \u043d\u0430 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435.\n\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0438\u0445 \u0441\u0435\u0439\u0447\u0430\u0441?",
        "wine_missing_title":"Wine \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d","wine_missing_msg":"\u042d\u0442\u043e .exe \u0444\u0430\u0439\u043b, \u043d\u043e Wine \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d.\n\u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438: sudo pacman -S wine (\u0438\u043b\u0438 apt/dnf), \u0437\u0430\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u043b\u0430\u0443\u043d\u0447\u0435\u0440.",
        "games_count":"{} \u0438\u0433\u0440\u0430","games_count_pl":"{} \u0438\u0433\u0440","v":"v1.3 (linux)",
    },
}
LANG_NAMES = {"en": "English", "fr": "Fran\u00e7ais", "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"}
def load_config():
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"language": "en"}

def save_config(cfg):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

_cfg  = load_config()
_lang = _cfg.get("language", "en")
if _lang not in STRINGS: _lang = "en"

def t(key):
    return STRINGS[_lang].get(key, STRINGS["en"].get(key, key))

def load_games():
    if not os.path.exists(DATA_FILE): return []
    try:
        with open(DATA_FILE, encoding="utf-8") as f: return json.load(f)
    except: return []

def save_games(games):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

def _raindrop(size):
    path = os.path.join(ICON_CACHE, f"drop_{size}.png")
    if os.path.exists(path): return path
    img  = Image.new("RGBA", (size,size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    r    = size//5
    mask = Image.new("L", (size,size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,size-1,size-1], radius=r, fill=255)
    img.paste(Image.new("RGBA",(size,size),(0,0,0,255)), mask=mask)
    cx,cr,cy = size/2, size*0.27, size*0.63
    draw.ellipse([cx-cr,cy-cr,cx+cr,cy+cr], fill=(255,255,255,255))
    draw.polygon([(cx,size*0.14),(cx-cr*1.02,cy),(cx+cr*1.02,cy)], fill=(255,255,255,255))
    draw.ellipse([cx-cr*.5,cy-cr*.65,cx-cr*.1,cy-cr*.25], fill=(255,255,255,70))
    img.save(path); return path

_UA = "RainsLauncher/1.3-linux"

def _rawg_search(name):
    try:
        q   = urllib.parse.quote(name)
        url = f"https://api.rawg.io/api/games?search={q}&page_size=1&key=demo"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=7) as r:
            data = json.loads(r.read())
        res = data.get("results", [])
        if res: return res[0].get("background_image")
    except: pass
    return None

def _download_cover(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=10) as r: raw = r.read()
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        w,h = img.size; s = min(w,h)
        img = img.crop([(w-s)//2,(h-s)//2,(w-s)//2+s,(h-s)//2+s])
        img = img.resize((128,128), Image.LANCZOS)
        img = Image.alpha_composite(img, Image.new("RGBA",(128,128),(0,0,0,35)))
        img.save(dest,"PNG"); return True
    except: return False

def fetch_cover(name, key):
    dest = os.path.join(ICON_CACHE, f"cover_{key}.png")
    if os.path.exists(dest): return dest
    url = _rawg_search(name)
    if url and _download_cover(url, dest): return dest
    return None


def _placeholder(name):
    key  = hashlib.md5(name.encode()).hexdigest()
    path = os.path.join(ICON_CACHE, f"ph_{key}.png")
    if os.path.exists(path): return path
    size = 128
    img  = Image.new("RGBA",(size,size),(14,14,14,255))
    mask = Image.new("L",(size,size),0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0,size-1,size-1], radius=18, fill=255)
    img.putalpha(mask)
    bd = Image.new("RGBA",(size,size),(0,0,0,0))
    ImageDraw.Draw(bd).rounded_rectangle([0,0,size-1,size-1], radius=18,
                                         outline=(74,158,255,40), width=1)
    img = Image.alpha_composite(img, bd)
    initials = "".join(w[0].upper() for w in name.split()[:2]) or "?"
    draw = ImageDraw.Draw(img)
    fs   = 44 if len(initials)==1 else 32
    font = None
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(candidate):
            try:
                font = ImageFont.truetype(candidate, fs); break
            except: pass
    if font is None:
        font = ImageFont.load_default()
    bb = draw.textbbox((0,0), initials, font=font)
    tw,th = bb[2]-bb[0], bb[3]-bb[1]
    draw.text(((size-tw)//2,(size-th)//2-2), initials, fill=(200,200,200,200), font=font)
    img.save(path); return path

def _extract_exe_icon(exe_path):
    """Extraction d'icone native depuis un .exe (Windows uniquement, via
    pywin32). Sur les autres plateformes on retombe sur le placeholder
    genere par _placeholder()."""
    if sys.platform != "win32":
        return None
    key  = hashlib.md5(exe_path.encode()).hexdigest()
    dest = os.path.join(ICON_CACHE, f"exe_{key}.png")
    if os.path.exists(dest): return dest
    try:
        import win32ui, win32gui, win32con, win32api
        sx = win32api.GetSystemMetrics(win32con.SM_CXICON)
        sy = win32api.GetSystemMetrics(win32con.SM_CYICON)
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        if not large: return None
        if small: win32gui.DestroyIcon(small[0])
        hdc  = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, sx, sy)
        hdc2 = hdc.CreateCompatibleDC(); hdc2.SelectObject(hbmp)
        hdc2.DrawIcon((0,0), large[0])
        bi = hbmp.GetInfo(); bs = hbmp.GetBitmapBits(True)
        img = Image.frombuffer("RGBA",(bi["bmWidth"],bi["bmHeight"]),bs,"raw","BGRA",0,1)
        img.resize((128,128), Image.LANCZOS).save(dest)
        win32gui.DestroyIcon(large[0]); return dest
    except: return None

class GameCard(tk.Frame):
    _icon_queue = queue.Queue()

    def __init__(self, parent, game, on_launch, on_delete, app_root, **kw):
        super().__init__(parent, bg=CARD, **kw)
        self.game      = game
        self.on_launch = on_launch
        self.on_delete = on_delete
        self._root     = app_root
        self._photo    = None
        self._photo2   = None
        self._icon_lbl = None
        self._hover_t  = 0.0
        self._hover_anim = None
        self._launch_btn = None
        self._pulse_anim = None
        self._build()
        self._bind_events(self)
        self._load_icon_async()

    def _build(self):
        self._bar = tk.Frame(self, bg=ACCENT, width=2)
        self._bar.place(x=0, y=0, relheight=1)

        icf = tk.Frame(self, bg=CARD, width=90, height=90)
        icf.pack_propagate(False)
        icf.pack(pady=(15,5), padx=12)
        self._icon_lbl = tk.Label(icf, bg=CARD, cursor="hand2")
        self._icon_lbl.pack(expand=True)
        self._icon_lbl.bind("<Button-1>", lambda e: self._on_launch_click())
        self._set_photo(_placeholder(self.game["name"]))

        self._name_lbl = tk.Label(self, text=self.game["name"],
                 font=("DejaVu Sans",10,"bold"), fg=TEXT, bg=CARD,
                 wraplength=140, justify="center")
        self._name_lbl.pack(padx=8)

        short = os.path.basename(self.game.get("path","")) or "\u2014"
        self._path_lbl = tk.Label(self, text=short, font=("DejaVu Sans",7),
                 fg=TEXT3, bg=CARD, wraplength=140, justify="center")
        self._path_lbl.pack(padx=8, pady=(1,7))

        bf = tk.Frame(self, bg=CARD)
        bf.pack(pady=(0,11), padx=10, fill="x")
        self._launch_btn = tk.Button(bf, text=t("launch"),
                  command=self._on_launch_click,
                  bg=ACCENT, fg="#050505", font=("DejaVu Sans",8,"bold"),
                  relief="flat", bd=0, padx=6, pady=5,
                  activebackground=ACCENT2, activeforeground="white",
                  cursor="hand2")
        self._launch_btn.pack(side="left", expand=True, fill="x", padx=(0,3))
        tk.Button(bf, text="\u2715", command=lambda: self.on_delete(self.game),
                  bg=BG3, fg=TEXT2, font=("DejaVu Sans",8),
                  relief="flat", bd=0, padx=7, pady=5,
                  activebackground=ERR, activeforeground="white",
                  cursor="hand2", width=2).pack(side="right")

    def _on_launch_click(self):
        if self._pulse_anim:
            self._pulse_anim.stop()
        def tick(t):
            if t < 0.5:
                c = lerp_color(ACCENT, "#ffffff", t*2)
            else:
                c = lerp_color("#ffffff", ACCENT, (t-0.5)*2)
            try: self._launch_btn.config(bg=c)
            except: pass
        self._pulse_anim = Anim(self._root, 280, tick, ease=_ease_in_out)
        self.on_launch(self.game)

    def _bind_events(self, w):
        w.bind("<Enter>", self._on_enter)
        w.bind("<Leave>", self._on_leave)
        for c in w.winfo_children(): self._bind_events(c)

    def _on_enter(self, e=None):
        if self._hover_anim: self._hover_anim.stop()
        start = self._hover_t
        def tick(raw):
            self._hover_t = start + (1.0 - start) * raw
            self._apply_hover()
        self._hover_anim = Anim(self._root, 160, tick)

    def _on_leave(self, e=None):
        if self._hover_anim: self._hover_anim.stop()
        start = self._hover_t
        def tick(raw):
            self._hover_t = start * (1.0 - raw)
            self._apply_hover()
        self._hover_anim = Anim(self._root, 200, tick)

    def _apply_hover(self):
        t  = self._hover_t
        bg = lerp_color(CARD, CARD_H, t)
        bar_w = int(2 + 2*t)
        try:
            self.config(bg=bg)
            self._bar.place_configure(width=bar_w)
            for w in [self._name_lbl, self._path_lbl,
                      self._icon_lbl, self._icon_lbl.master]:
                w.config(bg=bg)
            self._launch_btn.master.config(bg=bg)
        except tk.TclError: pass

    def _set_photo(self, path, animate=False):
        try:
            img = Image.open(path).convert("RGBA").resize((84,84), Image.LANCZOS)
            new_photo = ImageTk.PhotoImage(img)
        except: return

        if not animate or self._photo is None:
            self._photo = new_photo
            try: self._icon_lbl.config(image=self._photo)
            except: pass
            return

        old_photo = self._photo
        new_pil   = img

        try:
            old_pil = Image.open(_placeholder(self.game["name"])).convert("RGBA").resize((84,84), Image.LANCZOS)
        except: old_pil = new_pil

        def make_frame(alpha):
            blended = Image.blend(old_pil, new_pil, alpha)
            return ImageTk.PhotoImage(blended)

        def tick(t):
            try:
                ph = make_frame(t)
                self._photo = ph
                self._icon_lbl.config(image=ph)
            except: pass

        Anim(self._root, 350, tick)
        self._photo = new_photo

    def _load_icon_async(self):
        game = self.game
        name = game["name"]
        key  = hashlib.md5(name.encode()).hexdigest()
        cover_path = os.path.join(ICON_CACHE, f"cover_{key}.png")

        custom = game.get("icon","")
        if custom and os.path.exists(custom) and "ph_" not in custom:
            self._set_photo(custom); return
        if os.path.exists(cover_path):
            self._set_photo(cover_path)
            game["icon"] = cover_path; return

        exe_icon = _extract_exe_icon(game.get("path",""))
        if exe_icon:
            self._set_photo(exe_icon)

        def worker():
            path = fetch_cover(name, key)
            if path: GameCard._icon_queue.put((self, path))
        threading.Thread(target=worker, daemon=True).start()

    def apply_cover(self, path):
        if not self.winfo_exists(): return
        self._set_photo(path, animate=True)
        self.game["icon"] = path

class Grid(tk.Frame):
    def __init__(self, parent, cols=4, root=None, **kw):
        super().__init__(parent, **kw)
        self.cols  = cols
        self.cards = []
        self._root = root
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win  = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._win, width=e.width))
        # Molette : Linux (Button-4/5) + fallback MouseWheel
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)),"units"))
        self.canvas.bind_all("<Button-4>",
            lambda e: self.canvas.yview_scroll(-2,"units"))
        self.canvas.bind_all("<Button-5>",
            lambda e: self.canvas.yview_scroll(2,"units"))

    def rebuild(self, games, on_launch, on_delete):
        for w in self.inner.winfo_children(): w.destroy()
        self.cards = []
        if not games:
            f = tk.Frame(self.inner, bg=BG)
            f.pack(expand=True, pady=90)
            tk.Label(f, text="\U0001F4A7", font=("DejaVu Sans",44), bg=BG, fg=TEXT3).pack()
            tk.Label(f, text=t("no_games"), font=("DejaVu Sans",14,"bold"),
                     bg=BG, fg=TEXT2).pack(pady=6)
            tk.Label(f, text=t("no_games_sub"), font=("DejaVu Sans",9),
                     bg=BG, fg=TEXT3).pack()
            return
        for i, g in enumerate(games):
            row, col = divmod(i, self.cols)
            c = GameCard(self.inner, g, on_launch, on_delete,
                         app_root=self._root, width=172, height=248)
            c.grid(row=row, column=col, padx=9, pady=9, sticky="nsew")
            self.cards.append(c)
            self._stagger_in(c, i)
        for col in range(self.cols):
            self.inner.columnconfigure(col, weight=1)

    def _stagger_in(self, card, index):
        delay = index * 40
        duration = 300
        card.config(bg=BG)
        for ch in card.winfo_children():
            try: ch.config(bg=BG)
            except: pass

        SLIDE = 18

        def tick(t):
            bg  = lerp_color(BG, CARD, t)
            try:
                card.config(bg=bg)
                offset = int(SLIDE * (1 - t))
                card.grid_configure(pady=(9 + offset, 9 - offset))
                for ch in card.winfo_children():
                    try:
                        if ch.winfo_class() not in ("Button",):
                            ch.config(bg=bg)
                    except: pass
            except tk.TclError: pass

        def done():
            try:
                card.config(bg=CARD)
                card.grid_configure(pady=(9,9))
                card._apply_hover()
            except: pass

        Anim(self._root, duration, tick, on_done=done,
             ease=_ease_out, delay=delay)

class AddDialog(tk.Toplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.on_save    = on_save
        self._icon_path = None
        self._ico_photo = None
        self.title(t("add_title"))
        self.geometry("450x340")
        self.resizable(False, False)
        self.configure(bg=BG2)
        self.transient(parent)
        self.grab_set()

        self.attributes("-alpha", 0.0)
        self._build()
        self.update_idletasks()
        self._fade_in()
        self.wait_window()

    def _fade_in(self):
        Anim(self, 200,
             lambda t: self.attributes("-alpha", t),
             ease=_ease_out)

    def _entry(self, parent, var, **kw):
        e = tk.Entry(parent, textvariable=var, bg=BG3, fg=TEXT,
                     insertbackground=TEXT, relief="flat", bd=0, **kw)
        e.config(highlightthickness=1, highlightcolor=ACCENT, highlightbackground=SEP)
        return e

    def _build(self):
        tk.Label(self, text=t("add_title"), font=("DejaVu Sans",13,"bold"),
                 fg=TEXT, bg=BG2).pack(anchor="w", padx=22, pady=(18,12))
        tk.Frame(self, bg=SEP, height=1).pack(fill="x", padx=22)

        b = tk.Frame(self, bg=BG2)
        b.pack(fill="both", expand=True, padx=22, pady=14)

        tk.Label(b, text=t("name_lbl"), font=("DejaVu Sans",8,"bold"),
                 fg=TEXT2, bg=BG2).grid(row=0,column=0,sticky="w",pady=(0,3))
        self.name_var = tk.StringVar()
        ne = self._entry(b, self.name_var, font=("DejaVu Sans",10))
        ne.grid(row=1, column=0, columnspan=2, sticky="ew", ipady=7)

        tk.Label(b, text=t("exe_lbl"), font=("DejaVu Sans",8,"bold"),
                 fg=TEXT2, bg=BG2).grid(row=2,column=0,sticky="w",pady=(12,3))
        pf = tk.Frame(b, bg=BG2)
        pf.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.path_var = tk.StringVar()
        self._entry(pf, self.path_var, font=("DejaVu Sans",9)).pack(
            side="left", fill="x", expand=True, ipady=7)
        tk.Button(pf, text=t("browse"), command=self._browse,
                  bg=ACCENT, fg="#050505", font=("DejaVu Sans",8,"bold"),
                  relief="flat", bd=0, padx=10, pady=7,
                  activebackground=ACCENT2, cursor="hand2").pack(side="right", padx=(5,0))

        tk.Label(b, text=t("icon_lbl"), font=("DejaVu Sans",8,"bold"),
                 fg=TEXT2, bg=BG2).grid(row=4,column=0,sticky="w",pady=(12,3))
        icf = tk.Frame(b, bg=BG2)
        icf.grid(row=5, column=0, columnspan=2, sticky="w")
        self._prev = tk.Label(icf, bg=BG3, width=4, height=2, text="?",
                              fg=TEXT3, font=("DejaVu Sans",11), relief="flat")
        self._prev.pack(side="left")
        tk.Button(icf, text=t("pick_img"), command=self._browse_icon,
                  bg=BG3, fg=TEXT2, font=("DejaVu Sans",8), relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2").pack(side="left", padx=7)

        b.columnconfigure(0, weight=1)
        tk.Frame(self, bg=SEP, height=1).pack(fill="x", padx=22)
        br = tk.Frame(self, bg=BG2)
        br.pack(fill="x", padx=22, pady=14)
        tk.Button(br, text=t("cancel"), command=self._close,
                  bg=BG3, fg=TEXT2, font=("DejaVu Sans",9), relief="flat", bd=0,
                  padx=14, pady=7, cursor="hand2").pack(side="right", padx=(7,0))
        tk.Button(br, text=t("add_btn"), command=self._save,
                  bg=ACCENT, fg="#050505", font=("DejaVu Sans",9,"bold"),
                  relief="flat", bd=0, padx=14, pady=7,
                  activebackground=ACCENT2, cursor="hand2").pack(side="right")
        ne.focus_set()

    def _close(self):
        Anim(self, 150,
             lambda t: self.attributes("-alpha", 1.0 - t),
             on_done=self.destroy)

    def _browse(self):
        p = filedialog.askopenfilename(
            title=t("exe_lbl"),
            initialdir=os.path.expanduser("~"),
            filetypes=[("Executables",".exe"), ("All files","*")] if sys.platform == "win32" else [("All files","*")])
        if not p: return
        self.path_var.set(p)
        if not self.name_var.get():
            self.name_var.set(os.path.splitext(os.path.basename(p))[0])
        ip = _extract_exe_icon(p)
        if ip: self._icon_path = ip; self._set_prev(ip)

    def _browse_icon(self):
        p = filedialog.askopenfilename(
            title=t("pick_img"),
            filetypes=[("Images","*.png *.jpg *.jpeg *.ico *.bmp *.svg"),("All","*.*")])
        if p: self._icon_path = p; self._set_prev(p)

    def _set_prev(self, path):
        try:
            img = Image.open(path).convert("RGBA").resize((36,36), Image.LANCZOS)
            self._ico_photo = ImageTk.PhotoImage(img)
            self._prev.config(image=self._ico_photo, text="", width=36, height=36)
        except: pass

    def _save(self):
        name = self.name_var.get().strip()
        path = self.path_var.get().strip()
        if not name: messagebox.showerror("", t("err_name")); return
        if not path: messagebox.showerror("", t("err_path")); return
        self.on_save({"name":name,"path":path,"icon":self._icon_path or ""})
        self._close()


class RainsLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title(t("app_title"))
        self.geometry("1060x700")
        self.minsize(800,520)
        self.configure(bg=BG)

        self.attributes("-alpha", 0.0)

        try:
            p = _raindrop(32)
            self._app_ico = ImageTk.PhotoImage(Image.open(p).resize((32,32)))
            self.iconphoto(True, self._app_ico)
        except: pass

        self.games       = load_games()
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        self._grid       = None
        self._page_anim  = None

        self._build_ui()
        self._rebuild()

        self.update_idletasks()
        self.deiconify()
        Anim(self, 320, lambda t: self.attributes("-alpha", t), ease=_ease_out)

        self._poll_icons()

    def _poll_icons(self):
        try:
            while True:
                card, path = GameCard._icon_queue.get_nowait()
                if card.winfo_exists():
                    card.apply_cover(path)
                    save_games(self.games)
        except queue.Empty: pass
        self.after(200, self._poll_icons)

    def _build_ui(self):
        self.sb = tk.Frame(self, bg=BG2, width=200)
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        lf = tk.Frame(self.sb, bg=BG2)
        lf.pack(fill="x", pady=(26,4), padx=16)
        try:
            p = _raindrop(38)
            self._logo_img = ImageTk.PhotoImage(Image.open(p).resize((38,38)))
            tk.Label(lf, image=self._logo_img, bg=BG2).pack(side="left")
        except:
            tk.Label(lf, text="\U0001F4A7", font=("DejaVu Sans",22), bg=BG2, fg=TEXT).pack(side="left")
        tc = tk.Frame(lf, bg=BG2)
        tc.pack(side="left", padx=10)
        tk.Label(tc, text="rain's", font=("DejaVu Sans",12,"bold"),
                 fg=ACCENT, bg=BG2).pack(anchor="w")
        tk.Label(tc, text="launcher", font=("DejaVu Sans",9),
                 fg=TEXT2, bg=BG2).pack(anchor="w")

        tk.Frame(self.sb, bg=SEP, height=1).pack(fill="x", padx=14, pady=12)

        for ico, key, cmd in [
            ("\U0001F3E0","library",  self._show_lib),
            ("\U0001F50D","search",   self._focus_search),
            ("\u2699", "settings", self._show_settings),
        ]:
            self._nav(ico, t(key), cmd)

        tk.Frame(self.sb, bg=SEP, height=1).pack(fill="x", padx=14, pady=12)

        tk.Button(self.sb, text=t("add_game"), command=self._add,
                  bg=ACCENT, fg="#050505", font=("DejaVu Sans",9,"bold"),
                  relief="flat", bd=0, pady=10,
                  activebackground=ACCENT2, activeforeground="white",
                  cursor="hand2").pack(fill="x", padx=14)

        self._count_lbl = tk.Label(self.sb, text="",
                                    font=("DejaVu Sans",7), fg=TEXT3, bg=BG2)
        self._count_lbl.pack(pady=5)
        tk.Label(self.sb, text=t("v"), font=("DejaVu Sans",6), fg=TEXT3, bg=BG2
                 ).pack(side="bottom", pady=8)

        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        hdr = tk.Frame(main, bg=BG, height=56)
        hdr.pack(fill="x", padx=20, pady=(16,0))
        hdr.pack_propagate(False)

        self._title_lbl = tk.Label(hdr, text=t("library"),
                                    font=("DejaVu Sans",16,"bold"), fg=TEXT, bg=BG)
        self._title_lbl.pack(side="left", anchor="center")
        sf = tk.Frame(hdr, bg=BG3, highlightthickness=1,
                      highlightcolor="#1e3a5f", highlightbackground=SEP)
        sf.pack(side="right", anchor="center")
        tk.Label(sf, text="\U0001F50D", bg=BG3, fg=TEXT3,
                 font=("DejaVu Sans",8)).pack(side="left", padx=(7,2))
        self._se = tk.Entry(sf, textvariable=self._search_var,
                             bg=BG3, fg=TEXT, insertbackground=TEXT,
                             font=("DejaVu Sans",9), relief="flat", bd=0, width=18)
        self._se.pack(side="left", ipady=7, padx=(0,9))
        self._se.insert(0, t("search_ph")); self._se.config(fg=TEXT2)
        self._se.bind("<FocusIn>",  lambda e: self._sfocus(True))
        self._se.bind("<FocusOut>", lambda e: self._sfocus(False))

        tk.Frame(main, bg=SEP, height=1).pack(fill="x", padx=20, pady=8)

        self._page_container = tk.Frame(main, bg=BG)
        self._page_container.pack(fill="both", expand=True, padx=5)
        self._stack = self._page_container

        stf = tk.Frame(main, bg=BG2, height=24)
        stf.pack(fill="x", side="bottom")
        self._stlbl = tk.Label(stf, text="", font=("DejaVu Sans",7), fg=TEXT3, bg=BG2)
        self._stlbl.pack(side="left", padx=10, pady=3)

    def _sfocus(self, on):
        ph = t("search_ph")
        if on:
            if self._se.get() == ph: self._se.delete(0,tk.END); self._se.config(fg=TEXT)
        else:
            if not self._se.get(): self._se.insert(0,ph); self._se.config(fg=TEXT2)

    def _nav(self, ico, lbl, cmd):
        fr  = tk.Frame(self.sb, bg=BG2, cursor="hand2")
        fr.pack(fill="x", padx=5, pady=1)
        inn = tk.Frame(fr, bg=BG2)
        inn.pack(fill="x", padx=8, pady=6)
        tk.Label(inn, text=ico, font=("DejaVu Sans",10), fg=TEXT2, bg=BG2).pack(side="left")
        tk.Label(inn, text=lbl, font=("DejaVu Sans",9),  fg=TEXT2, bg=BG2).pack(side="left", padx=7)
        def _e(e):
            fr.config(bg=BG3); inn.config(bg=BG3)
            [c.config(bg=BG3) for c in inn.winfo_children()]
        def _l(e):
            fr.config(bg=BG2); inn.config(bg=BG2)
            [c.config(bg=BG2) for c in inn.winfo_children()]
        for w in [fr,inn]+list(inn.winfo_children()):
            w.bind("<Enter>",_e); w.bind("<Leave>",_l)
            w.bind("<Button-1>", lambda e, c=cmd: c())

    def _switch_page(self, build_fn):
        old_children = list(self._stack.winfo_children())

        if not old_children:
            build_fn()
            self._page_fade_in()
            return

        def do_fade_out(t):
            for ch in old_children:
                try:
                    offset = int(12 * t)
                    ch.pack_configure(pady=(0, offset))
                except: pass

        def after_out():
            for ch in old_children:
                try: ch.destroy()
                except: pass
            build_fn()
            self._page_fade_in()

        Anim(self, 120, do_fade_out, on_done=after_out, ease=_ease_in_out)

    def _page_fade_in(self):
        new_children = list(self._stack.winfo_children())
        def tick(t):
            offset = int(14 * (1 - t))
            for ch in new_children:
                try: ch.pack_configure(pady=(offset, 0))
                except: pass
        Anim(self, 180, tick, ease=_ease_out)

    def _show_lib(self):
        self._title_lbl.config(text=t("library"))
        self._search_var.set("")
        self._switch_page(self._build_library_page)

    def _build_library_page(self):
        self._grid = Grid(self._stack, cols=4, root=self, bg=BG)
        self._grid.pack(fill="both", expand=True)
        self._grid.rebuild(self.games, self._launch, self._delete)
        n = len(self.games)
        key = "games_count" if n<=1 else "games_count_pl"
        self._count_lbl.config(text=t(key).format(n))

    def _focus_search(self):
        self._se.focus_set()

    def _show_settings(self):
        self._title_lbl.config(text=t("settings_title"))
        self._switch_page(self._build_settings_page)
        self._grid = None

    def _build_settings_page(self):
        s = tk.Frame(self._stack, bg=BG)
        s.pack(fill="both", expand=True, padx=24, pady=18)
        tk.Label(s, text=t("settings_title"), font=("DejaVu Sans",13,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", pady=(0,16))
        lang_frame = tk.Frame(s, bg=CARD, padx=16, pady=14)
        lang_frame.pack(fill="x", pady=(0,10))
        tk.Label(lang_frame, text=t("language_lbl"), font=("DejaVu Sans",9,"bold"),
                 fg=TEXT, bg=CARD).pack(anchor="w")
        btn_row = tk.Frame(lang_frame, bg=CARD)
        btn_row.pack(anchor="w", pady=(8,0))
        self._lang_var = tk.StringVar(value=_lang)
        for code, label in LANG_NAMES.items():
            tk.Radiobutton(btn_row, text=label, variable=self._lang_var, value=code,
                bg=CARD, fg=TEXT2, selectcolor=BG3,
                activebackground=CARD, activeforeground=TEXT,
                font=("DejaVu Sans",9), relief="flat",
                command=self._apply_lang).pack(side="left", padx=(0,16))
        self._lang_note = tk.Label(lang_frame, text="",
                                    font=("DejaVu Sans",7), fg=TEXT3, bg=CARD)
        self._lang_note.pack(anchor="w", pady=(6,0))

        info = tk.Frame(s, bg=CARD, padx=16, pady=12)
        info.pack(fill="x")
        for lbl_key, val in [(t("data_file"), DATA_FILE),(t("icon_cache"), ICON_CACHE)]:
            tk.Label(info, text=lbl_key, font=("DejaVu Sans",8,"bold"),
                     fg=TEXT, bg=CARD).pack(anchor="w")
            tk.Label(info, text=val, font=("DejaVu Sans",7),
                     fg=TEXT2, bg=CARD).pack(anchor="w", pady=(1,8))
        tk.Frame(s, bg=SEP, height=1).pack(fill="x", pady=10)
        tk.Button(s, text=t("clear_cache_btn"), command=self._clear_cache,
                  bg=BG3, fg=TEXT2, font=("DejaVu Sans",8), relief="flat", bd=0,
                  padx=12, pady=8, cursor="hand2").pack(anchor="w")
        tk.Button(s, text=t("clear_all_btn"), command=self._clear_all,
                  bg=ERR, fg="white", font=("DejaVu Sans",8,"bold"), relief="flat", bd=0,
                  padx=12, pady=8, cursor="hand2").pack(anchor="w", pady=(6,0))

    def _apply_lang(self):
        global _lang, _cfg
        chosen = self._lang_var.get()
        _cfg["language"] = chosen
        save_config(_cfg)
        self._lang_note.config(text=t("restart_note"), fg=TEXT2)

    def _add(self):
        def on_save(game):
            self.games.append(game)
            save_games(self.games)
            self._rebuild()
            self._status(t("added").format(game["name"]))
        AddDialog(self, on_save)

    def _launch(self, game):
        p = game.get("path","")
        if not p or not os.path.exists(p):
            messagebox.showerror(t("not_found_title"), t("not_found_msg").format(p)); return

        is_exe = p.lower().endswith(".exe")

        if is_exe and sys.platform != "win32":
            # .exe on Linux/macOS -> launch through Wine
            import shutil as _shutil
            if not _shutil.which("wine"):
                messagebox.showerror(
                    t("wine_missing_title"),
                    t("wine_missing_msg"))
                return
            try:
                subprocess.Popen(["wine", p], cwd=os.path.dirname(p) or None)
                self._status(t("launched").format(game["name"]))
            except Exception as ex:
                messagebox.showerror("", str(ex))
            return

        if is_exe:
            # .exe on Windows -> launch natively
            try:
                subprocess.Popen([p], cwd=os.path.dirname(p) or None)
                self._status(t("launched").format(game["name"]))
            except Exception as ex:
                messagebox.showerror("", str(ex))
            return

        if sys.platform != "win32" and not os.access(p, os.X_OK):
            if messagebox.askyesno(t("not_exec_title"), t("not_exec_msg")):
                try:
                    st = os.stat(p)
                    os.chmod(p, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except Exception as ex:
                    messagebox.showerror("", str(ex)); return
            else:
                return
        try:
            subprocess.Popen([p], cwd=os.path.dirname(p) or None)
            self._status(t("launched").format(game["name"]))
        except Exception as ex:
            messagebox.showerror("", str(ex))

    def _delete(self, game):
        if messagebox.askyesno(t("delete_title"), t("delete_msg").format(game["name"])):
            self.games = [g for g in self.games if g.get("path") != game.get("path")]
            save_games(self.games)
            self._rebuild()
            self._status(t("removed").format(game["name"]))

    def _clear_all(self):
        if messagebox.askyesno(t("clear_title"), t("clear_msg")):
            self.games = []; save_games(self.games); self._show_lib()

    def _clear_cache(self):
        import shutil
        try:
            shutil.rmtree(ICON_CACHE); os.makedirs(ICON_CACHE)
            self._status(t("cache_cleared"))
        except Exception as ex:
            messagebox.showerror("", str(ex))

    def _filter(self):
        q  = self._search_var.get().lower().strip()
        ph = t("search_ph").lower()
        filtered = self.games if (not q or q==ph) else \
                   [g for g in self.games if q in g["name"].lower()]
        if self._grid:
            self._grid.rebuild(filtered, self._launch, self._delete)

    def _rebuild(self):
        for w in self._stack.winfo_children(): w.destroy()
        self._grid = Grid(self._stack, cols=4, root=self, bg=BG)
        self._grid.pack(fill="both", expand=True)
        self._grid.rebuild(self.games, self._launch, self._delete)
        n = len(self.games)
        key = "games_count" if n<=1 else "games_count_pl"
        self._count_lbl.config(text=t(key).format(n))

    def _status(self, msg):
        self._stlbl.config(text=msg, fg=OK)
        if hasattr(self, "_status_anim") and self._status_anim:
            self._status_anim.stop()
        def fade_out(t):
            c = lerp_color(OK, TEXT3, t)
            try: self._stlbl.config(fg=c)
            except: pass
        def clear():
            try: self._stlbl.config(text="", fg=TEXT3)
            except: pass
        self.after(2500, lambda: setattr(self, "_status_anim",
            Anim(self, 600, fade_out, on_done=clear, ease=_ease_in_out)))

if __name__ == "__main__":
    RainsLauncher().mainloop()
