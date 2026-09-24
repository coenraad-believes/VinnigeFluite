"""Vinnige Fluite — 'n Afrikaanse Top Trumps-kaartspel met karre vir 2 tot 4 spelers."""

import html

import streamlit as st

from game import storage
from game.engine import GameState, new_game, play_round
from game.render import CSS, card_back_html, card_foot_html, card_head_html, card_html, chooser_css
from game.stats import BY_KEY, STATS

st.set_page_config(page_title="Vinnige Fluite", page_icon="🏎️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

CARS = storage.load_cars()
CREDITS = storage.load_credits()
EMOJIS = ["🔴", "🔵", "🟢", "🟡"]
LENGTHS = {"Kort (20 rondtes)": 20, "Medium (40 rondtes)": 40, "Volledig (tot een wen alles)": None}

ss = st.session_state
ss.setdefault("screen", "begin")
ss.setdefault("game", None)


def go(screen: str) -> None:
    ss.screen = screen
    if ss.game is not None and screen not in ("begin", "oor"):
        storage.save_game(ss.game, screen)


def card(cid: str, **kw) -> str:
    return card_html(CARS[cid], CREDITS.get(cid), **kw)


def who(i: int) -> str:
    p = ss.game.players[i]
    return f"{p.emoji} {html.escape(p.naam)}"


# ---------- actions ----------

def start_game(n: int, names: list[str], length: str) -> None:
    players = [(names[i].strip() or f"Speler {i + 1}", EMOJIS[i]) for i in range(n)]
    ss.game = new_game(players, list(CARS), max_rounds=LENGTHS[length])
    ss.celebrated = False
    go("gee_oor")


def resume(saved: tuple[GameState, str]) -> None:
    ss.game, screen = saved
    ss.celebrated = False
    go(screen)


def choose(stat_key: str) -> None:
    play_round(ss.game, stat_key, CARS)
    go("onthul")


def next_round() -> None:
    g: GameState = ss.game
    if g.over:
        go("einde")
    elif g.current != g.last.chooser:
        go("gee_oor")  # new player's turn: let the others look away first
    else:
        go("kies")


def quit_game() -> None:
    storage.clear_game()
    ss.game = None
    ss.screen = "begin"


def back_from_about() -> None:
    ss.screen = ss.get("before_about", "begin")


def open_about() -> None:
    if ss.screen != "oor":
        ss.before_about = ss.screen
    ss.screen = "oor"


# ---------- sidebar ----------

def sidebar() -> None:
    g: GameState | None = ss.game
    with st.sidebar:
        st.markdown("## 🏎️ Vinnige Fluite")
        if g is not None and ss.screen != "begin":
            st.markdown("### Telbord")
            for i, p in enumerate(g.players):
                turn = " ⬅️ beurt" if i == g.current and not g.over else ""
                out = " — uit 😢" if not p.active else ""
                st.markdown(f"**{p.emoji} {html.escape(p.naam)}**: {len(p.pile)} kaarte{turn}{out}")
            st.markdown(f"🪙 **Pot:** {len(g.pot)} kaarte")
            limit = f" van {g.max_rounds}" if g.max_rounds else ""
            st.markdown(f"🔁 **Rondte:** {g.rounds}{limit}")
            st.divider()
            with st.popover("🏠 Begin oor", width="stretch"):
                st.write("Wil jy regtig hierdie spel stop?")
                st.button("Ja, stop die spel", on_click=quit_game, type="primary")
        st.button("ℹ️ Oor die kaarte", on_click=open_about, width="stretch")


# ---------- screens ----------

def screen_begin() -> None:
    st.markdown('<p class="vf-title">🏎️ Vinnige Fluite 💨</p>', unsafe_allow_html=True)
    st.markdown('<p class="vf-sub">Die kaartspel met 80 regte karre. Wie het die vinnigste fluit?</p>',
                unsafe_allow_html=True)

    saved = storage.load_game()
    if saved and not saved[0].over:
        g = saved[0]
        names = ", ".join(f"{p.emoji} {p.naam}" for p in g.players)
        st.info(f"Daar is 'n spel wat nog nie klaar is nie: {names} (rondte {g.rounds}).")
        st.button("▶️ Hervat spel", on_click=resume, args=(saved,), type="primary")
        st.divider()

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        n = st.segmented_control("Hoeveel spelers?", [2, 3, 4], default=2, required=True, width="stretch")
        names = []
        cols = st.columns(2)
        for i in range(n):
            with cols[i % 2]:
                names.append(st.text_input(f"{EMOJIS[i]} Speler {i + 1}", value=f"Speler {i + 1}",
                                           key=f"name{i}", max_chars=16))
        length = st.radio("Hoe lank wil julle speel?", list(LENGTHS), horizontal=True)
        st.button("🏁 Speel!", on_click=start_game, args=(n, names, length), type="primary", width="stretch")

        with st.expander("📖 Hoe speel mens?"):
            st.markdown(
                "- Die 80 kaarte word geskommel en uitgedeel.\n"
                "- Wie se beurt dit is, kyk na sy of haar **boonste kaart** en kies iets om te vergelyk.\n"
                "- Almal se boonste kaarte word omgedraai. Die beste waarde wen al die kaarte!\n"
                "  - **Topspoed**, **Krag**, **Wringkrag**, **Produksiejare** en **Enjingrootte**: hoër wen ⬆️\n"
                "  - **0–100 km/h**, **Kwartmyl** en **Massa**: laer wen ⬇️\n"
                "- As jy wen, is dit weer jou beurt. As iemand jou klop, is dit hulle beurt.\n"
                "- Gelykop? Die kaarte gaan in die **pot**, en die wenner van die volgende rondte kry alles.\n"
                "- Wie al die kaarte het (of die meeste as die rondtes op is), wen!"
            )


def screen_gee_oor() -> None:
    g: GameState = ss.game
    p = g.players[g.current]
    st.markdown(f'<div class="vf-curtain">Dis {who(g.current)} se beurt!</div>', unsafe_allow_html=True)
    st.markdown('<p class="vf-sub">Ander spelers, kyk weg! 🙈</p>', unsafe_allow_html=True)
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.markdown(card_back_html(f"{len(p.pile)} kaarte"), unsafe_allow_html=True)
        st.button(f"👀 Ek is {p.naam}, wys my kaart", on_click=go, args=("kies",), type="primary", width="stretch")


def screen_kies() -> None:
    g: GameState = ss.game
    p = g.players[g.current]
    top = CARS[p.pile[0]]
    st.markdown(f'<div class="vf-banner">{who(g.current)}, tik op jou sterkste punt!</div>', unsafe_allow_html=True)
    others = [i for i in g.active_players() if i != g.current]
    st.markdown('<p class="vf-sub">Teen: ' + ", ".join(
        f"{who(i)} ({len(g.players[i].pile)} kaarte)" for i in others) + "</p>", unsafe_allow_html=True)

    st.markdown(chooser_css(top, "kieskaart"), unsafe_allow_html=True)
    with st.container(key="kieskaart"):
        st.markdown(card_head_html(top), unsafe_allow_html=True)
        for s in STATS:
            arrow = "⬆️" if s.higher_wins else "⬇️"
            st.button(f"{s.icon} {s.label} {arrow}", key=f"stat_{s.key}", on_click=choose, args=(s.key,),
                      help=s.hint)
        st.markdown(card_foot_html(top, CREDITS.get(top["id"]))
                    + '<div class="vf-credit">⬆️ hoër wen · ⬇️ laer wen</div>', unsafe_allow_html=True)


def screen_onthul() -> None:
    g: GameState = ss.game
    r = g.last
    stat = BY_KEY[r.stat]
    if r.winner is None:
        banner = f"🤝 Gelykop op {stat.label}! Die kaarte gaan in die pot."
    elif r.winner == r.chooser:
        banner = f"🎉 {who(r.winner)} wen met {stat.label}! Dis weer jou beurt."
    else:
        banner = f"💥 {who(r.winner)} klop {who(r.chooser)} op {stat.label}!"
    if r.winner is not None and r.pot_won:
        banner += f" (+{r.pot_won} uit die pot 🪙)"
    st.markdown(f'<div class="vf-banner">{banner}</div>', unsafe_allow_html=True)

    cols = st.columns(len(r.played))
    best = [i for i, v in r.values.items() if v == (max if stat.higher_wins else min)(r.values.values())]
    for col, (i, cid) in zip(cols, r.played.items()):
        if r.winner is None:
            result = "gelyk" if i in best else "verloor"
        else:
            result = "wen" if i == r.winner else "verloor"
        with col:
            chooser = " (het gekies)" if i == r.chooser else ""
            st.markdown(f"**{who(i)}**{chooser}", unsafe_allow_html=True)
            st.markdown(card(cid, highlight=r.stat, result=result), unsafe_allow_html=True)

    label = "🏁 Kyk wie het gewen!" if g.over else "➡️ Volgende rondte"
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.button(label, on_click=next_round, type="primary", width="stretch")


def screen_einde() -> None:
    g: GameState = ss.game
    winners = g.winners()
    if not winners:
        st.markdown('<div class="vf-curtain">Almal se kaarte is op — dis gelykop! 🤝</div>', unsafe_allow_html=True)
    elif len(winners) == 1:
        st.markdown(f'<div class="vf-curtain">🏆 {who(winners[0])} wen die spel! 🏆</div>', unsafe_allow_html=True)
    else:
        names = " en ".join(who(i) for i in winners)
        st.markdown(f'<div class="vf-curtain">🏆 {names} deel die oorwinning! 🏆</div>', unsafe_allow_html=True)
    if not ss.get("celebrated"):
        st.balloons()
        ss.celebrated = True
    storage.clear_game()

    # Only now, once a kid has won, reveal that Pappa/Mamma never stood a chance.
    if g.rigged and winners and not any(g.players[i].rigged for i in winners):
        parents = " en ".join(who(i) for i, p in enumerate(g.players) if p.rigged)
        kon = "kon" if parents.count(" en ") == 0 else "kon albei"
        st.markdown(
            f'<div class="vf-geheim">🤫 Psst... hierdie spel was gedokter!<br>'
            f'{parents} {kon} nooit wen nie. Die kaarte is {g.swaps} keer stilletjies omgeruil. 😉</div>',
            unsafe_allow_html=True)

    left, mid, right = st.columns([1, 1, 1])
    with mid:
        ranked = sorted(range(len(g.players)), key=lambda i: -len(g.players[i].pile))
        medals = ["🥇", "🥈", "🥉", "🎗️"]
        for place, i in enumerate(ranked):
            st.markdown(f"### {medals[place]} {who(i)} — {len(g.players[i].pile)} kaarte")
        st.caption(f"{g.rounds} rondtes gespeel.")
        st.button("🔄 Speel weer", on_click=quit_game, type="primary", width="stretch")


def screen_oor() -> None:
    st.button("⬅️ Terug", on_click=back_from_about)
    st.markdown("## ℹ️ Oor die kaarte")
    st.markdown(
        "Al 80 karre is regte karre. Die syfers kom uit publieke bronne (vervaardigers se spesifikasies, "
        "Wikipedia en motortydskrifte se toetse). Tye soos 0–100 km/h en die kwartmyl verskil van toets tot "
        "toets, so dit is **benaderde** syfers. Topspoed is die amptelike (soms elektronies beperkte) waarde, "
        "en massa is die leë gewig.\n\n"
        "Die foto's kom van **Wikimedia Commons** en word onder vrye lisensies gebruik. "
        "Die fotograwe word hieronder genoem."
    )
    rows = []
    for cid, car in sorted(CARS.items(), key=lambda kv: kv[1]["naam"]):
        c = CREDITS.get(cid)
        if c:
            lic = f"[{c['licence']}]({c['licence_url']})" if c.get("licence_url") else c["licence"]
            rows.append(f"| {car['naam']} | {c['artist']} | {lic} | [bron]({c['source']}) |")
        else:
            rows.append(f"| {car['naam']} | *(geen foto nie — tekening)* | | |")
    st.markdown("| Kar | Fotograaf | Lisensie | |\n|---|---|---|---|\n" + "\n".join(rows))


sidebar()
{
    "begin": screen_begin,
    "gee_oor": screen_gee_oor,
    "kies": screen_kies,
    "onthul": screen_onthul,
    "einde": screen_einde,
    "oor": screen_oor,
}.get(ss.screen if ss.game is not None or ss.screen == "oor" else "begin", screen_begin)()
