#!/usr/bin/env python3
import json
import os
from difflib import get_close_matches
from collections import Counter
from typing import Sequence

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# ==============================================================================
# 1. Configuration & Setup
# ==============================================================================

# Load configuration from Discord.env
ENV_PATH = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Discord.env"
load_dotenv(ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
EVOLUTION_DB_PATH = os.getenv("EVOLUTION_DB_PATH")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")
GUILD_IDS_ENV = os.getenv("GUILD_IDS")  # Optional: comma-separated list of guild IDs

# Parse Channel ID
if TARGET_CHANNEL_ID is not None:
    try:
        TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID)
    except ValueError:
        TARGET_CHANNEL_ID = None

# Parse Test Guild IDs
TEST_GUILDS = []
if GUILD_IDS_ENV:
    for raw in GUILD_IDS_ENV.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            TEST_GUILDS.append(int(raw))
        except ValueError:
            pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# NOTE: Only the new unified evolution DB is supported going forward.
# Legacy files (e.g., evolution_db1.json) are intentionally ignored so that
# Discord embeds always reflect the latest schema with attempt counters.
DEFAULT_DB_FILES = ["evolution_db.json"]
RESOLVED_DB_PATH: str | None = None

# ==============================================================================
# 2. ANSI Color Helpers
# ==============================================================================

def ansi(text: str, color_code: str) -> str:
    """
    Wraps text in Discord ANSI escape codes.
    Common Codes:
    30=Gray, 31=Red, 32=Green, 33=Yellow, 34=Blue, 35=Pink, 36=Cyan, 37=White
    Prefix with '1;' for Bold (e.g., '1;36' is Bold Cyan).
    """
    return f"\u001b[{color_code}m{text}\u001b[0m"

# ==============================================================================
# 3. Formatting Functions (with ANSI Support)
# ==============================================================================

def resolve_db_path() -> str:
    """
    Decide which evolution DB to load.
    Priority:
      1. EVOLUTION_DB_PATH (if it exists)
      2. evolution_db1.json next to this script
      3. evolution_db.json next to this script
    """
    global RESOLVED_DB_PATH
    if RESOLVED_DB_PATH and os.path.exists(RESOLVED_DB_PATH):
        return RESOLVED_DB_PATH

    # Respect an explicitly provided path if it exists
    if EVOLUTION_DB_PATH and os.path.exists(EVOLUTION_DB_PATH):
        RESOLVED_DB_PATH = EVOLUTION_DB_PATH
        return RESOLVED_DB_PATH

    # Fall back to common filenames beside the script
    for name in DEFAULT_DB_FILES:
        candidate = os.path.join(SCRIPT_DIR, name)
        if os.path.exists(candidate):
            RESOLVED_DB_PATH = candidate
            return RESOLVED_DB_PATH

    search_list = [EVOLUTION_DB_PATH] if EVOLUTION_DB_PATH else []
    search_list.extend(DEFAULT_DB_FILES)
    raise FileNotFoundError(
        "Could not locate an evolution DB. "
        "Searched (in order): " + ", ".join(str(p) for p in search_list if p)
    )


def load_evolution_db() -> dict:
    """Load the evolution DB (supports both old and new filenames)."""
    db_path = resolve_db_path()

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("evolution DB root is not an object/dict")

    return data


def format_gem_counts_ansi(gem_counts: dict) -> str:
    """Formats gem counts with Green keys and White values."""
    if not gem_counts:
        return "(none)"
    lines = []
    for key, value in gem_counts.items():
        # 32 = Green, 37 = White
        lines.append(f"{ansi(key, '0;32')}: {ansi(str(value), '0;37')}")
    return "\n".join(lines)


def format_stats_ansi(stats: dict) -> str:
    """Formats stats with Pink keys and Cyan values."""
    if not stats:
        return "(none)"

    ordered_keys = [
        "Perfect Points", "Combo Multiplier", "Fever Multiplier",
        "Fever Fill Rate", "Fever Time", "Chill", "Flow", "Rush", "Beat", "Vibe"
    ]

    lines = []
    
    def add_line(k, v):
        # 35 = Pink, 36 = Cyan
        lines.append(f"{ansi(k, '0;35')}: {ansi(str(v), '0;36')}")

    for key in ordered_keys:
        if key in stats:
            add_line(key, stats[key])
            
    for key, value in stats.items():
        if key not in ordered_keys:
            add_line(key, value)
            
    return "\n".join(lines)


def find_best_song_match(db: dict, query: str, difficulty: str = "all"):
    """
    Find best match for song name with optional difficulty filtering.
    difficulty: 'hard', 'normal', or 'all'
    """
    query = query.strip().lower()
    if not query:
        return None

    all_keys = list(db.keys())
    candidates = []

    # Filter keys based on difficulty preference
    if difficulty == "hard":
        # Must contain "(hard)"
        candidates = [k for k in all_keys if "(hard)" in k.lower()]
    elif difficulty == "normal":
        # Must NOT contain "(hard)"
        candidates = [k for k in all_keys if "(hard)" not in k.lower()]
    else:
        # 'all' or unknown -> Search everything
        candidates = all_keys

    # If filtering left us with nothing, return None immediately
    if not candidates:
        return None

    # 1. Exact match within candidates
    for key in candidates:
        if key.lower() == query:
            return key

    # 2. Substring match within candidates
    substring_matches = [k for k in candidates if query in k.lower()]
    if len(substring_matches) == 1:
        return substring_matches[0]
    elif len(substring_matches) > 1:
        best = get_close_matches(query, substring_matches, n=1, cutoff=0.0)
        if best:
            return best[0]

    # 3. Fuzzy match within candidates
    best = get_close_matches(query, candidates, n=1, cutoff=0.0)
    if best:
        return best[0]
        
    return None

# ==============================================================================
# 4. Embed Builders (The Visuals)
# ==============================================================================
def canonical_number(val):
    """Best-effort cast to int/float for consistent hashing and display."""
    try:
        f = float(val)
        if f.is_integer():
            return int(f)
        return round(f, 3)
    except (TypeError, ValueError):
        return val

def normalize_record_variant(record: dict, placement: int = 1) -> tuple[dict, int]:
    """
    Return a normalized record for the requested placement.
    Placement 1 -> top score (default record)
    Placement 2 -> uses record['second'] when present, else falls back to placement 1
    """
    def _sig(rec: dict) -> tuple:
        """Build a content signature to detect duplicate placements with differing scores."""
        gear_list = rec.get("gear", rec.get("loadout", [])) or []
        minis_list = rec.get("minis", []) or []
        details = rec.get("details", {}) or {}
        try:
            details_key = json.dumps(details, sort_keys=True)
        except Exception:
            details_key = str(details)
        return (tuple(gear_list), tuple(minis_list), details_key)

    placement = 2 if placement == 2 else 1
    base = record or {}
    base_attempts = base.get("attempt_lifetime", base.get("attempts"))
    attempts_first = base.get("attempts_first")
    attempts_second = base.get("attempts_second")

    base_sig = _sig(base)

    if placement == 2:
        runner_up = base.get("second")
        if isinstance(runner_up, dict) and _sig(runner_up) != base_sig:
            return (
                {
                    "score": runner_up.get("score", base.get("score")),
                    "gear": runner_up.get("gear") or runner_up.get("loadout") or base.get("gear") or base.get("loadout") or [],
                    "minis": runner_up.get("minis") or [],
                    "details": runner_up.get("details", {}),
                    "attempts": attempts_second,
                    "attempt_lifetime": base_attempts,
                },
                2,
            )

    return (
        {
            "score": base.get("score"),
            "gear": base.get("gear", base.get("loadout", [])),
            "minis": base.get("minis", []),
            "details": base.get("details", {}),
            "attempts": attempts_first,
            "attempt_lifetime": base_attempts,
        },
        1,
    )


def placement_label(placement: int) -> str:
    return "2nd" if placement == 2 else "1st"


def build_song_embed(song_key: str, record: dict, placement: int = 1) -> discord.Embed:
    normalized, actual_placement = normalize_record_variant(record, placement)

    score = normalized.get("score")
    details = normalized.get("details", {})
    attempts = normalized.get("attempts")
    attempt_lifetime = normalized.get("attempt_lifetime")
    
    ft = details.get("FT")
    ff = details.get("FF")
    selected_element = details.get("SelectedElement", "N/A")
    gem_counts = details.get("GemCounts", {})
    stats = details.get("Stats", {})

    gear_list = normalized.get("gear", [])
    minis_list = normalized.get("minis", [])

    # 1. Main Embed Frame
    embed = discord.Embed(
        title=f"{song_key} — {placement_label(actual_placement)}",
        color=discord.Color.from_rgb(43, 45, 49), # Dark gray to blend with code blocks
    )

    # 2. Best Score -> Bold Cyan (1;36)
    score_val = f"{score:,}" if score is not None else "N/A"
    embed.add_field(
        name="Best Score", 
        value=f"```ansi\n{ansi(score_val, '1;36')}\n```", 
        inline=False
    )

    # 3. Gear & Minis -> Yellow (0;33)
    gear_str = "\n".join(f"• {g}" for g in gear_list) if gear_list else "(none)"
    minis_str = "\n".join(f"• {m}" for m in minis_list) if minis_list else "(none)"

    embed.add_field(
        name="Gear", 
        value=f"```ansi\n{ansi(gear_str, '0;33')}\n```", 
        inline=True
    )
    embed.add_field(
        name="Minis", 
        value=f"```ansi\n{ansi(minis_str, '0;33')}\n```", 
        inline=True
    )

    # 4. Fever Config -> Blue Labels (34), White Values (37)
    ft_val = str(ft) if ft is not None else "N/A"
    ff_val = str(ff) if ff is not None else "N/A"
    
    fever_lines = [
        f"{ansi('Element', '0;34')} : {selected_element}",
        f"{ansi('FT Gems', '0;34')} : {ft_val}",
        f"{ansi('FF Gems', '0;34')} : {ff_val}"
    ]
    
    embed.add_field(
        name="Fever Config", 
        value=f"```ansi\n{chr(10).join(fever_lines)}\n```", 
        inline=False
    )

    # 5. Gem Allocation -> Green Labels (32)
    embed.add_field(
        name="Gem Allocation", 
        value=f"```ansi\n{format_gem_counts_ansi(gem_counts)}\n```", 
        inline=False
    )

    # 6. Final Stats -> Pink Labels (35), Cyan Values (36)
    embed.add_field(
        name="Final Stats", 
        value=f"```ansi\n{format_stats_ansi(stats)}\n```", 
        inline=False
    )
    
    footer_note = "RoBeats Gear Optimizer"
    if attempts is not None:
        footer_note += f" • attempts ({placement_label(actual_placement)}): {attempts}"
    if attempt_lifetime is not None:
        footer_note += f" • attempts (lifetime): {attempt_lifetime}"
    if placement == 2 and actual_placement == 1 and not record.get("second"):
        footer_note += " | 2nd entry not found; showing 1st"
    embed.set_footer(text=footer_note)

    return embed


def aggregate_color_category(db: dict, color: str) -> dict | None:
    """
    Aggregate information for a given element (Primary first, then Selected as fallback).
    Returns a summary dict or None if no songs match that element.
    """
    target = color.strip().lower()
    if not target:
        return None

    songs = []
    canonical_name = None

    def norm(val):
        return val.strip().lower() if isinstance(val, str) else ""

    def pick_display(*vals):
        return next((v for v in vals if isinstance(v, str) and v.strip()), color.strip())

    for song_key, record in db.items():
        details = record.get("details", {})
        primary = norm(details.get("PrimaryColor") or details.get("Primary Color"))
        sel = norm(details.get("SelectedElement") or details.get("Selected Element"))
        matched = False
        if primary == target:
            matched = True
        elif not primary and sel == target:
            matched = True
        if matched:
            songs.append((song_key, record))
            if canonical_name is None:
                canonical_name = pick_display(
                    details.get("SelectedElement") or details.get("Selected Element"),
                    details.get("PrimaryColor") or details.get("Primary Color"),
                )

    if not songs:
        return None

    gear_counter = Counter()
    mini_counter = Counter()
    loadout_counter = Counter()
    minis_combo_counter = Counter()
    gem_config_counter = Counter()

    for _, record in songs:
        details = record.get("details", {})
        gear_list = record.get("gear", record.get("loadout", [])) or []
        minis_list = record.get("minis", []) or []

        # Count individual gear & minis
        for g in gear_list:
            gear_counter[g] += 1
        for m in minis_list:
            mini_counter[m] += 1

        # Count full loadouts and mini teams
        if gear_list:
            loadout_counter[tuple(gear_list)] += 1
        if minis_list:
            minis_combo_counter[tuple(minis_list)] += 1

        # Track most frequent gem configuration (including FT / FF)
        gem_counts_dict = details.get("GemCounts") or {}
        norm_gems = {}
        if isinstance(gem_counts_dict, dict):
            for k, v in gem_counts_dict.items():
                norm_gems[k] = canonical_number(v)

        ft = canonical_number(details.get("FT"))
        ff = canonical_number(details.get("FF"))
        config_key = (ft, ff, tuple(sorted(norm_gems.items())))
        gem_config_counter[config_key] += 1

    result = {
        "color": canonical_name or color.strip(),
        "song_count": len(songs),
    }

    if loadout_counter:
        best_loadout, best_loadout_count = loadout_counter.most_common(1)[0]
        result["best_loadout"] = list(best_loadout)
        result["best_loadout_count"] = best_loadout_count

    if minis_combo_counter:
        best_minis, best_minis_count = minis_combo_counter.most_common(1)[0]
        result["best_minis"] = list(best_minis)
        result["best_minis_count"] = best_minis_count

    if gear_counter:
        result["top_gear"] = gear_counter.most_common(6)

    if mini_counter:
        result["top_minis"] = mini_counter.most_common(6)

    if gem_config_counter:
        (ft_val, ff_val, gem_items), freq = gem_config_counter.most_common(1)[0]
        result["gem_mode"] = {
            "FT": ft_val,
            "FF": ff_val,
            "GemCounts": {k: v for k, v in gem_items},
            "uses": freq,
        }

    return result


def build_meta_loadout_embed(summary: dict) -> discord.Embed:
    """
    Build an embed for /meta showing:
    - Element color
    - # of songs in that category
    - Most common gear loadout
    - Most common mini team
    - Most common gem allocation (including Fever Time / Fever Fill gems)
    """
    color_name = summary.get("color", "Unknown")
    song_count = summary.get("song_count", 0)

    embed = discord.Embed(
        title=f"{color_name} Category — Meta",
        color=discord.Color.from_rgb(43, 45, 49),
    )

    # Overview
    overview_lines = [
        f"{ansi('Element', '0;34')}: {ansi(color_name, '1;36')}",
        f"{ansi('Songs in DB', '0;34')}: {ansi(str(song_count), '1;36')}",
    ]
    embed.add_field(
        name="Overview",
        value=f"```ansi\n{chr(10).join(overview_lines)}\n```",
        inline=False,
    )

    # Most common gear loadout
    best_loadout = summary.get("best_loadout")
    if best_loadout:
        count = summary.get("best_loadout_count", 0)
        lines = [ansi("Most common gear loadout:", "0;33"), ""]
        lines.extend(f"• {g}" for g in best_loadout)
        lines.append("")
        lines.append(ansi(f"Used in {count} run(s).", "0;37"))
        embed.add_field(
            name="Gear Loadout",
            value=f"```ansi\n{chr(10).join(lines)}\n```",
            inline=False,
        )

    # Most common mini team
    best_minis = summary.get("best_minis")
    if best_minis:
        count = summary.get("best_minis_count", 0)
        lines = [ansi("Most common mini team:", "0;33"), ""]
        lines.extend(f"• {m}" for m in best_minis)
        lines.append("")
        lines.append(ansi(f"Used in {count} run(s).", "0;37"))
        embed.add_field(
            name="Mini Team",
            value=f"```ansi\n{chr(10).join(lines)}\n```",
            inline=False,
        )

    # Most common gem allocation across all songs of this color
    gem_mode = summary.get("gem_mode")
    if gem_mode:
        gem_lines = []
        ft_val = gem_mode.get("FT")
        ff_val = gem_mode.get("FF")
        uses = gem_mode.get("uses", 0)

        if ft_val is not None:
            gem_lines.append(f"{ansi('FT Gems', '0;34')}: {ft_val}")
        if ff_val is not None:
            gem_lines.append(f"{ansi('FF Gems', '0;34')}: {ff_val}")
        gem_lines.append("")
        gem_lines.append(ansi("GemCounts:", "0;34"))
        gem_lines.append(format_gem_counts_ansi(gem_mode.get("GemCounts", {})))
        gem_lines.append("")
        gem_lines.append(ansi(f"Used in {uses} run(s).", "0;37"))

        embed.add_field(
            name="Most common gem allocation",
            value=f"```ansi\n{chr(10).join(gem_lines)}\n```",
            inline=False,
        )

    embed.set_footer(text="RoBeats Gear Optimizer – Meta summary")
    return embed


def emphasize_query_fragment(text: str, query: str) -> str:
    """Bold the first matching substring inside a gear name for readability."""
    if not isinstance(text, str):
        return str(text)

    query = query.strip().lower()
    if not query:
        return text

    lower_text = text.lower()
    idx = lower_text.find(query)
    if idx == -1:
        return text

    end = idx + len(query)
    return f"{text[:idx]}**{text[idx:end]}**{text[end:]}"


def build_gear_usage_embeds(
    matches: Sequence[dict],
    display_name: str,
    query: str,
    placement: int,
    per_page: int = 5,
) -> list[discord.Embed]:
    """Build paginated embeds showing which songs use the requested gear snippet."""
    if not matches:
        embed = discord.Embed(
            title=f"Gear usage for “{display_name or query}”",
            description="No loadouts were found.",
            color=discord.Color.from_rgb(43, 45, 49),
        )
        return [embed]

    total = len(matches)
    pages: list[discord.Embed] = []
    total_pages = (total + per_page - 1) // per_page

    for page_index in range(total_pages):
        start = page_index * per_page
        chunk = matches[start : start + per_page]

        lines: list[str] = []
        for absolute_idx, entry in enumerate(chunk, start=start + 1):
            song_name = entry.get("song", "Unknown Song")
            score_val = canonical_number(entry.get("score"))
            if isinstance(score_val, (int, float)):
                score_text = f"{score_val:,}"
            elif score_val is None:
                score_text = "N/A"
            else:
                score_text = str(score_val)

            gear_list = entry.get("gear") or []
            highlighted_gears = [
                emphasize_query_fragment(str(g), query) for g in gear_list if g
            ]
            gear_text = ", ".join(highlighted_gears) if highlighted_gears else "(none)"

            minis_list = entry.get("minis") or []
            minis_text = ", ".join(str(m) for m in minis_list if m)

            lines.append(f"**{absolute_idx}. {song_name}**")
            lines.append(f"Score: {score_text}")
            lines.append(f"Gear: {gear_text}")
            if minis_text:
                lines.append(f"Minis: {minis_text}")
            lines.append("")

        description = "\n".join(lines).strip()
        embed = discord.Embed(
            title=f"Gear usage for “{display_name or query}” — placement {placement}",
            description=description or "No details available.",
            color=discord.Color.from_rgb(43, 45, 49),
        )
        embed.set_footer(
            text=f"Page {page_index + 1}/{total_pages} • Total songs: {total}"
        )
        pages.append(embed)

    return pages


class GearUsagePaginator(discord.ui.View):
    """Simple Previous/Next paginator for /find_gears results."""

    def __init__(self, user_id: int, pages: Sequence[discord.Embed], timeout: float = 120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.pages = list(pages)
        self.current_page = 0
        self.message: discord.Message | None = None
        self._sync_button_states()

    def _sync_button_states(self):
        total = len(self.pages)
        if total <= 1:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            return

        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= total - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the command invoker can use these controls.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        if not self.message:
            return
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page == 0:
            await interaction.response.defer()
            return

        self.current_page -= 1
        self._sync_button_states()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page >= len(self.pages) - 1:
            await interaction.response.defer()
            return

        self.current_page += 1
        self._sync_button_states()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

# ==============================================================================
# 5. Bot Instance & Events
# ==============================================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    """Called when the bot is fully connected."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    try:
        global_synced = await tree.sync()
        print(f"[on_ready] Globally synced {len(global_synced)} command(s).")

        if TEST_GUILDS:
            for gid in TEST_GUILDS:
                g_obj = discord.Object(id=gid)
                synced = await tree.sync(guild=g_obj)
                print(f"[on_ready] Per-guild sync -> {len(synced)} command(s) in guild {gid}.")
    except Exception as e:
        print(f"[on_ready] Failed to sync commands: {e}")

    if TARGET_CHANNEL_ID:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel is not None:
            try:
                await channel.send(
                    "**RoBeats Gear Optimizer Bot is online.** "
                    "Use `/find <song>` or `/meta <element>` to query the evolution database."
                )
            except Exception as e:
                print(f"Failed to send startup message: {e}")

# ==============================================================================
# 6. Slash Commands
# ==============================================================================

@tree.command(name="find", description="Find song stats (Auto-searches for both Normal and Hard versions).")
@app_commands.describe(
    song_name="Song name (full or partial, case-insensitive)",
    placement="Which entry to display: 1 (best) or 2 (runner-up). Default: 1",
)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.allowed_installs(guilds=True, users=False)
async def find_song(
    interaction: discord.Interaction,
    song_name: str,
    placement: app_commands.Range[int, 1, 2] = 1,
):
    await interaction.response.defer(thinking=True)

    try:
        db = load_evolution_db()
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to load evolution_db.json: `{e}`", ephemeral=True)
        return

    if not db:
        await interaction.followup.send("⚠️ `evolution_db.json` is empty.", ephemeral=True)
        return

    # ---------------------------------------------------------
    # DUAL SEARCH: Look for Normal AND Hard independently
    # ---------------------------------------------------------
    match_normal = find_best_song_match(db, song_name, difficulty="normal")
    match_hard = find_best_song_match(db, song_name, difficulty="hard")

    found_embeds = []

    # Build Normal Embed
    if match_normal:
        record = db.get(match_normal)
        if isinstance(record, dict):
            found_embeds.append(build_song_embed(match_normal, record, placement))

    # Build Hard Embed
    if match_hard:
        # Prevent duplicate if for some reason fuzzy matching returned the exact same key twice
        if match_hard != match_normal:
            record = db.get(match_hard)
            if isinstance(record, dict):
                found_embeds.append(build_song_embed(match_hard, record, placement))

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------
    if not found_embeds:
        # If neither was found, fallback to a generic "All" search to show close matches
        # from the entire DB so the user knows what's wrong.
        all_keys = list(db.keys())
        sample = all_keys[:10]
        sample_text = "\n".join(f"• {k}" for k in sample)
        
        msg = (
            f"❌ I couldn't find any entry matching **`{song_name}`** (checked Normal & Hard).\n\n"
            f"Here are some example keys from the database:\n{sample_text}"
        )
        await interaction.followup.send(msg, ephemeral=True)
    else:
        # Send all found embeds (up to 2)
        await interaction.followup.send(embeds=found_embeds)


@tree.command(
    name="find_gears",
    description="List which songs (by placement) include a gear name snippet.",
)
@app_commands.describe(
    name="Partial gear name to search for (case-insensitive).",
    placement="Which entry to check: 1 (best) or 2 (runner-up). Default: 1",
)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.allowed_installs(guilds=True, users=False)
async def find_gears(
    interaction: discord.Interaction,
    name: str,
    placement: app_commands.Range[int, 1, 2] = 1,
):
    await interaction.response.defer(thinking=True)

    query = (name or "").strip().lower()
    if not query:
        await interaction.followup.send(
            "❌ Provide a gear name snippet to search for.", ephemeral=True
        )
        return

    try:
        db = load_evolution_db()
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to load evolution_db.json: `{e}`", ephemeral=True)
        return

    if not db:
        await interaction.followup.send("⚠️ `evolution_db.json` is empty.", ephemeral=True)
        return

    matches: list[dict] = []
    for song_key, record in db.items():
        if not isinstance(record, dict):
            continue

        normalized, actual_placement = normalize_record_variant(record, placement)
        if actual_placement != placement:
            # Skip fallback entries so that placement filtering stays exact.
            continue

        gear_list = normalized.get("gear") or []
        minis_list = normalized.get("minis") or []
        if not gear_list:
            continue

        match_found = False
        for gear_name in gear_list:
            if isinstance(gear_name, str) and query in gear_name.lower():
                match_found = True
                break

        if match_found:
            matches.append(
                {
                    "song": song_key,
                    "score": normalized.get("score"),
                    "gear": gear_list,
                    "minis": minis_list,
                }
            )

    if not matches:
        await interaction.followup.send(
            f"No loadouts using `{name}` were found for placement {placement}.",
            ephemeral=True,
        )
        return

    matches.sort(key=lambda entry: str(entry.get("song", "")).lower())
    display_name = (name or "").strip()
    pages = build_gear_usage_embeds(matches, display_name, query, placement)

    if len(pages) == 1:
        await interaction.followup.send(embed=pages[0])
        return

    view = GearUsagePaginator(interaction.user.id, pages)
    message = await interaction.followup.send(embed=pages[0], view=view, wait=True)
    view.message = message


@tree.command(
    name="meta",
    description="Meta summary for an element: most common gear, minis, and gem allocation."
)
@app_commands.describe(color="Element color (e.g. Chill, Flow, Rush, Beat, Vibe)")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.allowed_installs(guilds=True, users=False)
async def meta(interaction: discord.Interaction, color: str):
    """
    /meta <color>
    Aggregates all entries with details.SelectedElement == color (case-insensitive),
    then shows:
      - most common full gear loadout
      - most common mini team
      - most common gem allocation for that color category (including FT/FF)
    """
    await interaction.response.defer(thinking=True)

    try:
        db = load_evolution_db()
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to load evolution_db.json: `{e}`", ephemeral=True)
        return

    if not db:
        await interaction.followup.send("⚠️ `evolution_db.json` is empty.", ephemeral=True)
        return

    summary = aggregate_color_category(db, color)
    if not summary:
        await interaction.followup.send(
            f"❌ No entries found with `SelectedElement = {color}`.\n"
            "Make sure you typed the element correctly (e.g., `Rush`, `Beat`, `Vibe`).",
            ephemeral=True,
        )
        return

    embed = build_meta_loadout_embed(summary)
    await interaction.followup.send(embed=embed)

# ==============================================================================
# 7. Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in Discord.env.")
    bot.run(DISCORD_TOKEN)
