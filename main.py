import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from collections import defaultdict
import asyncio
import json
import random
import time
from datetime import datetime, timedelta, timezone
import io
import numpy as np
import shutil
import aiohttp
from zoneinfo import ZoneInfo
import re

# =========================
# Boot / Config
# =========================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
AT_USER = os.getenv("ATERNOS_USERNAME")
AT_PASS = os.getenv("ATERNOS_PASSWORD")
ATERNOS_SUBDOMAIN = os.getenv("ATERNOS_SUBDOMAIN")
COVER_BOT_ID = 684773505157431347
COVER_INVITE_URL = "https://top.gg/bot/684773505157431347/invite?campaign=210-3"
RESTRICT_GUILD_NAME = "QMUL - Unofficial"
MONEY_LOCKS = defaultdict(asyncio.Lock)
ALWAYS_BANKROB_USER_ID = 734468552903360594  # always succeed on !bankrob for this user
BANKROB_STEAL_MIN_PCT = 0.12   # 12% lower bound
BANKROB_STEAL_MAX_PCT = 0.28   # 28% upper bound
BANKROB_MIN_STEAL     = 100    # absolute minimum when success (matches your 100 bank threshold)
BANKROB_MAX_STEAL_PCT_CAP = 0.40  # hard cap: never take more than 40% in a single success

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# Files / Constants
# =========================
MARRIAGE_PROPOSALS: dict[str, str] = {}
MARRIAGE_FILE = "marriages.json"
COIN_DATA_FILE = "coins.json"
SHOP_FILE = "shop_stock.json"
INVENTORY_FILE = "inventories.json"
PLAYLIST_FILE = "playlists.json"
QUEST_FILE = "quests.json"
EVENT_FILE = "events.json"
STOCK_FILE = "stocks.json"
SUGGESTION_FILE = "suggestions.json"
TRIVIA_STATS_FILE = "trivia_stats.json"
TRIVIA_STREAKS_FILE = "trivia_streaks.json"
BEG_STATS_FILE = "beg_stats.json"

ANNOUNCEMENT_CHANNEL_ID = 1433248053665726547
WELCOME_CHANNEL_ID = 1433248053665726546
MARKET_ANNOUNCE_CHANNEL_ID = 1433412796531347586
SUGGESTION_CHANNEL_ID = 1433413006842396682  # set to your #suggestions channel

TOP_ROLE_NAME = "🌟 EXP Top"

INTEREST_RATE = 0.02          # 2% bank interest
INTEREST_INTERVAL = 3600      # hourly
DIVIDEND_RATE = 0.01          # 1% portfolio value
DIVIDEND_INTERVAL = 86400     # daily
XP_PER_MESSAGE = 10

# Economy / Items
SHOP_ITEMS = ["Anime body pillow", "Oreo plush", "Rtx5090", "Crash token", "Imran's nose"]
ITEM_PRICES = {
    "Anime body pillow": 30000,
    "Oreo plush": 15000,
    "Rtx5090": 150000,
    "Crash token": 175000,
    "Imran's nose": 999999,
}
CRASH_TOKEN_NAME = "Crash token"  # normalize on this

# Stocks (consistent casing everywhere)
STOCKS = ["Oreobux", "QMkoin", "Seelsterling", "Fwizfinance", "BingBux"]
STOCK_PURCHASE_COUNT = {stock: 0 for stock in STOCKS}

# Blackjack (solo + placeholder for future lobbies)
SOLO_BLACKJACK_GAMES = {}
blackjack_lobbies = defaultdict(lambda: {
    "players": [],
    "bets": {},
    "dealer_hand": [],
    "game_started": False,
    "current_turn": 0,
    "hands": {},
    "scores": {},
})

# Quests / Events
QUEST_POOL = [
    {"task": "Rob someone", "command": "!rob", "reward": 100},
    {"task": "Win a gamble", "command": "!gamble", "reward": 150},
    {"task": "Use !daily", "command": "!daily", "reward": 75},
    {"task": "Buy stock", "command": "!buy <stock> <amount>", "reward": 200},
    {"task": "Reach 1 level up", "command": "Chat", "reward": 100},
]
EVENTS = {
    "Double XP": {"xp_mult": 2},
    "Crash Week": {"crash_odds": 0.3},
    "Boom Frenzy": {"boom_odds": 0.3},
    "Coin Rain": {"bonus_daily": 100},
}

# AFK / XP
AFK_STATUS = {}
DATA_FILE = "data.json"
COOLDOWN_FILE = "cooldowns.json"
VOICE_XP_COOLDOWN = {}

# Role colour reactions
ROLE_COLOR_EMOJIS = {
    "🟥": "Red",
    "🟩": "Green",
    "🟦": "Blue",
    "🟨": "Yellow",
    "🟪": "Purple",
    "⬛": "Black",
}

# Snake
wall = "⬜"
innerWall = "⬛"
energy = "🍎"
snakeHead = "😍"
snakeBody = "🟨"
snakeLoose = "😵"

# =========================
# Minecraft (!mc)
# =========================

MC_NAME = "QMUL Survival"
MC_ADDRESS = "qmul-survival.modrinth.gg"

# IMPORTANT: For SRV-based Java domains, do NOT force a port.
MC_JAVA_PORT = None  # keep None unless you truly know the Java port and do not use SRV

# Links (buttons only show if non-empty)
MC_MODRINTH_URL = ""
MC_MAP_URL = ""      # e.g. "https://map.example.com"
MC_RULES_URL = ""    # e.g. "https://example.com/rules"
MC_DISCORD_URL = "https://discord.gg/7uc8B4YN"

# Display info
MC_VERSION = "1.20.10"
MC_LOADER = "Fabric"
MC_MODPACK_NAME = "QMUL Survival Pack"
MC_WHITELISTED = False
MC_REGION = "UK / London"

MC_NOTES = [
    "Be respectful — no griefing.",
    "No x-ray / cheating clients.",
    "Ask an admin if you need help.",
]

# Bedrock info disabled for clean UX (enable only if you truly want Bedrock join instructions shown)
MC_SHOW_BEDROCK = False
MC_BEDROCK_PORT = 22165  # display-only if MC_SHOW_BEDROCK=True

LONDON_TZ = ZoneInfo("Europe/London")

PRAYER_UPDATES_CHANNEL_ID = 1471992400351334626  # <-- your channel

# You pasted this URL truncated; keep it as-is if it works, but you likely need the full IDMF value.
RAMADAN_TIMETABLE_IMAGE_URL = "https://www.eastlondonmosque.org.uk/Handlers/GetImage.ashx?IDMF=563cffb2-14c6-4a1f-a94f-"

ELM_PRAYER_TEST_URL = "https://www.eastlondonmosque.org.uk/prayer-times-test"

PRAYER_NOTIF_STATE_FILE = "prayer_notif_state.json"   # remembers what we've already notified today
RAMADAN_POST_STATE_FILE  = "ramadan_post_state.json"  # remembers if we already posted today's iftar update


class MCLinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        if MC_MODRINTH_URL:
            self.add_item(discord.ui.Button(label="Modrinth", url=MC_MODRINTH_URL))
        if MC_MAP_URL:
            self.add_item(discord.ui.Button(label="Live Map", url=MC_MAP_URL))
        if MC_RULES_URL:
            self.add_item(discord.ui.Button(label="Rules", url=MC_RULES_URL))
        if MC_DISCORD_URL:
            self.add_item(discord.ui.Button(label="Discord", url=MC_DISCORD_URL))


async def fetch_mc_status_fallback(address: str):
    """
    SRV-friendly fallback status provider (public API).
    """
    url = f"https://api.mcsrvstat.us/2/{address}"
    timeout = aiohttp.ClientTimeout(total=6)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Fallback API returned HTTP {resp.status}")
            return await resp.json()


def _safe_join_url(label: str, url: str) -> str:
    # Keeps links tidy + consistent
    return f"{label}: {url}"


@bot.command(name="mc", help="Show Minecraft server info (IP, version, modpack, status, etc.)")
async def mc(ctx: commands.Context):
    address = MC_ADDRESS

    # --- Player-facing description (NO ports for Java SRV) ---
    desc_lines = [
        f"**Bedrock Port:** 22050",
        "**Java Port:** 22165",
        "",
        "**Join (Java):** `qmul-survival.modrinth.gg`",
        "",
        "**How to join:** Multiplayer → Add Server → paste the address above.",
    ]

    # Optional Bedrock info (only if you want it displayed)
    if MC_SHOW_BEDROCK:
        desc_lines += [
            "",
            f"**Bedrock Address:** `{address}`",
            f"**Bedrock Port:** `{MC_BEDROCK_PORT}`",
        ]

    embed = discord.Embed(
        title=f"⛏️ {MC_NAME} — Minecraft Server",
        description="\n".join(desc_lines),
        color=discord.Color.purple()
    )

    # Core info
    embed.add_field(name="Version", value=f"`{MC_VERSION}`", inline=True)
    embed.add_field(name="Loader", value=f"`{MC_LOADER}`", inline=True)
    embed.add_field(name="Modpack", value=f"`{MC_MODPACK_NAME}`", inline=True)

    # Optional extra info (kept compact)
    embed.add_field(name="Access", value=("Whitelist ON" if MC_WHITELISTED else "Public / No whitelist"), inline=True)
    embed.add_field(name="Region", value=MC_REGION, inline=True)

    # Notes
    if MC_NOTES:
        embed.add_field(
            name="📌 Notes",
            value="\n".join(f"• {x}" for x in MC_NOTES)[:1024],
            inline=False
        )

    # Links (also shown as buttons below)
    link_lines = []
    if MC_MODRINTH_URL:
        link_lines.append(_safe_join_url("Modrinth", MC_MODRINTH_URL))
    if MC_MAP_URL:
        link_lines.append(_safe_join_url("Live Map", MC_MAP_URL))
    if MC_RULES_URL:
        link_lines.append(_safe_join_url("Rules", MC_RULES_URL))
    if MC_DISCORD_URL:
        link_lines.append(_safe_join_url("Discord", MC_DISCORD_URL))

    if link_lines:
        embed.add_field(name="Links", value="\n".join(link_lines)[:1024], inline=False)

    # =========================
    # Live Status (Java)
    # =========================
    live_status_set = False

    # ---- Attempt 1: mcstatus (best for Java; DO NOT force SRV domains) ----
    try:
        from mcstatus import JavaServer

        def ping_java():
            # Let SRV resolve: do NOT include port unless you explicitly know the Java port
            if MC_JAVA_PORT:
                server = JavaServer.lookup(f"{address}:{MC_JAVA_PORT}")
            else:
                server = JavaServer.lookup(address)
            return server.status()

        status = await asyncio.to_thread(ping_java)

        online = getattr(status.players, "online", None)
        maxp = getattr(status.players, "max", None)

        motd_plain = None
        try:
            motd_plain = status.motd.to_plain()
        except Exception:
            motd_plain = None

        # Status field (clean)
        if online is not None and maxp is not None:
            embed.add_field(name="🟢 Server Status", value=f"Online — **{online}/{maxp}** players", inline=False)
        else:
            embed.add_field(name="🟢 Server Status", value="Online", inline=False)

        # MOTD
        if motd_plain:
            embed.add_field(name="MOTD", value=motd_plain[:1000], inline=False)

        # Ping
        latency_ms = getattr(status, "latency", None)
        if latency_ms is not None:
            embed.add_field(name="Ping", value=f"{latency_ms:.0f} ms", inline=True)

        live_status_set = True

    except ModuleNotFoundError:
        # mcstatus not installed; try fallback
        pass
    except Exception:
        # mcstatus failed; try fallback
        pass

    # ---- Attempt 2: SRV-friendly fallback API ----
    if not live_status_set:
        try:
            data = await fetch_mc_status_fallback(address)

            if not data.get("online"):
                embed.add_field(name="🔴 Server Status", value="Offline", inline=False)
            else:
                players = data.get("players") or {}
                online = players.get("online", "?")
                maxp = players.get("max", "?")
                embed.add_field(name="🟢 Server Status", value=f"Online — **{online}/{maxp}** players", inline=False)

                motd = data.get("motd") or {}
                clean = motd.get("clean")
                if isinstance(clean, list) and clean:
                    embed.add_field(name="MOTD", value="\n".join(clean)[:1000], inline=False)

        except Exception:
            embed.add_field(
                name="⚠️ Live Status",
                value="Couldn’t fetch status right now.",
                inline=False
            )

    embed.set_footer(text=f"Copy/paste Java join IP: {address}")

    view = MCLinksView()
    await ctx.send(embed=embed, view=view)

# =========================
# Utilities: File I/O
# =========================
def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def _save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=4)

def load_data():
    return _load_json(DATA_FILE, {})

def save_data(d):
    _save_json(DATA_FILE, d)

def load_cooldowns():
    return _load_json(COOLDOWN_FILE, {})

def save_cooldowns(d):
    _save_json(COOLDOWN_FILE, d)

def load_coins():
    return _load_json(COIN_DATA_FILE, {})

def save_coins(d):
    _save_json(COIN_DATA_FILE, d)

def load_marriages():
    return _load_json(MARRIAGE_FILE, {})

def save_marriages(d):
    _save_json(MARRIAGE_FILE, d)

def load_shop_stock():
    if not os.path.exists(SHOP_FILE):
        return {item: 0 for item in SHOP_ITEMS}
    return _load_json(SHOP_FILE, {item: 0 for item in SHOP_ITEMS})

def save_shop_stock(d):
    _save_json(SHOP_FILE, d)

def load_inventory():
    return _load_json(INVENTORY_FILE, {})

def save_inventory(d):
    _save_json(INVENTORY_FILE, d)

def load_playlists():
    return _load_json(PLAYLIST_FILE, {})

def save_playlists(d):
    _save_json(PLAYLIST_FILE, d)

def load_quests():
    return _load_json(QUEST_FILE, {})

def save_quests(d):
    _save_json(QUEST_FILE, d)

def load_event():
    return _load_json(EVENT_FILE, {})

def save_event(d):
    _save_json(EVENT_FILE, d)

def save_stocks(d):
    _save_json(STOCK_FILE, d)

def load_stocks():
    if not os.path.exists(STOCK_FILE):
        data = {
            "Oreobux": {"price": 100, "history": [100]},
            "QMkoin": {"price": 150, "history": [150]},
            "Seelsterling": {"price": 200, "history": [200]},
            "Fwizfinance": {"price": 250, "history": [250]},
        }
        save_stocks(data)
        return data
    data = _load_json(STOCK_FILE, {})
    # Repair unknown/missing structure & enforce keys/casing
    changed = False
    template = {
        "Oreobux": {"price": 100, "history": [100]},
        "QMkoin": {"price": 150, "history": [150]},
        "Seelsterling": {"price": 200, "history": [200]},
        "Fwizfinance": {"price": 250, "history": [250]},
    }
    fixed = {}
    for key in STOCKS:
        entry = data.get(key)
        if not entry:
            # try to map wrong-cased keys
            for k in data.keys():
                if k.lower() == key.lower():
                    entry = data[k]
                    changed = True
                    break
        if not entry or "price" not in entry or "history" not in entry:
            fixed[key] = template[key]
            changed = True
        else:
            fixed[key] = entry
    if changed:
        save_stocks(fixed)
    return fixed

def load_beg_stats():
    return _load_json(BEG_STATS_FILE, {})


def save_beg_stats(d):
    _save_json(BEG_STATS_FILE, d)

import re

def _load_state(path: str, default: dict):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def _save_state(path: str, obj: dict):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

async def fetch_elm_today():
    """
    Scrape https://www.eastlondonmosque.org.uk/prayer-times-test and extract today's row.
    Row format (observed):
    DD/MM/YYYY Hijri Sunrise FajrBeg FajrJam ZuhrBeg ZuhrJam AsrBeg AsrJam MagBeg MagJam IshaBeg IshaJam
    """
    today = datetime.now(LONDON_TZ).strftime("%d/%m/%Y")

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(ELM_PRAYER_TEST_URL) as resp:
            if resp.status != 200:
                raise RuntimeError(f"ELM prayer page HTTP {resp.status}")
            text = await resp.text()

    # Find the line that starts with today's date.
    # Example:
    # 13/02/2026 25 Sha‘bān 1447 7:15 5:38 5:58 12:20 1:00 2:43 3:23 3:45 5:15 5:22 6:45 7:30
    pattern = rf"^{re.escape(today)}\s+(.+?)$"
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"Could not find today's row for {today}")

    row = m.group(0).strip()
    parts = row.split()

    # parts[0] = date
    # parts[1..3] = hijri (often 3 tokens, e.g. "25", "Sha‘bān", "1447")
    # then 10 time tokens
    if len(parts) < 14:
        raise RuntimeError(f"Unexpected row format: {row}")

    date_str = parts[0]
    hijri = " ".join(parts[1:4])
    times = parts[4:14]  # 10 items

    keys = [
        "sunrise",
        "fajr_beg", "fajr_jam",
        "zuhr_beg", "zuhr_jam",
        "asr_beg", "asr_jam",
        "maghrib_beg", "maghrib_jam",
        "isha_beg", "isha_jam",
    ]

    # The row provides exactly 10 time tokens after hijri + sunrise? (ELM row includes sunrise + 9 others = 10)
    # Observed: sunrise + (fajr beg/jam) + (zuhr beg/jam) + (asr beg/jam) + (maghrib beg/jam) + (isha beg/jam) = 11
    # BUT from the page: after Hijri there are 11 time values:
    # sunrise, fajr beg, fajr jam, zuhr beg, zuhr jam, asr beg, asr jam, maghrib beg, maghrib jam, isha beg, isha jam
    # So we should take 11, not 10.
    times = parts[4:15]
    if len(times) != 11:
        raise RuntimeError(f"Expected 11 time tokens, got {len(times)}: {times}")

    data = dict(zip(keys, times))

    def to_dt(hhmm: str) -> datetime:
        # times are like "5:38" or "12:20" (no leading zero)
        h, m = hhmm.split(":")
        now = datetime.now(LONDON_TZ)
        return now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

    # Build dt objects for begins times for notifications
    begins = {
        "Fajr": to_dt(data["fajr_beg"]),
        "Zuhr": to_dt(data["zuhr_beg"]),
        "Asr": to_dt(data["asr_beg"]),
        "Maghrib": to_dt(data["maghrib_beg"]),
        "Isha": to_dt(data["isha_beg"]),
    }

    jamaah = {
        "Fajr": to_dt(data["fajr_jam"]),
        "Zuhr": to_dt(data["zuhr_jam"]),
        "Asr": to_dt(data["asr_jam"]),
        "Maghrib": to_dt(data["maghrib_jam"]),
        "Isha": to_dt(data["isha_jam"]),
    }

    return {
        "date": date_str,
        "hijri": hijri,
        "raw": data,
        "begins": begins,
        "jamaah": jamaah,
    }

# =========================
# Snake (reaction + command controls)
# =========================
SNAKE_GAMES = {}  # channel_id -> {"matrix": np.ndarray, "points": int, "is_out": bool, "msg_id": int}

SNAKE_CONTROLS = {
    "⬆️": "up",
    "⬇️": "down",
    "⬅️": "left",
    "➡️": "right",
    "🔄": "reset",
}

def _snake_new_matrix():
    # 12x12 with border = 0 (wall), inside = 1 (empty), head = 2, body = 3, energy = 4, lose = 5
    m = np.array([
        [0]*12,
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*9 +[2]+[0],  # start head at (3,10)
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]+[1]*10+[0],
        [0]*12,
    ])
    return m

def _snake_generate_energy(state):
    m = state["matrix"]
    # keep trying until we place on an empty cell (1)
    for _ in range(200):
        i = random.randint(1,10)
        j = random.randint(1,10)
        if m[i][j] == 1:
            m[i][j] = 4
            return

def _snake_grid_to_text(m):
    out = []
    for row in m:
        line = []
        for v in row:
            if v == 0:
                line.append(wall)
            elif v == 1:
                line.append(innerWall)
            elif v == 2:
                line.append(snakeHead)
            elif v == 3:
                line.append(snakeBody)
            elif v == 4:
                line.append(energy)
            else:
                line.append(snakeLoose)
        out.append("".join(line))
    return "\n".join(out)

def _snake_is_boundary(i, j):
    return i == 0 or j == 0 or i == 11 or j == 11

def _snake_handle_energy(state, i, j):
    m = state["matrix"]
    if m[i][j] == 4:
        state["points"] += 1
        _snake_generate_energy(state)

def _snake_update_head(state, ni, nj):
    m = state["matrix"]
    # current head
    head = np.argwhere(m == 2)
    if head.size == 0:
        return
    hi, hj = head[0]
    m[ni][nj] = 2
    m[hi][hj] = 1  # turn old head to empty (we aren't tracking tail segments; body is cosmetic)
    # optional: leave a short body trail
    # m[hi][hj] = 3

def _snake_move(state, direction):
    if state["is_out"]:
        return
    m = state["matrix"]
    hi, hj = np.argwhere(m == 2)[0]
    di, dj = 0, 0
    if direction == "up":
        di, dj = -1, 0
    elif direction == "down":
        di, dj = 1, 0
    elif direction == "left":
        di, dj = 0, -1
    elif direction == "right":
        di, dj = 0, 1
    ni, nj = hi + di, hj + dj

    if _snake_is_boundary(ni, nj):
        m[hi][hj] = 5  # lose face on current head
        state["is_out"] = True
        return

    _snake_handle_energy(state, ni, nj)
    _snake_update_head(state, ni, nj)

async def _snake_render(ctx_or_channel, state, *, title="Pick Apple Game"):
    desc = _snake_grid_to_text(state["matrix"])
    embed = discord.Embed(title=title, description=desc, color=discord.Color.green())
    embed.add_field(name="Your Score", value=state["points"], inline=True)
    channel = ctx_or_channel.channel if hasattr(ctx_or_channel, "channel") else ctx_or_channel
    if state.get("msg_id"):
        try:
            msg = await channel.fetch_message(state["msg_id"])
            await msg.edit(embed=embed)
            return msg
        except discord.NotFound:
            state["msg_id"] = None
    msg = await channel.send(embed=embed)
    state["msg_id"] = msg.id
    for emoji in ("⬆️","⬇️","⬅️","➡️","🔄"):
        try:
            await msg.add_reaction(emoji)
        except Exception:
            pass
    return msg

def _snake_reset_state():
    state = {"matrix": _snake_new_matrix(), "points": 0, "is_out": False, "msg_id": None}
    _snake_generate_energy(state)
    return state

@bot.command(name="snake", help="Play the emoji snake! Usage: !snake start | !snake w/a/s/d | !snake reset")
async def snake_cmd(ctx, action: str = "start"):
    ch_id = ctx.channel.id
    action = action.lower()

    if action in ("start", "reset"):
        SNAKE_GAMES[ch_id] = _snake_reset_state()
        await _snake_render(ctx, SNAKE_GAMES[ch_id], title=f"Pick Apple Game • {ctx.author.display_name}")
        await ctx.send("Use reactions ⬆️ ⬇️ ⬅️ ➡️ to move, or `!snake w/a/s/d`. `!snake reset` to restart.")
        return

    if ch_id not in SNAKE_GAMES:
        SNAKE_GAMES[ch_id] = _snake_reset_state()

    move_map = {"w":"up","a":"left","s":"down","d":"right","up":"up","down":"down","left":"left","right":"right"}
    if action not in move_map:
        return await ctx.send("❌ Invalid action. Use `start`, `reset`, or one of `w/a/s/d`.")

    state = SNAKE_GAMES[ch_id]
    if state["is_out"]:
        return await ctx.send(embed=discord.Embed(title="Game Over", description=f"Final score: **{state['points']}**", color=discord.Color.red()))

    _snake_move(state, move_map[action])
    if state["is_out"]:
        await _snake_render(ctx, state)
        return await ctx.send(embed=discord.Embed(title="Game Over", description=f"Scored: **{state['points']}**", color=discord.Color.red()))
    await _snake_render(ctx, state)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # ignore bot’s own reactions
    if payload.user_id == (bot.user.id if bot.user else None):
        return

    guild = bot.get_guild(payload.guild_id)

    # ===== Role Colour Handler =====
    try:
        with open("role_colour_msg.txt", "r") as f:
            target_msg_id = int(f.read())
    except FileNotFoundError:
        target_msg_id = None

    if target_msg_id and payload.message_id == target_msg_id:
        member = payload.member or (guild.get_member(payload.user_id) if guild else None)
        if not guild or not member:
            return
        role_name = ROLE_COLOR_EMOJIS.get(str(payload.emoji))
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(name=role_name, colour=discord.Colour.default())
                except discord.Forbidden:
                    role = None
            if role:
                # remove other colour roles
                for rname in ROLE_COLOR_EMOJIS.values():
                    r = discord.utils.get(guild.roles, name=rname)
                    if r and r in member.roles and r.name != role_name:
                        await member.remove_roles(r)
                if role not in member.roles:
                    await member.add_roles(role)
                # remove other reactions by this user on same message
                channel = guild.get_channel(payload.channel_id)
                if channel:
                    msg = await channel.fetch_message(payload.message_id)
                    for reaction in msg.reactions:
                        if str(reaction.emoji) != str(payload.emoji):
                            async for u in reaction.users():
                                if u.id == member.id:
                                    await reaction.remove(member)

    # ===== Snake Handler =====
    ch_id = payload.channel_id
    state = SNAKE_GAMES.get(ch_id)
    if state and state.get("msg_id") and payload.message_id == state["msg_id"]:
        emoji = str(payload.emoji)
        action = SNAKE_CONTROLS.get(emoji)
        if not action:
            return
        channel = guild.get_channel(ch_id) if guild else None
        if not channel:
            return

        if action == "reset":
            SNAKE_GAMES[ch_id] = _snake_reset_state()
            await _snake_render(channel, SNAKE_GAMES[ch_id])
            return

        if state["is_out"]:
            await channel.send(embed=discord.Embed(
                title="Game Over",
                description=f"Scored: **{state['points']}**",
                color=discord.Color.red()
            ))
            return

        _snake_move(state, action)
        if state["is_out"]:
            await _snake_render(channel, state)
            await channel.send(embed=discord.Embed(
                title="Game Over",
                description=f"Scored: **{state['points']}**",
                color=discord.Color.red()
            ))
        else:
            await _snake_render(channel, state)

def only_mention_target(ctx) -> int | None:
    # require exactly one user mention and use that ID
    if len(ctx.message.mentions) != 1:
        return None
    return ctx.message.mentions[0].id

# =========================
# Trivia
# =========================
def load_trivia_stats():
    return _load_json(TRIVIA_STATS_FILE, {})

def save_trivia_stats(d):
    _save_json(TRIVIA_STATS_FILE, d)

def load_trivia_streaks(): return _load_json(TRIVIA_STREAKS_FILE, {})
def save_trivia_streaks(d): _save_json(TRIVIA_STREAKS_FILE, d)

def add_trivia_result(uid: str, category: str, correct: bool):
    stats = load_trivia_stats()
    user = stats.setdefault(uid, {})
    cat = user.setdefault(category, {"correct": 0, "attempts": 0})
    cat["attempts"] += 1
    if correct:
        cat["correct"] += 1
    save_trivia_stats(stats)

import aiohttp

@bot.command(name="trivia", help="Answer a trivia question with emoji reactions!")
async def trivia(ctx):
    url = "https://the-trivia-api.com/v2/questions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return await ctx.send("❌ Could not reach Trivia API. Try again later.")
            data = await resp.json()

    if not data:
        return await ctx.send("❌ No trivia received.")

    q = data[0]
    question = q["question"]["text"]
    correct = q["correctAnswer"]
    options = q["incorrectAnswers"] + [correct]
    random.shuffle(options)

    # Normalise category label for stats
    raw_cat = q.get("category", "General")
    category = (raw_cat[0] if isinstance(raw_cat, list) and raw_cat else raw_cat)
    category = str(category).title()

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    option_lines = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))

    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=f"**{question}**\n\n{option_lines}\n\nReact with the correct answer!",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=embed)

    for emoji in emojis:
        await msg.add_reaction(emoji)

    def check(payload):
        return (
            payload.user_id == ctx.author.id and
            payload.message_id == msg.id and
            str(payload.emoji) in emojis
        )

    try:
        payload = await bot.wait_for("raw_reaction_add", timeout=20.0, check=check)
    except asyncio.TimeoutError:
        return await ctx.send(f"⏰ Out of time! The correct answer was **{correct}**.")

    choice_index = emojis.index(str(payload.emoji))
    chosen = options[choice_index]

    # ===== Streaks + rewards (Part A) =====
    uid = str(ctx.author.id)
    streaks = load_trivia_streaks()
    streak = int(streaks.get(uid, 0))

    if chosen == correct:
        streak += 1
        reward_base = 50
        streak_bonus = 5 * min(streak - 1, 10)  # cap bonus after 10 steps
        reward = reward_base + streak_bonus

        coins = ensure_user_coins(ctx.author.id)
        coins[uid]["wallet"] += reward
        save_coins(coins)
        await update_xp(ctx.author.id, ctx.guild.id, 20)

        add_trivia_result(uid, category, True)
        streaks[uid] = streak
        save_trivia_streaks(streaks)

        await ctx.send(f"✅ Correct! **+{reward}** coins (streak **{streak}**).")
    else:
        add_trivia_result(uid, category, False)
        streaks[uid] = 0
        save_trivia_streaks(streaks)

        await ctx.send(f"❌ Wrong! The correct answer was **{correct}**. Streak reset.")

@bot.command(name="triviastats", help="Show how many you got right/wrong in each trivia category. Usage: !triviastats [@user]")
async def triviastats(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)
    stats = load_trivia_stats()
    u = stats.get(uid)

    if not u:
        return await ctx.send(f"📊 No trivia stats for **{member.display_name}** yet.")

    # Build per-category rows and totals
    rows = []
    total_attempts = 0
    total_correct = 0
    for cat, rec in u.items():
        attempts = int(rec.get("attempts", 0))
        correct  = int(rec.get("correct", 0))
        wrong    = attempts - correct
        acc = (correct / attempts * 100.0) if attempts else 0.0
        total_attempts += attempts
        total_correct  += correct
        rows.append((cat, correct, wrong, attempts, acc))

    # Sort by most attempts
    rows.sort(key=lambda r: r[3], reverse=True)

    # Format output
    lines = []
    for cat, correct, wrong, attempts, acc in rows[:20]:  # show up to 20 categories
        lines.append(f"**{cat}** — ✅ {correct} · ❌ {wrong} · {attempts} total · {acc:.0f}%")

    overall_acc = (total_correct / total_attempts * 100.0) if total_attempts else 0.0
    embed = discord.Embed(
        title=f"📊 Trivia Stats — {member.display_name}",
        description="\n".join(lines) if lines else "No data yet.",
        color=discord.Color.teal()
    )
    embed.set_footer(text=f"Overall: ✅ {total_correct} / {total_attempts} · {overall_acc:.0f}% accuracy")
    await ctx.send(embed=embed)

@bot.command(
    name="trivialeaderboard",
    help=("Show the server trivia leaderboard.\n"
          "Usage: !trivialeaderboard [metric] [min_attempts] [count]\n"
          "metric = correct|accuracy|attempts (default: correct)")
)
async def trivialeaderboard(ctx, metric: str = "correct", min_attempts: int = 1, count: int = 10):
    metric = metric.lower().strip()
    if metric not in ("correct", "accuracy", "attempts"):
        metric = "correct"

    # clamp inputs
    try:
        min_attempts = max(0, int(min_attempts))
    except Exception:
        min_attempts = 1
    try:
        count = max(3, min(25, int(count)))
    except Exception:
        count = 10

    stats = load_trivia_stats()
    guild = ctx.guild

    # Build per-user totals for members in this guild (ignore bots)
    leaderboard = []
    for member in guild.members:
        if member.bot:
            continue
        uid = str(member.id)
        u = stats.get(uid)
        if not u:
            continue

        # Totals across all categories
        total_attempts = sum(int(rec.get("attempts", 0)) for rec in u.values())
        total_correct  = sum(int(rec.get("correct", 0))  for rec in u.values())
        if total_attempts < min_attempts or total_attempts == 0:
            continue

        acc = (total_correct / total_attempts) * 100.0
        leaderboard.append({
            "member": member,
            "attempts": total_attempts,
            "correct": total_correct,
            "accuracy": acc
        })

    if not leaderboard:
        return await ctx.send(
            f"📊 No qualifying players yet (min attempts: {min_attempts})."
        )

    # Sort according to metric (with sensible tiebreakers)
    if metric == "correct":
        leaderboard.sort(key=lambda r: (r["correct"], r["accuracy"], r["attempts"]), reverse=True)
        title = "🏆 Trivia Leaderboard — Most Correct"
    elif metric == "accuracy":
        # accuracy first, then attempts, then correct
        leaderboard.sort(key=lambda r: (r["accuracy"], r["attempts"], r["correct"]), reverse=True)
        title = "🎯 Trivia Leaderboard — Best Accuracy"
    else:  # attempts
        leaderboard.sort(key=lambda r: (r["attempts"], r["correct"], r["accuracy"]), reverse=True)
        title = "⏱️ Trivia Leaderboard — Most Attempts"

    # Format top N
    lines = []
    for i, row in enumerate(leaderboard[:count], start=1):
        m = row["member"]
        lines.append(
            f"**{i}.** {m.mention} — "
            f"✅ {row['correct']} · ❌ {row['attempts'] - row['correct']} · "
            f"{row['attempts']} attempts · {row['accuracy']:.0f}% acc"
        )

    embed = discord.Embed(
        title=title,
        description="\n".join(lines),
        color=discord.Color.teal()
    )
    embed.set_footer(text=f"Filter: min attempts ≥ {min_attempts} • Metric: {metric}")
    await ctx.send(embed=embed)

# =========================
# Economy helpers
# =========================
def ensure_user_coins(user_id):
    user_id = str(user_id)
    coins = load_coins()
    if user_id not in coins:
        coins[user_id] = {
            "wallet": 100,
            "bank": 0,
            "last_daily": 0,
            "last_rob": 0,
            "last_bankrob": 0,
            "portfolio": {s: 0 for s in STOCKS},
        }
        save_coins(coins)
    else:
        data = coins[user_id]
        data.setdefault("last_rob", 0)
        data.setdefault("last_bankrob", 0)
        data.setdefault("portfolio", {})
        for s in STOCKS:
            data["portfolio"].setdefault(s, 0)
        save_coins(coins)
    return coins

# =========================
# XP helpers
# =========================
def calculate_level(xp):
    return int(xp ** 0.5)

async def update_top_exp_role(guild):
    data = load_data()
    gid = str(guild.id)
    if gid not in data or not data[gid]:
        return
    top_user_id, _ = max(data[gid].items(), key=lambda x: x[1]["xp"])
    top_member = guild.get_member(int(top_user_id))
    if not top_member:
        return

    role = discord.utils.get(guild.roles, name=TOP_ROLE_NAME)
    if not role:
        try:
            role = await guild.create_role(name=TOP_ROLE_NAME)
        except discord.Forbidden:
            return

    for m in guild.members:
        if role in m.roles and m != top_member:
            await m.remove_roles(role)
    if role not in top_member.roles:
        await top_member.add_roles(role)

async def update_xp(user_id, guild_id, xp_amount):
    data = load_data()
    gid = str(guild_id)
    uid = str(user_id)
    data.setdefault(gid, {})
    user = data[gid].setdefault(uid, {"xp": 0})
    prev_xp = user["xp"]
    prev_level = user.get("level", calculate_level(prev_xp))

    event = load_event()
    mult = EVENTS.get(event.get("active", ""), {}).get("xp_mult", 1)
    user["xp"] = prev_xp + xp_amount * mult
    new_level = calculate_level(user["xp"])
    user["level"] = new_level
    save_data(data)

    if new_level > prev_level and new_level % 5 == 0:
        channel = bot.get_channel(1433417692320239666)
        if channel:
            u = await bot.fetch_user(user_id)
            await channel.send(f"🎉 **{u.mention}** just reached level **{new_level}**! 🚀")

    if new_level % 10 == 0:
        role_name = f"Level {new_level}"
        guild = bot.get_guild(int(gid))
        if guild:
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(name=role_name)
                except discord.Forbidden:
                    role = None
            member = guild.get_member(int(uid))
            if role and member:
                await member.add_roles(role)

    guild = bot.get_guild(int(gid))
    if guild:
        await update_top_exp_role(guild)

# =========================
# Commands (non-music)
# =========================
@bot.command(name="insult", help="Roast someone with a spicy insult 🔥")
async def insult(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("🥲 Self-roasting is a brave move, respect.")

    if member.bot:
        return await ctx.send("🤖 I'm not allowed to roast other bots... yet.")

    insults = [
        "I hope you know ur a fat fuck, biggie",
        "Any racial slur would be a complement to you",
        "I would rather drag my testicles over shattered glass than to talk to you any longer",
        "Even moses cant part that fucking unibrow, ugly fuck",
        "your Ital*an (from iggy)",
        "kys",
        "retard.",
        "retarded is a compliment to you",
        "I hope love never finds ur fugly ahh",
        "Fuckkk 🐺...",
        "flippin Malteser",
        "Fuck you, you ho. Come and say to my face, I'll fuck you in the ass in front of everybody. You bitch.",
        "Whoever's willing to fuck you is just too lazy to jerk off.",
        "God just be making anyone",
        "You should have been a blowjob"
    ]

    chosen = random.choice(insults)
    await ctx.send(f"{ctx.author.mention} roasts {member.mention}:\n> {chosen}")

@bot.command(name="threaten", help="Playfully threaten someone 😈 (fictional ofc)")
async def threaten(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("😅 Threatening yourself? Therapy might be cheaper.")

    if member.bot:
        return await ctx.send("🤖 I could never threaten my fellow bot comrades.")

    threats = [
        "I will pee your pants",
        "I will touch you",
        "*twirls your balls (testicular torsion way)* 🔌😈",
        "I will jiggle your tits",
        "I will send you to I*aly",
        "I will wet your socks (sexually)",
        "🇫🇷"
    ]

    chosen = random.choice(threats)
    await ctx.send(f"{ctx.author.mention} threatens {member.mention}:\n> {chosen}")

@bot.command(name="warn", help="Warn an individual for profanity")
async def warn(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("Putting yourself in timeout is not something you should be proud to say to the class")

    if member.bot:
        return await ctx.send("watch ur tone. twink")

    warnings = [
        "⚠️ Warning: That message has been escorted out by security.",
        "⚠️ Warning: Please keep your hands, feet, and words to yourself.",
        "⚠️ Warning: This is a no-weird-zone. Thank you for your cooperation.",
        "⚠️ Warning: Bonk. Go to respectful conversation jail.",
        "⚠️ Warning: That was a bit much. Let’s dial it back.",
        "⚠️ Warning: Socks will remain dry. Boundaries enforced.",
        "⚠️ Warning: International incidents are not permitted here."
    ]

    chosen = random.choice(warnings)
    await ctx.send(f"{ctx.author.mention} warns {member.mention}:\n> {chosen}")

@bot.command(name="compliment", help="Give someone a wholesome compliment 💖")
async def compliment(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("🥰 Self-love is important. You're doing amazing!")

    if member.bot:
        return await ctx.send("🤖 Even bots need a little appreciation sometimes!")

    compliments = [
        "You're not just smart — you're wise. There's a difference 💡",
        "You have a vibe that makes people feel safe and seen 💞",
        "You’re the kind of person who makes the internet a better place 📶✨",
        "You're basically a human golden retriever: loyal, loving, and always uplifting 🐶",
        "If good vibes were a currency, you'd be a millionaire 💸🌟",
        "You radiate the kind of energy people wish they had 🌈",
        "You could brighten up a Discord server with just a 'hi' ✨"
    ]

    chosen = random.choice(compliments)
    await ctx.send(f"{ctx.author.mention} compliments {member.mention}:\n> {chosen}")

@bot.command(
    name="leaderboard",
    help="Show top members by XP or coins. Usage: !leaderboard [xp|wallet|bank|networth] [count]"
)
async def leaderboard(ctx: commands.Context, metric: str = "xp", count: int = 10):
    guild = ctx.guild

    # Allow "!leaderboard 15" (number first) and clamp count
    if metric.isdigit():
        count, metric = int(metric), "xp"
    try:
        count = int(count)
    except Exception:
        count = 10
    count = max(3, min(25, count))
    metric = metric.lower()

    # ===== XP Leaderboard =====
    if metric in ("xp", "level"):
        data = load_data()
        gid = str(guild.id)
        entries = []
        for uid, info in (data.get(gid) or {}).items():
            member = guild.get_member(int(uid))
            if not member or member.bot:
                continue
            xp = int(info.get("xp", 0))
            lvl = int(info.get("level", calculate_level(xp)))
            entries.append((member, xp, lvl))

        if not entries:
            return await ctx.send("No XP data yet.")

        entries.sort(key=lambda t: t[1], reverse=True)
        lines = []
        for i, (m, xp, lvl) in enumerate(entries[:count], start=1):
            crown = " 👑" if i == 1 else ""
            you = " ← you" if m.id == ctx.author.id else ""
            lines.append(f"**{i}.** {m.mention}{crown} — Lvl **{lvl}** · {xp} XP{you}")

        your_rank = next((i for i, (m, *_rest) in enumerate(entries, start=1) if m.id == ctx.author.id), None)
        embed = discord.Embed(title="🏆 XP Leaderboard", description="\n".join(lines), color=discord.Color.gold())
        if your_rank:
            embed.set_footer(text=f"Your rank: {your_rank}/{len(entries)}")
        return await ctx.send(embed=embed)

    # ===== Coins Leaderboard =====
    if metric in ("wallet", "bank", "networth", "coins", "money"):
        coins = load_coins()
        stocks = load_stocks() if metric == "networth" else None

        def value_for(user_id: int) -> int:
            d = coins.get(str(user_id), {})
            wallet = int(d.get("wallet", 0))
            bank = int(d.get("bank", 0))
            if metric == "wallet":
                return wallet
            if metric == "bank":
                return bank
            # net worth (wallet + bank + portfolio)
            total = wallet + bank
            if stocks:
                pf = d.get("portfolio", {}) or {}
                for s, qty in pf.items():
                    try:
                        total += int(qty) * int(stocks[s]["price"])
                    except Exception:
                        pass
            return total

        members = [m for m in guild.members if not m.bot]
        entries = [(m, value_for(m.id)) for m in members]
        entries = [e for e in entries if e[1] > 0]
        if not entries:
            return await ctx.send("No coin data yet.")

        entries.sort(key=lambda t: t[1], reverse=True)
        lines = []
        for i, (m, val) in enumerate(entries[:count], start=1):
            you = " ← you" if m.id == ctx.author.id else ""
            lines.append(f"**{i}.** {m.mention} — {val} coins{you}")

        label = {"wallet": "Wallet", "bank": "Bank", "networth": "Net Worth"}.get(metric, "Coins")
        your_rank = next((i for i, (m, _val) in enumerate(entries, start=1) if m.id == ctx.author.id), None)
        embed = discord.Embed(title=f"💰 {label} Leaderboard", description="\n".join(lines), color=discord.Color.green())
        if your_rank:
            embed.set_footer(text=f"Your rank: {your_rank}/{len(entries)}")
        return await ctx.send(embed=embed)

    # Bad metric
    return await ctx.send("Usage: `!leaderboard [xp|wallet|bank|networth] [count]`")

# =========================
# Suggestions
# =========================
def load_suggestions():
    return _load_json(SUGGESTION_FILE, [])

def save_suggestions(d):
    _save_json(SUGGESTION_FILE, d)

@bot.command(name="suggest", help="Submit a suggestion to the server.")
async def suggest(ctx, *, message: str):
    suggestions = load_suggestions()
    suggestions.append({
        "user_id": ctx.author.id,
        "username": ctx.author.name,
        "suggestion": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    save_suggestions(suggestions)

    channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
    if not channel:
        return await ctx.send("❌ Suggestion channel not found. Please contact an admin.")

    embed = discord.Embed(title="📬 New Suggestion", description=message, color=discord.Color.teal())
    embed.set_footer(text=f"Suggested by {ctx.author.display_name}")
    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await ctx.send("✅ Your suggestion has been submitted!")

# =========================
# Economy: wallet/bank/daily/beg/donate/pay
# =========================
@bot.command(name="balance", help="Check your or someone else's wallet and bank balance.")
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    coins = ensure_user_coins(member.id)
    data = coins[str(member.id)]
    embed = discord.Embed(title=f"💰 {member.display_name}'s Balance", color=discord.Color.purple())
    embed.add_field(name="Wallet", value=f"💵 {data['wallet']} coins")
    embed.add_field(name="Bank", value=f"🏦 {data['bank']} coins")
    await ctx.send(embed=embed)

@bot.command(name="deposit", help="Deposit to bank. Usage: !deposit <amount> or !deposit all")
async def deposit(ctx, amount: str):
    uid = str(ctx.author.id)
    coins = ensure_user_coins(uid)
    data = coins[uid]
    if amount.lower() == "all":
        amt = data["wallet"]
    else:
        if not amount.isdigit():
            return await ctx.send(embed=discord.Embed(description="❌ Enter a number or 'all'.", color=discord.Color.orange()))
        amt = int(amount)
    if amt <= 0 or amt > data["wallet"]:
        return await ctx.send(embed=discord.Embed(description="❌ Not enough wallet balance.", color=discord.Color.orange()))
    data["wallet"] -= amt
    data["bank"] += amt
    save_coins(coins)
    await ctx.send(embed=discord.Embed(description=f"🏦 Deposited **{amt}** coins.", color=discord.Color.orange()))

@bot.command(name="withdraw", help="Withdraw from bank. Usage: !withdraw <amount> or !withdraw all")
async def withdraw(ctx, amount: str):
    uid = str(ctx.author.id)
    coins = ensure_user_coins(uid)
    data = coins[uid]
    if amount.lower() == "all":
        amt = data["bank"]
    else:
        if not amount.isdigit():
            return await ctx.send(embed=discord.Embed(description="❌ Enter a number or 'all'.", color=discord.Color.orange()))
        amt = int(amount)
    if amt <= 0 or amt > data["bank"]:
        return await ctx.send(embed=discord.Embed(description="❌ Not enough bank balance.", color=discord.Color.orange()))
    data["bank"] -= amt
    data["wallet"] += amt
    save_coins(coins)
    await ctx.send(embed=discord.Embed(description=f"💰 Withdrew **{amt}** coins.", color=discord.Color.orange()))

@bot.command(name="daily", help="Claim your daily reward.")
async def daily(ctx):
    uid = str(ctx.author.id)
    coins = ensure_user_coins(uid)
    data = coins[uid]

    now = datetime.now(timezone.utc)
    last_ts = data.get("last_daily", 0)
    last_claim = datetime.fromtimestamp(last_ts, tz=timezone.utc)

    if last_claim.date() == now.date():
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = (tomorrow - now).total_seconds()
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        return await ctx.send(embed=discord.Embed(
            description=f"🕒 Already claimed. Try again in **{h}h {m}m {s}s** (resets at midnight UTC).",
            color=discord.Color.purple()
        ))

    reward = random.randint(200, 350)
    event = load_event()
    if event.get("active") == "Coin Rain":
        reward += EVENTS["Coin Rain"]["bonus_daily"]
    data["wallet"] += reward
    data["last_daily"] = now.timestamp()
    save_coins(coins)

    await ctx.send(embed=discord.Embed(description=f"💰 Daily claimed: **{reward}** coins!", color=discord.Color.purple()))

@bot.command(name="beg", help="Beg for coins (scales with begging experience, has cooldown).")
async def beg(ctx):
    uid = str(ctx.author.id)

    coins = ensure_user_coins(uid)
    data = coins[uid]

    # ---- Cooldown (30 seconds) ----
    now = time.time()
    cooldown = 30
    last_beg = data.get("last_beg", 0)

    if now - last_beg < cooldown:
        remaining = int(cooldown - (now - last_beg))
        return await ctx.send(f"⏳ You must wait **{remaining}s** before begging again.")

    # ---- Load begging XP ----
    beg_stats = load_beg_stats()
    user_beg = beg_stats.setdefault(uid, {"xp": 0, "level": 1, "total_begs": 0})

    # ---- Calculate level ----
    user_beg["level"] = int((user_beg["xp"] ** 0.5) // 5 + 1)

    # ---- Reward scales with level ----
    base_min = 10 + user_beg["level"] * 2
    base_max = 30 + user_beg["level"] * 5
    amount = random.randint(base_min, base_max)

    responses = [
        "A kind stranger gave you",
        "Your sob story worked. You received",
        "You found coins on the floor:",
        "Someone felt bad and handed you",
        "A rich NPC tipped you",
    ]

    msg = random.choice(responses)

    # ---- Apply reward ----
    data["wallet"] += amount
    data["last_beg"] = now

    # ---- Gain begging XP ----
    xp_gain = random.randint(5, 12)
    user_beg["xp"] += xp_gain
    user_beg["total_begs"] += 1

    save_coins(coins)
    save_beg_stats(beg_stats)

    embed = discord.Embed(
        title="🙏 Successful Beg",
        description=(
            f"{msg} **{amount}** coins!\n\n"
            f"📈 Beg Level: **{user_beg['level']}** | Total Begs: **{user_beg['total_begs']}**\n"
            f"✨ XP Gained: **+{xp_gain}**"
        ),
        color=discord.Color.orange(),
    )

    await ctx.send(embed=embed)

@bot.command(name="begleaderboard", help="Show top beggars in the server.")
async def begleaderboard(ctx, count: int = 10):
    count = max(3, min(25, count))

    beg_stats = load_beg_stats()
    guild = ctx.guild

    entries = []

    for member in guild.members:
        if member.bot:
            continue

        stats = beg_stats.get(str(member.id))
        if not stats:
            continue

        level = int(stats.get("level", 1))
        xp = int(stats.get("xp", 0))
        begs = int(stats.get("total_begs", 0))

        entries.append((member, level, xp, begs))

    if not entries:
        return await ctx.send("📭 No begging data yet.")

    # Sort by level → xp → total begs
    entries.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

    lines = []
    for i, (member, level, xp, begs) in enumerate(entries[:count], start=1):
        crown = " 👑" if i == 1 else ""
        you = " ← you" if member.id == ctx.author.id else ""

        lines.append(
            f"**{i}.** {member.mention}{crown} — "
            f"Lvl **{level}** · {xp} XP · {begs} begs{you}"
        )

    embed = discord.Embed(
        title="🏆 Begging Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )

    await ctx.send(embed=embed)

@bot.command(name="donate", help="Donate coins to someone.")
async def donate(ctx, member: discord.Member, amount: int):
    if member == ctx.author:
        return await ctx.send(embed=discord.Embed(description="❌ You can't donate to yourself.", color=discord.Color.orange()))
    if member.bot:
        return await ctx.send(embed=discord.Embed(description="🤖 Bots don't need donations.", color=discord.Color.orange()))
    if amount <= 0:
        return await ctx.send(embed=discord.Embed(description="❌ Amount must be > 0.", color=discord.Color.orange()))

    coins = ensure_user_coins(ctx.author.id)
    ensure_user_coins(member.id)
    donor = coins[str(ctx.author.id)]
    recipient = coins[str(member.id)]

    if donor["wallet"] < amount:
        return await ctx.send(embed=discord.Embed(description="💸 Not enough wallet balance.", color=discord.Color.orange()))

    donor["wallet"] -= amount
    recipient["wallet"] += amount
    save_coins(coins)
    await ctx.send(embed=discord.Embed(description=f"💖 {ctx.author.mention} donated **{amount}** to {member.mention}!", color=discord.Color.orange()))

@bot.command(name="pay", help="Send coins to another user.")
async def pay(ctx, member: discord.Member, amount: int):
    if member == ctx.author:
        return await ctx.send("❌ You can't pay yourself.")
    if member.bot:
        return await ctx.send("🤖 You can't pay bots.")
    if amount <= 0:
        return await ctx.send("❌ Enter a valid amount greater than 0.")

    coins = ensure_user_coins(ctx.author.id)
    ensure_user_coins(member.id)
    sender = coins[str(ctx.author.id)]
    recipient = coins[str(member.id)]

    if sender["wallet"] < amount:
        return await ctx.send("💸 You don't have enough coins in your wallet to send that much.")

    sender["wallet"] -= amount
    recipient["wallet"] += amount
    save_coins(coins)
    await ctx.send(embed=discord.Embed(description=f"✅ You sent **{amount}** coins to {member.mention}!", color=discord.Color.green()))

# =========================
# Robbery / Gambling / Blackjack
# =========================
@bot.command(name="rob", help="Attempt to rob someone. Usage: !rob @user")
async def rob(ctx, member: discord.Member = None):
    # Enforce mention-only to avoid ambiguous name resolution
    target_id = only_mention_target(ctx)
    if target_id is None:
        return await ctx.send("❌ Please mention exactly one user: `!rob @user`")
    if target_id == ctx.author.id:
        return await ctx.send(embed=discord.Embed(description="❌ You can't rob yourself.", color=discord.Color.purple()))

    # Fetch member safely (handles cache miss)
    target_member = ctx.guild.get_member(target_id) or await _get_member_safe(ctx.guild, target_id)
    if not target_member:
        return await ctx.send("❌ Could not find that member in this server.")
    if target_member.bot:
        return await ctx.send(embed=discord.Embed(description="🤖 You can't rob bots.", color=discord.Color.purple()))

    # Per-user locks to avoid race conditions touching the same wallets
    async with MONEY_LOCKS[min(ctx.author.id, target_id)], MONEY_LOCKS[max(ctx.author.id, target_id)]:
        # Ensure both users exist, then re-load the file so we work on the freshest dict
        ensure_user_coins(ctx.author.id)
        ensure_user_coins(target_id)
        coins = load_coins()

        thief  = coins[str(ctx.author.id)]
        victim = coins[str(target_id)]

        now = time.time()
        cooldown = 300
        if now - thief.get("last_rob", 0) < cooldown:
            remaining = int(cooldown - (now - thief["last_rob"]))
            return await ctx.send(embed=discord.Embed(description=f"⏳ Cooldown: **{remaining}**s", color=discord.Color.purple()))

        if victim.get("wallet", 0) < 50:
            return await ctx.send(embed=discord.Embed(description="😒 That user doesn't have enough to rob.", color=discord.Color.purple()))

        stolen = random.randint(10, max(10, victim["wallet"] // 2))
        victim["wallet"] -= stolen
        thief["wallet"]  += stolen
        thief["last_rob"] = now

        save_coins(coins)
        await ctx.send(embed=discord.Embed(
            description=f"💸 You robbed **{target_member.display_name}** and got **{stolen}** coins!",
            color=discord.Color.purple()
        ))

@bot.command(
    name="bankrob",
    help="Rob a specific person's bank (risky!). Usage: !bankrob @user"
)
async def bankrob(ctx, member: discord.Member = None):
    # Require exactly one mentioned member if param missing/ambiguous
    if member is None:
        tgt_id = only_mention_target(ctx)
        if tgt_id is None:
            return await ctx.send("❌ Usage: `!bankrob @user` (mention exactly one person)")
        member = ctx.guild.get_member(tgt_id) or await _get_member_safe(ctx.guild, tgt_id)
        if not member:
            return await ctx.send("❌ Couldn’t find that member.")

    if member.bot:
        return await ctx.send(embed=discord.Embed(description="🤖 You can’t rob bots.", color=discord.Color.purple()))
    if member.id == ctx.author.id:
        return await ctx.send(embed=discord.Embed(description="❌ You can’t rob yourself.", color=discord.Color.purple()))

    robber_id = str(ctx.author.id)
    victim_id = str(member.id)

    # Ensure ledgers exist
    ensure_user_coins(robber_id)
    ensure_user_coins(victim_id)

    # Per-user locks (sorted to avoid deadlocks)
    first, second = sorted([int(robber_id), int(victim_id)])
    async with MONEY_LOCKS[first], MONEY_LOCKS[second]:
        coins = load_coins()
        robber = coins[robber_id]
        victim = coins[victim_id]

        # Cooldown (10 minutes)
        now = time.time()
        cooldown = 600
        if now - robber.get("last_bankrob", 0) < cooldown:
            remaining = int(cooldown - (now - robber["last_bankrob"]))
            return await ctx.send(embed=discord.Embed(
                description=f"🚨 Try again in **{remaining//60}m {remaining%60}s**.",
                color=discord.Color.purple()
            ))
        robber["last_bankrob"] = now

        # Victim must have some bank to rob
        victim_bank = int(victim.get("bank", 0))
        if victim_bank < 100:
            return await ctx.send(embed=discord.Embed(
                description=f"😓 {member.display_name} doesn’t have enough in the bank to rob.",
                color=discord.Color.purple()
            ))

        # Success rule: special ID always succeeds; others 20% success
        if ctx.author.id == ALWAYS_BANKROB_USER_ID:
            success = True
        else:
            success = random.choices([True, False], weights=[20, 80])[0]

        if success:
            # --- Proportionate steal amount ---
            # Draw a percentage in [MIN_PCT, MAX_PCT], cap the steal at MAX_STEAL_PCT_CAP of victim_bank,
            # and enforce an absolute floor.
            pct = random.uniform(BANKROB_STEAL_MIN_PCT, BANKROB_STEAL_MAX_PCT)
            raw_amount = int(victim_bank * pct)
            hard_cap  = int(victim_bank * BANKROB_MAX_STEAL_PCT_CAP)

            amount = max(
                BANKROB_MIN_STEAL,
                min(raw_amount, hard_cap, victim_bank)  # never exceed the actual bank balance
            )

            # If rounding or caps push us to 0, bail out gracefully
            if amount <= 0:
                return await ctx.send(embed=discord.Embed(
                    description=f"😓 {member.display_name} doesn’t have enough in the bank to rob.",
                    color=discord.Color.purple()
                ))

            victim["bank"] -= amount
            robber["wallet"] += amount
            save_coins(coins)

            pct_display = (amount / max(1, victim_bank + amount)) * 100  # show % of pre-theft bank
            return await ctx.send(embed=discord.Embed(
                description=(
                    f"🏦 Success! You stole **{amount}** coins from **{member.display_name}** "
                    f"(~{pct_display:.0f}% of their bank)."
                ),
                color=discord.Color.purple()
            ))
        else:
            # Failure penalties (unchanged)
            if robber["wallet"] < 50:
                msg = "🚔 Caught, but too broke to fine. Warning issued."
            else:
                fine = random.randint(50, int(min(robber["wallet"], 150)))
                robber["wallet"] -= fine
                msg = f"🚔 You got caught and lost **{fine}** coins in legal fees."
            save_coins(coins)
            return await ctx.send(embed=discord.Embed(description=msg, color=discord.Color.purple()))

# Active solo blackjack games keyed by user_id
SOLO_BLACKJACK_GAMES: dict[str, dict] = {}

_CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
_CARD_SUITS = ["♠", "♥", "♦", "♣"]

def draw_card() -> str:
    return f"{random.choice(_CARD_RANKS)}{random.choice(_CARD_SUITS)}"

def _card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11  # adjust in calculate_score
    return int(rank)

def calculate_score(hand: list[str]) -> int:
    ranks = []
    for c in hand:
        ranks.append("10" if c.startswith("10") else c[0])
    total = sum(_card_value(r) for r in ranks)
    aces = ranks.count("A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def _hand_as_text(cards: list[str]) -> str:
    return ", ".join(cards)

@bot.command(name="blackjack", help="Play a solo game of blackjack. Usage: !blackjack <bet>")
async def solo_blackjack(ctx: commands.Context, bet: int):
    user_id = str(ctx.author.id)

    if user_id in SOLO_BLACKJACK_GAMES:
        return await ctx.send(
            "❌ You already have a solo Blackjack game in progress! Use `!hit` or `!stand`."
        )

    coins = ensure_user_coins(user_id)
    user_data = coins[user_id]

    if bet <= 0:
        return await ctx.send("❌ Your bet must be more than zero.")
    if user_data["wallet"] < bet:
        return await ctx.send("💸 You don’t have enough coins to bet that much.")

    user_data["wallet"] -= bet
    save_coins(coins)

    player_hand = [draw_card(), draw_card()]
    dealer_hand = [draw_card(), draw_card()]
    player_score = calculate_score(player_hand)
    dealer_up = dealer_hand[0]

    SOLO_BLACKJACK_GAMES[user_id] = {
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "bet": bet,
    }

    if player_score == 21:
        dealer_score = calculate_score(dealer_hand)
        while dealer_score < 17:
            dealer_hand.append(draw_card())
            dealer_score = calculate_score(dealer_hand)

        game = SOLO_BLACKJACK_GAMES.pop(user_id)
        coins = ensure_user_coins(user_id)
        user_data = coins[user_id]

        if dealer_score != 21:
            user_data["wallet"] += bet * 2
            save_coins(coins)
            embed = discord.Embed(
                title="🃏 Blackjack!",
                description=(
                    f"**Your hand:** {_hand_as_text(player_hand)} (Total: **21**)\n"
                    f"**Dealer hand:** {_hand_as_text(dealer_hand)} (Total: **{dealer_score}**)\n\n"
                    f"🎉 Natural blackjack! You earned **{bet*2}** coins."
                ),
                color=discord.Color.green(),
            )
        else:
            user_data["wallet"] += bet
            save_coins(coins)
            embed = discord.Embed(
                title="🤝 Push (Both Blackjack)",
                description=(
                    f"**Your hand:** {_hand_as_text(player_hand)} (Total: **21**)\n"
                    f"**Dealer hand:** {_hand_as_text(dealer_hand)} (Total: **21**)\n\n"
                    f"Your **{bet}** coins were returned."
                ),
                color=discord.Color.gold(),
            )
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🃏 Solo Blackjack",
        description=(
            f"**Your hand:** {_hand_as_text(player_hand)} (Total: **{player_score}**)\n"
            f"**Dealer shows:** {dealer_up}\n\n"
            "Type `!hit` to draw a card or `!stand` to hold."
        ),
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed)

@bot.command(name="hit", help="Draw a card in your solo Blackjack game.")
async def solo_hit(ctx: commands.Context):
    user_id = str(ctx.author.id)

    if user_id not in SOLO_BLACKJACK_GAMES:
        return await ctx.send(
            "❌ You don’t have a solo Blackjack game in progress. Use `!blackjack <bet>` to start."
        )

    game = SOLO_BLACKJACK_GAMES[user_id]
    game["player_hand"].append(draw_card())
    score = calculate_score(game["player_hand"])

    if score > 21:
        bet = game["bet"]
        final = _hand_as_text(game["player_hand"])
        del SOLO_BLACKJACK_GAMES[user_id]

        embed = discord.Embed(
            title="💥 Busted!",
            description=f"You drew: {final} (Total: **{score}**)\nYou lost **{bet}** coins.",
            color=discord.Color.red(),
        )
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🃏 You drew a card",
        description=(
            f"Your hand: {_hand_as_text(game['player_hand'])} (Total: **{score}**)\n"
            "Type `!hit` or `!stand`."
        ),
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed)

@bot.command(name="stand", help="Stand and let the dealer play in solo Blackjack.")
async def solo_stand(ctx: commands.Context):
    user_id = str(ctx.author.id)

    if user_id not in SOLO_BLACKJACK_GAMES:
        return await ctx.send("❌ You don’t have a solo Blackjack game in progress.")

    game = SOLO_BLACKJACK_GAMES.pop(user_id)
    player_hand = game["player_hand"]
    dealer_hand = game["dealer_hand"]
    bet = game["bet"]

    player_score = calculate_score(player_hand)
    dealer_score = calculate_score(dealer_hand)

    while dealer_score < 17:
        dealer_hand.append(draw_card())
        dealer_score = calculate_score(dealer_hand)

    coins = ensure_user_coins(user_id)
    user_data = coins[user_id]

    if dealer_score > 21 or player_score > dealer_score:
        winnings = bet * 2
        user_data["wallet"] += winnings
        result_msg = f"🎉 You win! Dealer had {dealer_score}. You earned **{winnings}** coins!"
        color = discord.Color.green()
    elif dealer_score == player_score:
        user_data["wallet"] += bet
        result_msg = f"🤝 It’s a tie! Dealer had {dealer_score}. Your **{bet}** coins were returned."
        color = discord.Color.gold()
    else:
        result_msg = f"😢 You lost. Dealer had {dealer_score}. Better luck next time!"
        color = discord.Color.red()

    save_coins(coins)

    embed = discord.Embed(
        title="🏁 Final Result",
        description=(
            f"**Your hand:** {_hand_as_text(player_hand)} (Total: **{player_score}**)\n"
            f"**Dealer hand:** {_hand_as_text(dealer_hand)} (Total: **{dealer_score}**)\n\n"
            f"{result_msg}"
        ),
        color=color,
    )
    await ctx.send(embed=embed)

@bot.command(name="gamble", help="Gamble coins on red or black 🎰 (use `!gamble <amount>` or `!gamble all`)")
async def gamble(ctx, amount: str):
    coins = ensure_user_coins(ctx.author.id)
    user = coins[str(ctx.author.id)]

    # ----- Parse amount -----
    if amount.lower() == "all":
        bet = user["wallet"]
        if bet <= 0:
            return await ctx.send("💸 You don’t have any coins to gamble.")
    else:
        if not amount.isdigit():
            return await ctx.send("❌ Invalid amount. Use a number or `all`.")
        bet = int(amount)
        if bet <= 0:
            return await ctx.send("❌ Invalid amount to gamble.")
        if user["wallet"] < bet:
            return await ctx.send("💸 You don’t have enough coins in your wallet to gamble that much.")

    # ----- Spin -----
    result = random.choice(["red", "black"])

    embed = discord.Embed(
        title="🎰 Place Your Bet!",
        description=(
            f"Bet: **{bet}** coins\n\n"
            "React with 🟥 for **Red** or ⬛ for **Black**.\n"
            "You have **5 seconds**..."
        ),
        color=discord.Color.gold()
    )
    message = await ctx.send(embed=embed)
    await message.add_reaction("🟥")
    await message.add_reaction("⬛")

    def check(reaction, u):
        return (
            u == ctx.author and
            str(reaction.emoji) in ["🟥", "⬛"] and
            reaction.message.id == message.id
        )

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=5.0, check=check)
    except asyncio.TimeoutError:
        return await ctx.send("⏰ You didn’t react in time. Bet cancelled.")

    choice = "red" if str(reaction.emoji) == "🟥" else "black"
    win = choice == result

    # ----- Resolve bet -----
    user["wallet"] -= bet

    if win:
        winnings = bet * 2
        user["wallet"] += winnings
        resp = discord.Embed(
            title="🎉 You Win!",
            description=(
                f"The wheel landed on **{result.upper()}**!\n"
                f"You won **{winnings}** coins 🎉"
            ),
            color=discord.Color.green()
        )
    else:
        resp = discord.Embed(
            title="😢 You Lose!",
            description=(
                f"The wheel landed on **{result.upper()}**.\n"
                f"You lost **{bet}** coins 💀"
            ),
            color=discord.Color.red()
        )

    save_coins(coins)
    await ctx.send(embed=resp)

# =========================
# Shop / Inventory
# =========================
@bot.command(name="shop", help="Browse items currently in stock.")
async def shop(ctx):
    stock = load_shop_stock()
    embed = discord.Embed(title="🛒 QMUL Shop", color=discord.Color.purple())
    for item in SHOP_ITEMS:
        price = ITEM_PRICES[item]
        count = stock.get(item, 0)
        embed.add_field(name=item, value=f"💰 {price} coins\n📦 Stock: {count}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="inventory", help="View your or someone else's inventory.")
async def inventory(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)
    inv = load_inventory()
    user_inv = inv.get(uid, {})
    if not user_inv:
        return await ctx.send(embed=discord.Embed(description=f"{member.display_name} has nothing in their inventory 🪫", color=discord.Color.orange()))
    embed = discord.Embed(title=f"🎒 {member.display_name}'s Inventory", color=discord.Color.orange())
    for item, qty in user_inv.items():
        embed.add_field(name=item, value=f"🧮 Quantity: {qty}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="buy", help="Buy a stock or shop item. Stocks: !buy <stock> <amount>|all; Items: !buy <item> [all].")
async def buy(ctx, *, raw: str):
    uid = str(ctx.author.id)
    raw = " ".join(raw.strip().split())  # normalize spaces

    # Case-insensitive lookup maps
    stock_names = {s.lower(): s for s in STOCKS}
    shop_names  = {item.lower(): item for item in SHOP_ITEMS}

    parts = raw.split()

    # ---------- STOCKS ----------
    # Accept: "!buy qmkoin 3" OR "!buy qmkoin all" OR "!buy all qmkoin"
    if len(parts) >= 2:
        last = parts[-1].lower()
        first = parts[0].lower()

        # Case A: amount is a number at the end
        if last.isdigit():
            amount = int(last)
            symbol = " ".join(parts[:-1]).lower()
            if symbol in stock_names:
                if amount <= 0:
                    return await ctx.send("❌ Amount must be a positive integer.")
                stocks = load_stocks()
                coins  = ensure_user_coins(uid)
                user   = coins[uid]
                s = stock_names[symbol]
                try:
                    price = int(stocks[s]["price"])
                except Exception:
                    return await ctx.send("⚠️ Couldn't get stock price. Try again later.")
                cost = price * amount
                if user["wallet"] < cost:
                    return await ctx.send(f"💸 You need {cost} coins to buy {amount} shares of {s}.")
                user["wallet"] -= cost
                user["portfolio"][s] = user["portfolio"].get(s, 0) + amount
                STOCK_PURCHASE_COUNT[s] = STOCK_PURCHASE_COUNT.get(s, 0) + amount
                save_coins(coins)
                return await ctx.send(f"✅ You bought {amount} shares of **{s}** at {price} coins each!")

        # Case B: "all" at the end -> buy max shares
        if last == "all":
            symbol = " ".join(parts[:-1]).lower()
            if symbol in stock_names:
                stocks = load_stocks()
                coins  = ensure_user_coins(uid)
                user   = coins[uid]
                s = stock_names[symbol]
                try:
                    price = int(stocks[s]["price"])
                except Exception:
                    return await ctx.send("⚠️ Couldn't get stock price. Try again later.")
                if price <= 0:
                    return await ctx.send("⚠️ Invalid price.")
                amount = user["wallet"] // price
                if amount <= 0:
                    return await ctx.send("💸 You can't afford any shares right now.")
                cost = price * amount
                user["wallet"] -= cost
                user["portfolio"][s] = user["portfolio"].get(s, 0) + amount
                STOCK_PURCHASE_COUNT[s] = STOCK_PURCHASE_COUNT.get(s, 0) + amount
                save_coins(coins)
                return await ctx.send(f"✅ Bought **{amount}** shares of **{s}** (spent {cost} coins).")

        # Case C: "all" first -> "!buy all qmkoin"
        if first == "all":
            symbol = " ".join(parts[1:]).lower()
            if symbol in stock_names:
                stocks = load_stocks()
                coins  = ensure_user_coins(uid)
                user   = coins[uid]
                s = stock_names[symbol]
                try:
                    price = int(stocks[s]["price"])
                except Exception:
                    return await ctx.send("⚠️ Couldn't get stock price. Try again later.")
                if price <= 0:
                    return await ctx.send("⚠️ Invalid price.")
                amount = user["wallet"] // price
                if amount <= 0:
                    return await ctx.send("💸 You can't afford any shares right now.")
                cost = price * amount
                user["wallet"] -= cost
                user["portfolio"][s] = user["portfolio"].get(s, 0) + amount
                STOCK_PURCHASE_COUNT[s] = STOCK_PURCHASE_COUNT.get(s, 0) + amount
                save_coins(coins)
                return await ctx.send(f"✅ Bought **{amount}** shares of **{s}** (spent {cost} coins).")

    # ---------- SHOP ITEMS ----------
    # Accept exact item name (case-insensitive), optionally with "all" at start/end
    # e.g. "!buy anime body pillow", "!buy anime body pillow all", "!buy all anime body pillow"
    key = raw.lower()

    # Handle "<item> all"
    if key.endswith(" all"):
        key = key[:-4].strip()
        buy_all_items = True
    # Handle "all <item>"
    elif key.startswith("all "):
        key = key[4:].strip()
        buy_all_items = True
    else:
        buy_all_items = False

    # Flexible whitespace match
    key_compact = " ".join(key.split())
    match = next((k for k in shop_names if " ".join(k.split()) == key_compact), None)
    if match is None:
        return await ctx.send("❌ Invalid item or stock format.\nUse `!buy <stock> <amount|all>` or `!buy <shop item> [all]`.")

    item_name = shop_names[match]
    stock = load_shop_stock()
    coins = ensure_user_coins(uid)
    user  = coins[uid]

    price = ITEM_PRICES[item_name]
    available = int(stock.get(item_name, 0))
    if available <= 0:
        return await ctx.send(f"❌ {item_name} is out of stock.")

    if buy_all_items:
        affordable = user["wallet"] // price
        qty = min(available, affordable)
        if qty <= 0:
            return await ctx.send("💸 You can’t afford any right now.")
    else:
        # default single item buy
        qty = 1
        if user["wallet"] < price:
            return await ctx.send("💸 You don’t have enough coins to buy this item.")

    # Apply purchase
    cost = price * qty
    user["wallet"] -= cost
    stock[item_name] = available - qty
    save_shop_stock(stock)
    save_coins(coins)

    inv = load_inventory()
    inv.setdefault(uid, {})
    inv[uid][item_name] = inv[uid].get(item_name, 0) + qty
    save_inventory(inv)

    if qty == 1:
        await ctx.send(f"✅ You bought **{item_name}** for **{price}** coins!")
    else:
        await ctx.send(f"✅ You bought **{qty}× {item_name}** for **{cost}** coins (each {price}).")

@bot.command(name="claim", help="Use a Crash token to halve the value of a stock. Usage: !claim <stock>")
async def claim(ctx, stock_name: str):
    uid = str(ctx.author.id)
    stock_names = {s.lower(): s for s in STOCKS}
    key = stock_name.lower()
    if key not in stock_names:
        return await ctx.send(embed=discord.Embed(description="❌ Invalid stock name.", color=discord.Color.orange()))
    inv = load_inventory()
    qty = inv.get(uid, {}).get(CRASH_TOKEN_NAME, 0)
    if qty < 1:
        return await ctx.send(embed=discord.Embed(description=f"❌ You don’t have any **{CRASH_TOKEN_NAME}** to use.", color=discord.Color.orange()))
    stocks = load_stocks()
    s = stock_names[key]
    old = int(stocks[s]["price"])
    new = max(1, old // 2)
    stocks[s]["price"] = new
    stocks[s]["history"].append(new)
    if len(stocks[s]["history"]) > 24:
        stocks[s]["history"] = stocks[s]["history"][-24:]
    save_stocks(stocks)
    inv[uid][CRASH_TOKEN_NAME] -= 1
    if inv[uid][CRASH_TOKEN_NAME] <= 0:
        del inv[uid][CRASH_TOKEN_NAME]
    save_inventory(inv)
    await ctx.send(embed=discord.Embed(
        title="💥 Crash Token Used!",
        description=f"{ctx.author.mention} halved **{s}** from **{old}** → **{new}** coins!",
        color=discord.Color.orange()
    ))

@bot.command(name="sell", help="Sell shares of a stock. Usage: !sell <stock> <amount|all> (also: !sell all <stock>)")
async def sell(ctx, *, raw: str):
    uid = str(ctx.author.id)
    raw = " ".join(raw.strip().split())  # normalize spaces

    stock_names = {s.lower(): s for s in STOCKS}
    parts = raw.split()

    if not parts:
        return await ctx.send("❌ Usage: `!sell <stock> <amount|all>`")

    # Accept:
    # - "!sell qmkoin 3"
    # - "!sell qmkoin all"
    # - "!sell all qmkoin"
    amount = None
    symbol = None

    # Case A: ends with number
    if len(parts) >= 2 and parts[-1].isdigit():
        amount = int(parts[-1])
        symbol = " ".join(parts[:-1]).lower()

    # Case B: ends with "all"
    elif len(parts) >= 2 and parts[-1].lower() == "all":
        amount = "all"
        symbol = " ".join(parts[:-1]).lower()

    # Case C: starts with "all"
    elif parts[0].lower() == "all" and len(parts) >= 2:
        amount = "all"
        symbol = " ".join(parts[1:]).lower()

    # Otherwise treat whole string as symbol and assume 1 (for back-compat error message)
    else:
        symbol = " ".join(parts).lower()

    if symbol not in stock_names:
        return await ctx.send("❌ Invalid stock.\nUsage: `!sell <stock> <amount|all>`")

    s = stock_names[symbol]

    coins = ensure_user_coins(uid)
    user  = coins[uid]
    portfolio = user.get("portfolio", {})
    owned = int(portfolio.get(s, 0))

    if owned <= 0:
        return await ctx.send(f"❌ You don't own any **{s}** shares.")

    stocks = load_stocks()
    try:
        price = int(stocks[s]["price"])
    except Exception:
        return await ctx.send("⚠️ Couldn't get stock price. Try again later.")

    if amount == "all":
        sell_qty = owned
    else:
        # amount could be None or invalid -> show usage
        if not isinstance(amount, int) or amount <= 0:
            return await ctx.send("❌ Invalid amount.\nUsage: `!sell <stock> <amount|all>`")
        if amount > owned:
            return await ctx.send(f"❌ You only own {owned} shares of **{s}**.")
        sell_qty = amount

    total = price * sell_qty
    user["wallet"] += total
    user["portfolio"][s] = owned - sell_qty
    save_coins(coins)

    if sell_qty == owned:
        msg = f"🧾 Sold **ALL {sell_qty}** shares of **{s}** for **{total}** coins ({price} each)."
    else:
        msg = f"🧾 Sold **{sell_qty}** shares of **{s}** for **{total}** coins ({price} each)."
    await ctx.send(msg)

@bot.command(name="stocks", help="View current stock prices.")
async def stocks_cmd(ctx):
    stock_data = load_stocks()
    embed = discord.Embed(title="📈 Current Stock Prices", color=discord.Color.green())
    for name in STOCKS:
        price = int(stock_data[name]["price"])
        embed.add_field(name=name, value=f"💰 {price} coins", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="stockvalue", help="Show graph of stock growth.")
async def stockvalue(ctx, stock: str):
    stock_names = {s.lower(): s for s in STOCKS}
    key = stock.lower()
    if key not in stock_names:
        return await ctx.send("❌ Invalid stock.")
    s = stock_names[key]
    stocks = load_stocks()
    if s not in stocks:
        return await ctx.send("❌ Stock not found in database.")
    history = stocks[s]["history"]
    if len(history) < 2:
        return await ctx.send("📉 Not enough data to generate a graph yet.")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(history, marker='o', label=s)
    ax.set_title(f"{s} Price Trend")
    ax.set_xlabel("Update #")
    ax.set_ylabel("Price")
    ax.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    file = discord.File(buf, filename="stock.png")
    embed = discord.Embed(title=f"{s} Stock Value 📈", color=discord.Color.green())
    embed.set_image(url="attachment://stock.png")
    await ctx.send(embed=embed, file=file)

@bot.command(name="portfolio", help="View your stock portfolio.")
async def portfolio(ctx, member: discord.Member = None):
    member = member or ctx.author
    uid = str(member.id)
    coins = load_coins()
    stocks = load_stocks()
    if uid not in coins or "portfolio" not in coins[uid]:
        return await ctx.send("❌ No portfolio data found for this user.")
    pf = coins[uid]["portfolio"]
    embed = discord.Embed(title=f"📦 {member.display_name}'s Portfolio", color=discord.Color.blue())
    total_value = 0
    for s in STOCKS:
        shares = pf.get(s, 0)
        price = int(stocks[s]["price"])
        value = shares * price
        total_value += value
        embed.add_field(name=s, value=f"📊 Shares: `{shares}`\n💰 Price: `{price}`\n📦 Value: `{value}`", inline=False)
    embed.set_footer(text=f"Total Portfolio Value: {total_value} coins")
    await ctx.send(embed=embed)
# =========================
# Marriage
# =========================
# =========================
# Marriage
# =========================
@bot.command(name="marry", help="Propose to someone ❤️")
async def marry(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("❌ You can't marry yourself!")
    if member.bot:
        return await ctx.send("🤖 You can't marry a bot.")

    marriages = load_marriages()
    author_id = str(ctx.author.id)
    target_id = str(member.id)

    # Already married?
    if marriages.get(author_id) or marriages.get(target_id):
        return await ctx.send("💔 One of you is already married.")

    # Target already has a pending proposal?
    if target_id in MARRIAGE_PROPOSALS:
        return await ctx.send("⏳ That person already has a pending proposal. Please wait.")

    MARRIAGE_PROPOSALS[target_id] = author_id
    await ctx.send(
        f"💍 {ctx.author.mention} has proposed to {member.mention}!\n"
        f"{member.mention}, type `!accept` to say yes!"
    )

@bot.command(name="accept", help="Accept a marriage proposal 💖")
async def accept(ctx):
    user_id = str(ctx.author.id)
    proposer_id = MARRIAGE_PROPOSALS.get(user_id)
    if not proposer_id:
        return await ctx.send("❌ You don't have any pending proposals.")

    marriages = load_marriages()

    # Double-check neither is already married
    if marriages.get(proposer_id) or marriages.get(user_id):
        # Clean up stale proposal if any
        MARRIAGE_PROPOSALS.pop(user_id, None)
        return await ctx.send("💔 One of you is already married.")

    # Save both directions for convenience
    marriages[proposer_id] = user_id
    marriages[user_id] = proposer_id
    save_marriages(marriages)

    proposer = await bot.fetch_user(int(proposer_id))
    await ctx.send(f"💞 {ctx.author.mention} and {proposer.mention} are now married! 🎉")

    # Remove the pending proposal
    del MARRIAGE_PROPOSALS[user_id]

@bot.command(name="divorce", help="Divorce your current partner 😢")
async def divorce(ctx):
    user_id = str(ctx.author.id)
    marriages = load_marriages()
    partner_id = marriages.get(user_id)

    if not partner_id:
        return await ctx.send("❌ You are not married.")

    # Remove both records
    marriages.pop(user_id, None)
    marriages.pop(partner_id, None)
    save_marriages(marriages)

    partner = await bot.fetch_user(int(partner_id))
    await ctx.send(f"💔 {ctx.author.mention} and {partner.mention} are now divorced.")

@bot.command(name="partner", help="View your or someone else's partner 💘")
async def partner(ctx, member: discord.Member = None):
    member = member or ctx.author
    marriages = load_marriages()
    partner_id = marriages.get(str(member.id))

    if not partner_id:
        return await ctx.send(f"{member.display_name} is not married.")

    partner_user = await bot.fetch_user(int(partner_id))
    await ctx.send(f"💗 {member.display_name}'s partner is **{partner_user.display_name}**.")

@bot.command(name="flirt", help="Flirt with someone using a cute compliment 😘")
async def flirt(ctx, member: discord.Member):
    if member == ctx.author:
        return await ctx.send("😳 You can’t flirt with yourself... or can you?")
    if member.bot:
        return await ctx.send("🤖 Bots don't understand love... yet.")

    lines = [
        "Are you Wi-Fi? Because I’m feeling a strong connection.",
        "Do you have a map? I keep getting lost in your messages.",
        "If charm were XP, you'd be max level.",
        "You’re the reason the server’s uptime just improved.",
        "I’d share my last health potion with you. 💖",
    ]
    await ctx.send(f"{ctx.author.mention} flirts with {member.mention}:\n> {random.choice(lines)}")

@bot.command(name="stab", help="Stab someone (for jokes). Usage: !stab @user")
async def stab(ctx, member: discord.Member = None):
    # Prefer mention-only so it matches your rob/bankrob behavior
    target_id = only_mention_target(ctx)
    if target_id is None:
        return await ctx.send("❌ Please mention exactly one user: `!stab @user`")

    if target_id == ctx.author.id:
        return await ctx.send("😵 You stabbed yourself. Talent.")
    
    # Fetch member safely (handles cache miss)
    target_member = ctx.guild.get_member(target_id) or await _get_member_safe(ctx.guild, target_id)
    if not target_member:
        return await ctx.send("❌ Could not find that member in this server.")

    if target_member.bot:
        return await ctx.send("🤖 Leave the bots alone 😭")

    # Simple output (as requested)
    await ctx.send(f"🔪 **{ctx.author.display_name}** stabbed **{target_member.display_name}**!")

@bot.command(name="lick", help="Lick someone (for jokes). Usage: !lick @user")
async def lick(ctx, member: discord.Member = None):
    # Require exactly one mention (same behaviour as stab)
    target_id = only_mention_target(ctx)
    if target_id is None:
        return await ctx.send("❌ Please mention exactly one user: `!lick @user`")

    if target_id == ctx.author.id:
        return await ctx.send("You're a freakbob licking urself u twit")

    # Fetch member safely
    target_member = ctx.guild.get_member(target_id) or await _get_member_safe(ctx.guild, target_id)
    if not target_member:
        return await ctx.send("❌ Could not find that member in this server.")

    if target_member.bot:
        return await ctx.send("The bot licks you back (you like it)")

    # Output message
    await ctx.send(f"👅 **{ctx.author.display_name}** licked **{target_member.display_name}**!")

# =========================
# Quests / Events
# =========================
@bot.command(name="startevent", help="(Admin) Start a server-wide event.")
@commands.has_permissions(administrator=True)
async def startevent(ctx, name: str):
    if name not in EVENTS:
        return await ctx.send("❌ Invalid event name. Options: " + ", ".join(EVENTS.keys()))
    save_event({"active": name})
    await ctx.send(f"🎉 Event **{name}** is now active!")

@bot.command(name="endevent", help="(Admin) End the currently active event.")
@commands.has_permissions(administrator=True)
async def endevent(ctx):
    save_event({})
    await ctx.send("⛔ All events have ended.")

@bot.command(name="currentevent", help="View the currently active event.")
async def currentevent(ctx):
    data = load_event()
    name = data.get("active")
    if name:
        await ctx.send(f"🎊 Current Event: **{name}**")
    else:
        await ctx.send("📭 No event is currently running.")

@bot.command(name="quest", help="View your daily quest and reward.")
async def quest(ctx):
    user_id = str(ctx.author.id)
    quests = load_quests()
    if user_id not in quests:
        quests[user_id] = random.choice(QUEST_POOL)
        save_quests(quests)
    q = quests[user_id]
    embed = discord.Embed(
        title="📜 Your Daily Quest",
        description=f"**Task:** {q['task']}\n**Command Hint:** `{q['command']}`\n**Reward:** 💰 {q['reward']} coins",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name="complete", help="Complete your current quest and claim the reward.")
async def complete(ctx):
    user_id = str(ctx.author.id)
    quests = load_quests()
    if user_id not in quests:
        return await ctx.send("❌ You have no active quest.")
    coins = ensure_user_coins(user_id)
    reward = quests[user_id]["reward"]
    coins[user_id]["wallet"] += reward
    del quests[user_id]
    save_coins(coins)
    save_quests(quests)
    await ctx.send(f"✅ Quest completed! You earned **{reward}** coins!")

# =========================
# Announcements
# =========================
@bot.command(name="announcement", help="Post a yellow-embed announcement with @everyone")
async def announcement(ctx, *, message: str):
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not channel:
        return await ctx.send("❌ Announcement channel not found.")
    embed = discord.Embed(description=message, color=discord.Color.yellow())
    await channel.send(
        content="@everyone",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )
    await ctx.send(f"✅ Announcement sent in {channel.mention}")

# =========================
# AFK + Role Colours
# =========================
@bot.command(name="afk", help="Set your AFK status with a reason")
async def afk(ctx, *, reason: str = "AFK"):
    key = f"{ctx.guild.id}-{ctx.author.id}"
    AFK_STATUS[key] = reason
    embed = discord.Embed(description=f"{ctx.author.mention} is now AFK: {reason}", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="rolecolour", help="Post a message where users can choose their color role.")
@commands.has_permissions(manage_roles=True)
async def rolecolour(ctx):
    desc = "\n".join([f"{emoji} = **{role}**" for emoji, role in ROLE_COLOR_EMOJIS.items()])
    embed = discord.Embed(title="🎨 Pick Your Colour!", description=desc, color=discord.Color.purple())
    msg = await ctx.send(embed=embed)
    for emoji in ROLE_COLOR_EMOJIS.keys():
        await msg.add_reaction(emoji)
    with open("role_colour_msg.txt", "w") as f:
        f.write(str(msg.id))

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    try:
        with open("role_colour_msg.txt", "r") as f:
            target_msg_id = int(f.read())
    except FileNotFoundError:
        return
    if payload.message_id != target_msg_id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    if not guild or not member or member.bot:
        return

    role_name = ROLE_COLOR_EMOJIS.get(str(payload.emoji))
    if not role_name:
        return
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)

# =========================
# CoverBot
# =========================

def _restricted_here(ctx) -> bool:
    return (RESTRICT_GUILD_NAME is None) or (ctx.guild and ctx.guild.name == RESTRICT_GUILD_NAME)

async def _get_member_safe(guild: discord.Guild, user_id: int):
    m = guild.get_member(user_id)
    if m:
        return m
    try:
        return await guild.fetch_member(user_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None

@bot.command(name="coverstatus", help="Show whether the Cover bot is in this server.")
async def cover_status(ctx: commands.Context):
    if not _restricted_here(ctx):
        return await ctx.send(f"❌ This command is only for **{RESTRICT_GUILD_NAME}**.")
    member = await _get_member_safe(ctx.guild, COVER_BOT_ID)
    if member:
        await ctx.send("✅ The Cover bot is **already in this server**.")
    else:
        await ctx.send("ℹ️ The Cover bot is **not in this server** yet.")

@bot.command(name="coverjoin", help="Invite the Cover bot (opens the OAuth page).")
@commands.has_permissions(manage_guild=True)
async def cover_join(ctx: commands.Context):
    if not _restricted_here(ctx):
        return await ctx.send(f"❌ This command is only for **{RESTRICT_GUILD_NAME}**.")
    member = await _get_member_safe(ctx.guild, COVER_BOT_ID)
    if member:
        return await ctx.send("✅ The Cover bot is already here.")

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Invite Cover Bot", url=COVER_INVITE_URL))
    embed = discord.Embed(
        title="Add the Cover bot",
        description=("Click the button below to open the Discord OAuth2 page.\n"
                     "You must be logged in and have **Manage Server** permission here."),
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed, view=view)

    # Also DM the inviter (nice QoL; ignore if DMs are closed)
    try:
        dm_view = discord.ui.View()
        dm_view.add_item(discord.ui.Button(label="Invite Cover Bot", url=COVER_INVITE_URL))
        await ctx.author.send("Here’s the invite link for the Cover bot:", view=dm_view)
    except discord.Forbidden:
        pass

@bot.command(name="coverleave", help="Remove the Cover bot from this server.")
@commands.has_permissions(kick_members=True)
async def cover_leave(ctx: commands.Context):
    if not _restricted_here(ctx):
        return await ctx.send(f"❌ This command is only for **{RESTRICT_GUILD_NAME}**.")
    member = await _get_member_safe(ctx.guild, COVER_BOT_ID)
    if not member:
        return await ctx.send("ℹ️ The Cover bot isn’t in this server.")

    # Your bot needs a role above the Cover bot and Kick Members permission.
    try:
        await member.kick(reason=f"Requested by {ctx.author} via !coverleave")
        await ctx.send("👋 The Cover bot has been removed from this server.")
    except discord.Forbidden:
        await ctx.send("❌ I don’t have permission to kick that bot (role too low or missing permission).")
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to remove: {type(e).__name__}. Try again later.")

@bot.command(name="prayer", help="Show what prayer time we're in now + what's next (ELM times).")
async def prayer(ctx):
    try:
        today = await fetch_elm_today()
    except Exception:
        return await ctx.send("⚠️ Couldn’t fetch ELM prayer times right now. Try again in a bit.")

    now = datetime.now(LONDON_TZ)
    begins = today["begins"]

    # Order of prayers for the day
    order = ["Fajr", "Zuhr", "Asr", "Maghrib", "Isha"]
    times = [(p, begins[p]) for p in order]
    times.sort(key=lambda x: x[1])

    current_prayer = None
    next_prayer = None

    for i, (p, t) in enumerate(times):
        nxt = times[i + 1][0] if i + 1 < len(times) else None
        nxt_t = times[i + 1][1] if i + 1 < len(times) else None

        if now >= t and (nxt_t is None or now < nxt_t):
            current_prayer = p
            next_prayer = nxt
            next_time = nxt_t
            break

    # If it's after Isha begins, next is tomorrow's Fajr (we’ll just label it)
    if current_prayer is None and now < begins["Fajr"]:
        current_prayer = "Before Fajr"
        next_prayer = "Fajr"
        next_time = begins["Fajr"]
    elif current_prayer == "Isha" and next_prayer is None:
        next_prayer = "Fajr (tomorrow)"
        next_time = None

    embed = discord.Embed(title="🕌 Prayer Status (ELM)", color=discord.Color.purple())
    embed.add_field(name="Date", value=f"{today['date']} • {today['hijri']}", inline=False)

    if current_prayer and current_prayer != "Before Fajr":
        embed.add_field(
            name="You can pray now",
            value=f"✅ **{current_prayer}** (began {begins[current_prayer].strftime('%H:%M')})",
            inline=False
        )
    else:
        embed.add_field(name="You can pray now", value="⏳ Not in a prayer window yet (before Fajr).", inline=False)

    if next_prayer == "Fajr (tomorrow)":
        embed.add_field(name="Next prayer", value="➡️ **Fajr (tomorrow)**", inline=False)
    else:
        remaining = int((next_time - now).total_seconds()) if next_time else None
        if remaining is not None:
            h = remaining // 3600
            m = (remaining % 3600) // 60
            embed.add_field(
                name="Next prayer",
                value=f"➡️ **{next_prayer}** at **{next_time.strftime('%H:%M')}** (in {h}h {m}m)",
                inline=False
            )

    # quick table of begins/jamaah
    lines = []
    for p in ["Fajr", "Zuhr", "Asr", "Maghrib", "Isha"]:
        lines.append(
            f"**{p}:** begins {today['begins'][p].strftime('%H:%M')} • jamā‘ah {today['jamaah'][p].strftime('%H:%M')}"
        )
    embed.add_field(name="Today’s times", value="\n".join(lines)[:1024], inline=False)

    await ctx.send(embed=embed)

@bot.command(
    name="baltop",
    help="Show the richest users by total balance (wallet + bank). Usage: !baltop [count]"
)
async def baltop(ctx, count: int = 10):
    guild = ctx.guild
    coins = load_coins()

    # clamp leaderboard size
    count = max(3, min(25, count))

    entries = []

    for member in guild.members:
        if member.bot:
            continue
        data = coins.get(str(member.id))
        if not data:
            continue

        wallet = int(data.get("wallet", 0))
        bank = int(data.get("bank", 0))
        total = wallet + bank

        if total > 0:
            entries.append((member, wallet, bank, total))

    if not entries:
        return await ctx.send("💸 No balance data yet.")

    # sort by total balance
    entries.sort(key=lambda x: x[3], reverse=True)

    lines = []
    for i, (member, wallet, bank, total) in enumerate(entries[:count], start=1):
        crown = " 👑" if i == 1 else ""
        you = " ← you" if member.id == ctx.author.id else ""
        lines.append(
            f"**{i}.** {member.mention}{crown} — "
            f"💼 {wallet} · 🏦 {bank} · **{total}** coins{you}"
        )

    your_rank = next(
        (i for i, (m, *_rest) in enumerate(entries, start=1) if m.id == ctx.author.id),
        None
    )

    embed = discord.Embed(
        title="💰 Balance Leaderboard",
        description="\n".join(lines),
        color=discord.Color.green()
    )

    if your_rank:
        embed.set_footer(text=f"Your rank: {your_rank}/{len(entries)}")

    await ctx.send(embed=embed)


# =========================
# Message events (AFK + XP)
# =========================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # ===== Word filter: "pathical" =====
    if "pathical" in message.content.lower():
        try:
            await message.delete()
        except discord.Forbidden:
            pass  # bot can't delete messages

        await message.channel.send(
            f"{message.author.mention} stop being a bum 😭",
            delete_after=5
        )
        return  # stop further processing

    key = f"{message.guild.id}-{message.author.id}"
    if key in AFK_STATUS:
        del AFK_STATUS[key]
        await message.channel.send(embed=discord.Embed(
            description=f"{message.author.mention} is no longer AFK.",
            color=discord.Color.red()
        ))

    for user in message.mentions:
        mention_key = f"{message.guild.id}-{user.id}"
        if mention_key in AFK_STATUS:
            reason = AFK_STATUS[mention_key]
            await message.channel.send(embed=discord.Embed(
                description=f"{user.display_name} is currently AFK: {reason}",
                color=discord.Color.purple()
            ))

    await update_xp(message.author.id, message.guild.id, XP_PER_MESSAGE)

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        return

    # Create an embed
    embed = discord.Embed(
        title=f"Welcome to QMUL - Unofficial 🎓",
        description=f"{member.mention}, we're glad to have you here!",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text="Make sure to check out the channels and have fun!")

    # Send the embed
    await channel.send(embed=embed)

# =========================
# Background Tasks
# =========================
@tasks.loop(seconds=INTEREST_INTERVAL)
async def apply_bank_interest():
    await bot.wait_until_ready()
    coins = load_coins()
    changed = False
    for _, balances in coins.items():
        bank_balance = balances.get("bank", 0)
        if bank_balance > 0:
            interest = int(bank_balance * INTEREST_RATE)
            if interest > 0:
                balances["bank"] += interest
                changed = True
    if changed:
        save_coins(coins)
        print("[Interest] Applied interest to bank balances.")

@tasks.loop(minutes=5)
async def update_stock_prices():
    await bot.wait_until_ready()
    global STOCK_PURCHASE_COUNT
    stocks = load_stocks()
    total_purchases = sum(STOCK_PURCHASE_COUNT.values())
    growth_bias = random.uniform(0.01, 0.02)

    crash_triggered = random.randint(1, 15) == 1
    boom_triggered  = random.randint(1, 15) == 1
    mega_crash_triggered = random.randint(1, 100) == 1
    mega_boom_triggered  = random.randint(1, 100) == 1

    crash_multiplier       = random.uniform(0.4, 0.8)
    boom_multiplier        = random.uniform(2.3, 2.8)
    mega_crash_multiplier  = random.uniform(0.1, 0.3)
    mega_boom_multiplier   = random.uniform(6.0, 7.0)

    crashed, boomed, mega_crashed, mega_boomed = [], [], [], []

    for s in STOCKS:
        current_price = int(stocks[s]["price"])
        purchase_count = STOCK_PURCHASE_COUNT.get(s, 0)

        if mega_crash_triggered and current_price > 10000:
            new_price = max(1, int(current_price * mega_crash_multiplier))
            mega_crashed.append((s, current_price, new_price))
        elif crash_triggered and current_price > 5000:
            new_price = max(1, int(current_price * crash_multiplier))
            crashed.append((s, current_price, new_price))
        elif mega_boom_triggered and current_price < 2000:
            new_price = int(current_price * mega_boom_multiplier)
            mega_boomed.append((s, current_price, new_price))
        elif boom_triggered and current_price < 3000:
            new_price = int(current_price * boom_multiplier)
            boomed.append((s, current_price, new_price))
        else:
            if total_purchases > 0:
                purchase_ratio = purchase_count / total_purchases
                change = 0.5 * (purchase_ratio - 0.25) + growth_bias
            else:
                change = random.uniform(-0.05, 0.05) + growth_bias
            new_price = max(1, int(current_price * (1 + change)))

        stocks[s]["price"] = new_price
        stocks[s]["history"].append(new_price)
        if len(stocks[s]["history"]) > 24:
            stocks[s]["history"] = stocks[s]["history"][-24:]

    save_stocks(stocks)
    STOCK_PURCHASE_COUNT = {s: 0 for s in STOCKS}

    channel = bot.get_channel(MARKET_ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    if mega_crashed:
        desc = "\n".join(f"💥 **{s}** plummeted from **{old}** → **{new}** coins" for s, old, new in mega_crashed)
        await channel.send(embed=discord.Embed(title="💀 MEGA CRASH!", description=f"A catastrophic collapse hit the market!\n\n{desc}", color=discord.Color.dark_red()))
    if crashed:
        desc = "\n".join(f"🔻 **{s}** crashed from **{old}** → **{new}** coins" for s, old, new in crashed)
        await channel.send(embed=discord.Embed(title="📉 Market Crash!", description=f"Some overvalued stocks took a hit:\n\n{desc}", color=discord.Color.red()))
    if mega_boomed:
        desc = "\n".join(f"🚀 **{s}** exploded from **{old}** → **{new}** coins" for s, old, new in mega_boomed)
        await channel.send(embed=discord.Embed(title="🚨 MEGA BOOM!", description=f"Insane surges swept the market!\n\n{desc}", color=discord.Color.gold()))
    if boomed:
        desc = "\n".join(f"📈 **{s}** rose from **{old}** → **{new}** coins" for s, old, new in boomed)
        await channel.send(embed=discord.Embed(title="📈 Market Boom!", description=f"Undervalued stocks surged upward:\n\n{desc}", color=discord.Color.green()))

@tasks.loop(seconds=DIVIDEND_INTERVAL)
async def pay_dividends():
    await bot.wait_until_ready()
    coins = load_coins()
    stocks = load_stocks()
    any_payout = False
    for user_id, data in coins.items():
        pf = data.get("portfolio", {})
        total_value = sum(pf.get(s, 0) * int(stocks[s]["price"]) for s in STOCKS)
        payout = int(total_value * DIVIDEND_RATE)
        if payout > 0:
            data["wallet"] += payout
            any_payout = True
    if any_payout:
        save_coins(coins)
        channel = bot.get_channel(MARKET_ANNOUNCE_CHANNEL_ID)
        if channel:
            await channel.send("💸 Dividends have been paid out to all shareholders!")

@tasks.loop(seconds=20)
async def prayer_time_notifier():
    await bot.wait_until_ready()
    channel = bot.get_channel(PRAYER_UPDATES_CHANNEL_ID)
    if not channel:
        return

    # Load today’s times
    try:
        today = await fetch_elm_today()
    except Exception:
        return  # fail silently; you can log if you want

    now = datetime.now(LONDON_TZ)
    date_key = now.strftime("%Y-%m-%d")

    state = _load_state(PRAYER_NOTIF_STATE_FILE, {"date": None, "sent": {}})

    # Reset state if new day
    if state.get("date") != date_key:
        state = {"date": date_key, "sent": {}}

    # Notify once per prayer
    for prayer, t in today["begins"].items():
        # fire when we are within a small window after start
        if now >= t and (now - t).total_seconds() <= 90:
            if state["sent"].get(prayer):
                continue

            jam = today["jamaah"][prayer].strftime("%H:%M")
            beg = t.strftime("%H:%M")

            embed = discord.Embed(
                title="🕌 Prayer Time",
                description=f"**{prayer}** has begun (**{beg}**).\nJamā‘ah at **{jam}**.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"ELM • {today['date']} • {today['hijri']}")
            await channel.send(embed=embed)

            state["sent"][prayer] = True
            _save_state(PRAYER_NOTIF_STATE_FILE, state)

@tasks.loop(minutes=5)
async def ramadan_daily_iftar_post():
    await bot.wait_until_ready()
    channel = bot.get_channel(PRAYER_UPDATES_CHANNEL_ID)
    if not channel:
        return

    now = datetime.now(LONDON_TZ)
    date_key = now.strftime("%Y-%m-%d")

    state = _load_state(RAMADAN_POST_STATE_FILE, {"date": None})

    # Post once per day, in the morning (adjust hour if you want)
    if state.get("date") == date_key:
        return
    if now.hour < 8:  # don’t post before 8am
        return

    try:
        today = await fetch_elm_today()
    except Exception:
        return

    iftar_time = today["begins"]["Maghrib"].strftime("%H:%M")

    embed = discord.Embed(
        title="🌙 Ramadan Update",
        description=f"**Iftar (Maghrib begins): {iftar_time}**\n\nTimetable:",
        color=discord.Color.gold()
    )
    # show the timetable image if the URL is valid
    if RAMADAN_TIMETABLE_IMAGE_URL:
        embed.set_image(url=RAMADAN_TIMETABLE_IMAGE_URL)

    embed.set_footer(text=f"ELM • {today['date']} • {today['hijri']}")
    await channel.send(embed=embed)

    _save_state(RAMADAN_POST_STATE_FILE, {"date": date_key})

# =========================
# Ready
# =========================
@bot.event
async def on_ready():
    print(f"{bot.user} is online and ready!")
    if not apply_bank_interest.is_running():
        apply_bank_interest.start()
    if not update_stock_prices.is_running():
        update_stock_prices.start()
    if not pay_dividends.is_running():
        pay_dividends.start()

# =========================
# Boot
# =========================
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in environment.")
    bot.run(TOKEN)
