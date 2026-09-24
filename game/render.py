"""HTML for the cards. Photos are embedded as base64 so the app never needs the network."""

import base64
import html
import zlib
from functools import lru_cache
from pathlib import Path

from game.stats import STATS

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "assets" / "cars"

# Card header colours, picked per car so every card looks a little different.
PALETTE = ["#e63946", "#1d7fd6", "#f18f01", "#2a9d8f", "#8e44ad", "#d62f7f", "#2b9348", "#e76f51"]


def colour(car: dict) -> str:
    return PALETTE[zlib.crc32(car["id"].encode()) % len(PALETTE)]


@lru_cache(maxsize=128)
def photo_src(car_id: str) -> str | None:
    path = PHOTOS / f"{car_id}.jpg"
    if not path.exists():
        return None
    data = path.read_bytes()
    mime = "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"  # a few Commons photos are PNGs
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def silhouette(tint: str) -> str:
    """Fallback art: a simple sports-car silhouette."""
    return f"""<svg viewBox="0 0 400 225" xmlns="http://www.w3.org/2000/svg" class="vf-photo">
  <rect width="400" height="225" fill="{tint}" opacity=".15"/>
  <path d="M40 150 Q45 120 90 112 L150 82 Q200 64 260 80 L320 108 Q362 116 364 150 Z" fill="{tint}"/>
  <path d="M160 88 L200 76 Q235 72 262 86 L285 106 L150 108 Z" fill="#fff" opacity=".7"/>
  <circle cx="110" cy="152" r="26" fill="#222"/><circle cx="110" cy="152" r="11" fill="#bbb"/>
  <circle cx="300" cy="152" r="26" fill="#222"/><circle cx="300" cy="152" r="11" fill="#bbb"/>
</svg>"""


def card_head_html(car: dict, badge: str = "") -> str:
    """The name bar and photo at the top of a card."""
    src = photo_src(car["id"])
    photo = (f'<img class="vf-photo" src="{src}" alt="{html.escape(car["naam"])}">' if src
             else silhouette(colour(car)))
    return f"""<div class="vf-head"><span class="vf-name">{html.escape(car['naam'])}</span><span class="vf-flag">{car['land']}</span></div>
  <div class="vf-pic">{photo}{f'<div class="vf-badge">{badge}</div>' if badge else ''}</div>"""


def card_foot_html(car: dict, credit: dict | None = None) -> str:
    """The fun fact and photo credit at the bottom of a card."""
    credit_line = ""
    if credit:
        credit_line = (f'<div class="vf-credit">Foto: {html.escape(credit["artist"][:60])} · '
                       f'{html.escape(credit["licence"])} · Wikimedia Commons</div>')
    return f'<div class="vf-fact">💡 {html.escape(car["feit"])}</div>{credit_line}'


def card_html(car: dict, credit: dict | None = None, *, highlight: str | None = None,
              result: str = "", big: bool = False) -> str:
    """One Top Trumps card. `result` is '', 'wen', 'verloor' or 'gelyk'."""
    rows = []
    for s in STATS:
        cls = "vf-row vf-hl" if s.key == highlight else "vf-row"
        rows.append(f'<div class="{cls}"><span>{s.icon} {s.label}</span><b>{html.escape(s.display(car))}</b></div>')
    badge = {"wen": "🏆 WEN!", "gelyk": "🤝 GELYK"}.get(result, "")
    return f"""
<div class="vf-card {'vf-big' if big else ''} vf-{result or 'plain'}" style="--tint:{colour(car)}">
  {card_head_html(car, badge)}
  <div class="vf-stats">{''.join(rows)}</div>
  {card_foot_html(car, credit)}
</div>"""


def chooser_css(car: dict, key: str) -> str:
    """Styles a Streamlit container (st.container(key=key)) holding one button per stat so it
    looks like a card whose stat rows are the buttons. Each value is drawn on the right with ::after."""
    values = "\n".join(
        f'.st-key-{key} .st-key-stat_{s.key} button::after {{ content:"{s.display(car)}"; }}' for s in STATS)
    return f"<style>.st-key-{key} {{ --tint:{colour(car)}; }}\n{values}</style>"


def card_back_html(label: str = "") -> str:
    return f"""<div class="vf-card vf-back"><div class="vf-back-inner">🏎️<br>Vinnige<br>Fluite
<div class="vf-back-label">{html.escape(label)}</div></div></div>"""


CSS = """
<style>
/* Only our own HTML gets the rounded font; overriding Streamlit's classes breaks its icon font. */
.vf-card, .vf-banner, .vf-title, .vf-sub, .vf-curtain { font-family: ui-rounded, "SF Pro Rounded", "Nunito", "Segoe UI", system-ui, sans-serif; }
.vf-card { background:#fff; color:#1b1b1b; border-radius:18px; border:6px solid var(--tint);
  box-shadow:0 6px 18px rgba(0,0,0,.18); overflow:hidden; max-width:360px; margin:0 auto 12px; }
.vf-big { max-width:430px; }
.vf-head { background:var(--tint); color:#fff; padding:8px 12px; display:flex; justify-content:space-between;
  align-items:center; gap:8px; font-weight:800; font-size:1.05rem; line-height:1.2; }
.vf-flag { font-size:1.4rem; }
.vf-pic { position:relative; background:#eee; }
.vf-photo { display:block; width:100%; aspect-ratio:16/10; object-fit:cover; }
.vf-badge { position:absolute; top:8px; right:8px; background:#ffd60a; color:#000; font-weight:900;
  padding:4px 10px; border-radius:999px; box-shadow:0 2px 6px rgba(0,0,0,.3); }
.vf-stats { padding:6px 10px; }
.vf-row { display:flex; justify-content:space-between; padding:5px 8px; border-radius:8px; font-size:.95rem; }
.vf-row:nth-child(odd) { background:#f4f4f6; }
.vf-row b { font-variant-numeric: tabular-nums; }
.vf-hl { background:#ffd60a !important; font-weight:800; transform:scale(1.03); }
.vf-fact { font-size:.8rem; padding:4px 14px 8px; color:#444; }
.vf-credit { font-size:.62rem; color:#888; padding:0 14px 8px; }
.vf-wen { border-color:#2b9348; box-shadow:0 0 0 4px #ffd60a, 0 8px 22px rgba(0,0,0,.25); }
.vf-verloor { opacity:.72; filter:grayscale(.35); }
/* the choosing card: a keyed Streamlit container dressed up as a card */
div[class*="st-key-kieskaart"] { background:#fff; color:#1b1b1b; border-radius:18px; border:6px solid var(--tint);
  box-shadow:0 6px 18px rgba(0,0,0,.18); overflow:hidden; max-width:430px; margin:0 auto 12px; gap:0 !important; padding-bottom:4px; }
div[class*="st-key-kieskaart"] .stMarkdown p { margin:0; }
div[class*="st-key-kieskaart"] .stButton { padding:0 10px; }
div[class*="st-key-kieskaart"] .stButton button { width:100%; min-height:2.5rem; margin:1px 0; padding:4px 10px;
  border:2px solid transparent; border-radius:10px; background:#f4f4f6; color:#1b1b1b; justify-content:flex-start;
  font-size:.98rem; font-weight:600; transition:transform .08s; }
div[class*="st-key-kieskaart"] .stButton button::after { margin-left:auto; padding-left:10px; font-weight:800;
  font-variant-numeric:tabular-nums; white-space:nowrap; }
div[class*="st-key-kieskaart"] .stButton button:hover { background:#ffd60a; border-color:var(--tint); transform:scale(1.02); }
div[class*="st-key-kieskaart"] .stButton button > div { flex:0 1 auto; }
div[class*="st-key-kieskaart"] .vf-fact { padding-top:8px; }
.vf-back { background:repeating-linear-gradient(45deg,#1d3557,#1d3557 14px,#274c77 14px,#274c77 28px);
  border-color:#1d3557; min-height:300px; display:flex; align-items:center; justify-content:center; }
.vf-back-inner { color:#fff; text-align:center; font-size:1.6rem; font-weight:900; line-height:1.25; padding:40px 10px; }
.vf-back-label { font-size:1rem; font-weight:600; margin-top:10px; }
.vf-banner { text-align:center; font-size:1.8rem; font-weight:900; margin:4px 0 14px; }
.vf-title { text-align:center; font-size:3rem; font-weight:900; margin:0; }
.vf-sub { text-align:center; font-size:1.1rem; color:#666; margin-bottom:18px; }
.vf-geheim { max-width:560px; margin:0 auto 18px; text-align:center; font-size:1.2rem; font-weight:700;
  background:#fff3bf; border:3px dashed #f18f01; border-radius:16px; padding:14px 18px;
  font-family: ui-rounded, "SF Pro Rounded", "Nunito", "Segoe UI", system-ui, sans-serif; }
.vf-curtain { text-align:center; font-size:2.2rem; font-weight:900; padding:40px 10px 20px; }
div.stButton > button { font-size:1.05rem; font-weight:700; min-height:3rem; border-radius:12px; }
</style>
"""
