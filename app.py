"""Vinnige Fluite — 'n Afrikaanse Top Trumps-kaartspel met karre vir 2 tot 4 spelers."""

import html
import socket

import segno
import streamlit as st

from game import storage
from game.engine import GameState, new_game, play_round
from game.room import EMOJIS, Room, RoomError, Snapshot
from game.render import CSS, card_back_html, card_foot_html, card_head_html, card_html, chooser_css
from game.stats import BY_KEY, STATS

st.set_page_config(page_title="Vinnige Fluite", page_icon="🏎️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

CARS = storage.load_cars()
CREDITS = storage.load_credits()
EIE = "Eie keuse"
LENGTHS = {"Kort (20 rondtes)": 20, "Medium (40 rondtes)": 40, "Volledig (tot een wen alles)": None, EIE: None}

ss = st.session_state
ss.setdefault("screen", "begin")
ss.setdefault("game", None)


@st.cache_resource
def shared_room() -> Room:
    """The phone game: one Room shared by every browser connected to this computer."""
    return Room()


ROOM = shared_room()


def go(screen: str) -> None:
    ss.screen = screen
    if ss.game is not None and screen not in ("begin", "oor"):
        storage.save_game(ss.game, screen)


def card(cid: str, **kw) -> str:
    return card_html(CARS[cid], CREDITS.get(cid), **kw)


def who(i: int, g: GameState | None = None) -> str:
    p = (g or ss.game).players[i]
    return f"{p.emoji} {html.escape(p.naam)}"


# ---------- actions ----------

def start_game(n: int, names: list[str], max_rounds: int | None) -> None:
    players = [(names[i].strip() or f"Speler {i + 1}", EMOJIS[i]) for i in range(n)]
    ss.game = new_game(players, list(CARS), max_rounds=max_rounds)
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

def scoreboard(g: GameState) -> None:
    for i, p in enumerate(g.players):
        turn = " ⬅️ beurt" if i == g.current and not g.over else ""
        out = " — uit 😢" if not p.active else ""
        afspeel = " ⚔️" if i in g.tied else ""
        st.markdown(f"**{p.emoji} {html.escape(p.naam)}**: {len(p.pile)} kaarte{afspeel}{turn}{out}")
    st.markdown(f"🪙 **Pot:** {len(g.pot)} kaarte")
    limit = f" van {g.max_rounds}" if g.max_rounds else ""
    st.markdown(f"🔁 **Rondte:** {g.rounds}{limit}")


def sidebar(net: Snapshot | None = None) -> None:
    g: GameState | None = net.game if net else ss.game
    with st.sidebar:
        st.markdown("## 🏎️ Vinnige Fluite")
        if g is not None and (net or ss.screen != "begin"):
            st.markdown("### Telbord")
            scoreboard(g)
            st.divider()
        if net or (g is not None and ss.screen != "begin"):
            with st.popover("🏠 Begin oor", width="stretch"):
                st.write("Wil jy regtig hierdie spel stop?" + (" Dit stop die spel op almal se fone." if net else ""))
                st.button("Ja, stop die spel", on_click=ROOM.close if net else quit_game, type="primary")
        st.button("ℹ️ Oor die kaarte", on_click=open_about, width="stretch")


# ---------- screens ----------

def screen_begin() -> None:
    st.markdown('<p class="vf-title">🏎️ Vinnige Fluite 💨</p>', unsafe_allow_html=True)
    st.markdown('<p class="vf-sub">Die kaartspel met 124 regte karre. Wie het die vinnigste fluit?</p>',
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
        max_rounds = LENGTHS[length]
        if length == EIE:
            max_rounds = int(st.number_input("Hoeveel rondtes?", min_value=1, max_value=500, value=30, step=5))
        st.button("🏁 Speel!", on_click=start_game, args=(n, names, max_rounds), type="primary", width="stretch")
        st.button("📱 Speel elkeen op sy eie foon", on_click=ROOM.open, width="stretch",
                  help="Almal se fone moet op dieselfde WiFi as hierdie rekenaar wees.")

        with st.expander("📖 Hoe speel mens?"):
            st.markdown(
                "- Die 124 kaarte word geskommel en uitgedeel.\n"
                "- Wie se beurt dit is, kyk na sy of haar **boonste kaart** en kies iets om te vergelyk.\n"
                "- Almal se boonste kaarte word omgedraai. Die beste waarde wen al die kaarte!\n"
                "  - **Topspoed**, **Krag**, **Wringkrag**, **Produksiejare**, **Enjingrootte** en **Silinders**: hoër wen ⬆️\n"
                "  - **0–100 km/h**, **Kwartmyl**, **Massa** en **Brandstof**: laer wen ⬇️\n"
                "- As jy wen, is dit weer jou beurt. As iemand jou klop, is dit hulle beurt.\n"
                "- Gelykop? Die kaarte gaan in die **pot**. Net die spelers wat gelykop was, speel 'n **afspeel** ⚔️ "
                "totdat een van hulle wen en die hele pot kry.\n"
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
    others = [i for i in g.contenders() if i != g.current]
    if g.tied:
        st.markdown(f'<p class="vf-sub">⚔️ Afspeel om die pot ({len(g.pot)} kaarte)! '
                    'Net die spelers wat gelykop was, speel.</p>', unsafe_allow_html=True)
    st.markdown('<p class="vf-sub">Teen: ' + ", ".join(
        f"{who(i)} ({len(g.players[i].pile)} kaarte)" for i in others) + "</p>", unsafe_allow_html=True)

    show_chooser(top, choose)


def show_chooser(top: dict, on_pick, *args) -> None:
    """The top card with a button per stat; on_pick(*args, stat_key) is called with the choice."""
    st.markdown(chooser_css(top, "kieskaart"), unsafe_allow_html=True)
    with st.container(key="kieskaart"):
        st.markdown(card_head_html(top), unsafe_allow_html=True)
        for s in STATS:
            arrow = "⬆️" if s.higher_wins else "⬇️"
            ok = s.choosable(top)
            st.button(f"{s.icon} {s.label} {arrow}", key=f"stat_{s.key}", on_click=on_pick, args=(*args, s.key),
                      help=s.hint if ok else "'n Elektriese kar het nie 'n enjin nie", disabled=not ok,
                      width="stretch")
        st.markdown(card_foot_html(top, CREDITS.get(top["id"]))
                    + '<div class="vf-credit">⬆️ hoër wen · ⬇️ laer wen</div>', unsafe_allow_html=True)


def screen_onthul() -> None:
    g: GameState = ss.game
    show_reveal(g)
    label = "🏁 Kyk wie het gewen!" if g.over else "➡️ Volgende rondte"
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.button(label, on_click=next_round, type="primary", width="stretch")


def show_reveal(g: GameState) -> None:
    """The result banner and everyone's cards from the last round."""
    r = g.last
    stat = BY_KEY[r.stat]
    if r.winner is None and g.tied:
        names = " en ".join(who(i, g) for i in g.tied)
        banner = f"🤝 Gelykop op {stat.label}! Die kaarte gaan in die pot. ⚔️ Afspeel: net {names} speel volgende."
    elif r.winner is None:
        banner = f"🤝 Gelykop op {stat.label}! Die kaarte gaan in die pot."
    elif r.tie_off:
        banner = f"⚔️ {who(r.winner, g)} wen die afspeel met {stat.label}!"
    elif r.winner == r.chooser:
        banner = f"🎉 {who(r.winner, g)} wen met {stat.label}! Dis weer jou beurt."
    else:
        banner = f"💥 {who(r.winner, g)} klop {who(r.chooser, g)} op {stat.label}!"
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
            st.markdown(f"**{who(i, g)}**{chooser}", unsafe_allow_html=True)
            st.markdown(card(cid, highlight=r.stat, result=result), unsafe_allow_html=True)


def screen_einde() -> None:
    g: GameState = ss.game
    storage.clear_game()
    show_end(g)
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.button("🔄 Speel weer", on_click=quit_game, type="primary", width="stretch")


def show_end(g: GameState) -> None:
    """Who won, the Pappa/Mamma secret, and everyone's final card count."""
    winners = g.winners()
    if not winners:
        st.markdown('<div class="vf-curtain">Almal se kaarte is op — dis gelykop! 🤝</div>', unsafe_allow_html=True)
    elif len(winners) == 1:
        st.markdown(f'<div class="vf-curtain">🏆 {who(winners[0], g)} wen die spel! 🏆</div>', unsafe_allow_html=True)
    else:
        names = " en ".join(who(i, g) for i in winners)
        st.markdown(f'<div class="vf-curtain">🏆 {names} deel die oorwinning! 🏆</div>', unsafe_allow_html=True)
    if not ss.get("celebrated"):
        st.balloons()
        ss.celebrated = True

    # Only now, once a kid has won, reveal that Pappa/Mamma never stood a chance.
    if g.rigged and winners and not any(g.players[i].rigged for i in winners):
        parents = " en ".join(who(i, g) for i, p in enumerate(g.players) if p.rigged)
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
            st.markdown(f"### {medals[place]} {who(i, g)} — {len(g.players[i].pile)} kaarte")
        st.caption(f"{g.rounds} rondtes gespeel.")


# ---------- phone game ----------
# Every phone is its own Streamlit session. The game itself lives in ROOM; a phone knows which
# player it is from the secret token in its URL (?speler=...), so reloading the page is safe.

def lan_url() -> str:
    """The address phones on the same WiFi can open."""
    ip = "127.0.0.1"
    for probe in ("8.8.8.8", "10.255.255.255"):  # UDP connect sends nothing; it only picks the WiFi address
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((probe, 1))
                ip = sock.getsockname()[0]
                break
        except OSError:
            continue
    return f"http://{ip}:{st.get_option('server.port')}"


def my_token() -> str | None:
    return st.query_params.get("speler")


def take_seat(token: str) -> None:
    st.query_params["speler"] = token


def join_room() -> None:
    try:
        take_seat(ROOM.join(ss.get("net_naam", "")))
    except RoomError as e:
        ss.net_error = str(e)


def leave_room() -> None:
    ROOM.leave(my_token())
    st.query_params.pop("speler", None)


def net_choose(token: str, stat_key: str) -> None:
    ROOM.choose(token, stat_key, CARS)


def start_room(max_rounds: int | None) -> None:
    try:
        ROOM.start(list(CARS), max_rounds)
    except RoomError as e:
        ss.net_error = str(e)


@st.fragment(run_every=1)
def watch_room(version: int) -> None:
    """Redraw this phone as soon as someone else changes the game."""
    if ROOM.version != version:
        st.rerun()


def join_link() -> None:
    url = lan_url()
    qr = segno.make(url, error="m")
    st.markdown(f'<div style="text-align:center"><img src="{qr.svg_data_uri(scale=6, border=2)}" '
                f'style="width:220px;max-width:100%" alt="QR-kode"><br><b style="font-size:1.3rem">{url}</b></div>',
                unsafe_allow_html=True)
    st.caption("Skandeer die QR-kode met jou foon se kamera, of tik die adres in. "
               "Die fone moet op dieselfde WiFi as hierdie rekenaar wees.")


def net_lobby(net: Snapshot, me: int | None) -> None:
    st.markdown('<p class="vf-title">📱 Vinnige Fluite</p>', unsafe_allow_html=True)
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        if me is None:
            join_link()
            if len(net.seats) < 4:
                with st.form("aansluit", border=False):
                    st.text_input("Wat is jou naam?", key="net_naam", max_chars=16)
                    st.form_submit_button("🙋 Sluit aan", on_click=join_room, type="primary", width="stretch")
        else:
            st.markdown(f'<div class="vf-banner">Jy is {EMOJIS[me]} {html.escape(net.seats[me].naam)}</div>',
                        unsafe_allow_html=True)
        if msg := ss.pop("net_error", None):
            st.error(msg)

        st.markdown(f"### Spelers ({len(net.seats)} van 4)")
        for i, seat in enumerate(net.seats):
            st.markdown(f"{EMOJIS[i]} **{html.escape(seat.naam)}**" + (" (jy)" if i == me else ""))
        if not net.seats:
            st.caption("Nog niemand nie. Wag vir die fone om aan te sluit…")

        if len(net.seats) >= 2:
            length = st.radio("Hoe lank wil julle speel?", list(LENGTHS), horizontal=True, key="net_length")
            max_rounds = LENGTHS[length]
            if length == EIE:
                max_rounds = int(st.number_input("Hoeveel rondtes?", min_value=1, max_value=500, value=30, step=5,
                                                 key="net_rounds"))
            st.button("🏁 Almal is hier, speel!", on_click=start_room, args=(max_rounds,), type="primary",
                      width="stretch")
        if me is not None:
            st.button("🚪 Verlaat", on_click=leave_room)
            with st.expander("📲 Nog spelers? Wys hulle hierdie kode"):
                join_link()


def net_kies(net: Snapshot, me: int | None) -> None:
    g = net.game
    if me == g.current:
        top = CARS[g.players[me].pile[0]]
        st.markdown(f'<div class="vf-banner">Dis jou beurt, {who(me, g)}! Tik op jou sterkste punt.</div>',
                    unsafe_allow_html=True)
        if g.tied:
            st.markdown(f'<p class="vf-sub">⚔️ Afspeel om die pot ({len(g.pot)} kaarte)!</p>', unsafe_allow_html=True)
        show_chooser(top, net_choose, my_token())
        return
    st.markdown(f'<div class="vf-curtain">{who(g.current, g)} kies nou… 🤔</div>', unsafe_allow_html=True)
    if me is not None:
        p = g.players[me]
        left, mid, right = st.columns([1, 1, 1])
        with mid:
            if not p.active or not p.pile:
                st.markdown(card_back_html("Jy is uit 😢"), unsafe_allow_html=True)
            elif me not in g.contenders():
                st.markdown(card_back_html(f"{len(p.pile)} kaarte · jy sit hierdie afspeel oor"),
                            unsafe_allow_html=True)
            else:
                st.markdown('<p class="vf-sub">Jou kaart:</p>', unsafe_allow_html=True)
                st.markdown(card(p.pile[0]), unsafe_allow_html=True)


def net_onthul(net: Snapshot, me: int | None) -> None:
    g = net.game
    show_reveal(g)
    label = "🏁 Kyk wie het gewen!" if g.over else "➡️ Volgende rondte"
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.button(label, on_click=ROOM.next_round, args=(net.version,), type="primary", width="stretch")


def net_einde(net: Snapshot, me: int | None) -> None:
    show_end(net.game)
    left, mid, right = st.columns([1, 1, 1])
    with mid:
        st.button("🔄 Speel weer", on_click=ROOM.play_again, type="primary", width="stretch",
                  help="Terug na die wagkamer met dieselfde spelers")


def net_screen(net: Snapshot) -> None:
    me = ROOM.seat_of(my_token())
    if net.phase != "einde":
        ss.celebrated = False
    if net.game is not None:
        if me is not None:
            p = net.game.players[me]
            st.caption(f"Jy is {p.emoji} {html.escape(p.naam)} · {len(p.pile)} kaarte · rondte {net.game.rounds}")
        else:
            with st.expander("🙋 Is jy een van die spelers? Tik jou naam"):
                for i, seat in enumerate(net.seats):
                    st.button(f"{EMOJIS[i]} {seat.naam}", key=f"seat{i}", on_click=take_seat,
                              args=(ROOM.token_for(i),))
    {"lobby": net_lobby, "kies": net_kies, "onthul": net_onthul, "einde": net_einde}[net.phase](net, me)
    watch_room(net.version)


def screen_oor() -> None:
    st.button("⬅️ Terug", on_click=back_from_about)
    st.markdown("## ℹ️ Oor die kaarte")
    st.markdown(
        "Al 124 karre is regte karre. Die syfers kom uit publieke bronne (vervaardigers se spesifikasies, "
        "Wikipedia en motortydskrifte se toetse). Tye soos 0–100 km/h en die kwartmyl verskil van toets tot "
        "toets, so dit is **benaderde** syfers. Topspoed is die amptelike (soms elektronies beperkte) waarde, "
        "en massa is die leë gewig. Brandstof is die amptelike Europese gekombineerde verbruik. Elektriese karre ⚡ "
        "kry die Europese petrol-ekwivalent: hul kWh per 100 km gedeel deur 8,9 (die energie in een liter petrol).\n\n"
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


net = ROOM.snapshot() if ss.game is None and ss.screen != "oor" else None  # a one-screen game keeps going
if net and net.phase is not None:
    sidebar(net)
    net_screen(net)
    st.stop()

sidebar()
{
    "begin": screen_begin,
    "gee_oor": screen_gee_oor,
    "kies": screen_kies,
    "onthul": screen_onthul,
    "einde": screen_einde,
    "oor": screen_oor,
}.get(ss.screen if ss.game is not None or ss.screen == "oor" else "begin", screen_begin)()
