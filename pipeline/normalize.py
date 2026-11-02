"""Normalization helpers — districts (§6.4), salary parsing, dedupe norm (§6.3).

Timezone is Asia/Hong_Kong everywhere (Invariant 6).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from .schema import (
    HK_TZ,
    DAY_TO_MONTH,
    HOUR_TO_MONTH,
    YEAR_TO_MONTH,
    collapse_ws,
)

# ------------------------------------------------------------------ districts

# 18 official HK districts (§6.4)
DISTRICTS = [
    "Central and Western",
    "Eastern",
    "Islands",
    "Kowloon City",
    "Kwai Tsing",
    "Kwun Tong",
    "North",
    "Sai Kung",
    "Sham Shui Po",
    "Sha Tin",
    "Southern",
    "Tai Po",
    "Tsuen Wan",
    "Tuen Mun",
    "Wan Chai",
    "Wong Tai Sin",
    "Yau Tsim Mong",
    "Yuen Long",
]

ANYWHERE_HINTS = (
    "anywhere in h.k.", "anywhere in hk", "any district", "hk-wide",
    "hong kong wide", "anywhere in hong kong", "hong kong", "hk wide",
)

# Non-HK geographic markers — if present in a raw location, no HK mapping is
# attempted (trap: "Central - United States" must NOT hit Central & Western).
NON_HK_MARKERS = (
    "united states", "united kingdom", "usa", "u.s.", "u.k.", "canada",
    "australia", "singapore", "china ", "china,", "shenzhen", "shanghai",
    "beijing", "overseas", "japan", "taiwan", "macau", "europe", "remote",
    "singapore,", "london", "new york", "tokyo",
)

# Initial alias table (§6.4) — agent-extended from observed data during B2.
# Map: lowercase substring observed in postings → official district.
# Longest-key match first. Kln. Peninsula is intentionally ABSENT: per §6.4
# it maps to *no* single district (districts[] stays empty, raw retained).
ALIAS_TABLE: dict[str, str] = {
    # central & western
    "central": "Central and Western",
    "sheung wan": "Central and Western",
    "admiralty": "Central and Western",
    "sai ying pun": "Central and Western",
    "kempeks": "Central and Western",  # observed misspelling, extended B2
    "kemper": "Central and Western",
    # wan chai
    "wan chai": "Wan Chai",
    "causeway bay": "Wan Chai",
    "tai hang": "Wan Chai",
    "happy valley": "Wan Chai",
    "wanchai": "Wan Chai",
    "cwbb": "Wan Chai",
    # eastern
    "north point": "Eastern",
    "quarry bay": "Eastern",
    "olympian heights": "Eastern",
    "sai wan ho": "Eastern",
    "shaukeiwan": "Eastern",
    "shau kei wan": "Eastern",
    "taikoo": "Eastern",
    "kowloon bay": "Kwun Tong",
    # kwun tong
    "kwun tong": "Kwun Tong",
    "kowloon bay": "Kwun Tong",
    "yau tong": "Kwun Tong",
    "lam tin": "Kwun Tong",
    "ngau tau kok": "Kwun Tong",
    "tol yau": "Kwun Tong",
    "kln bay": "Kowloon City",
    "kowloon city": "Kowloon City",
    "kowloon tong": "Kowloon City",
    "kln. tong": "Kowloon City",
    "kln tong": "Kowloon City",
    "hung hom": "Kowloon City",
    "to kwa wan": "Kowloon City",
    "to kwan wan": "Kowloon City",
    "san po kong": "Kowloon City",
    "sanpokong": "Kowloon City",
    "diamond hill": "Kowloon City",
    "kai tak": "Kowloon City",
    "ho man tin": "Kowloon City",
    # yau tsim mong
    "tsim sha tsui": "Yau Tsim Mong",
    "tst": "Yau Tsim Mong",
    "yau ma tei": "Yau Tsim Mong",
    "yaumatei": "Yau Tsim Mong",
    "mong kok": "Yau Tsim Mong",
    "mongkok": "Yau Tsim Mong",
    "jordan": "Yau Tsim Mong",
    "west kowloon": "Yau Tsim Mong",
    "kowloon station": "Yau Tsim Mong",
    "austin station": "Yau Tsim Mong",
    "olympic station": "Yau Tsim Mong",
    "olympic": "Yau Tsim Mong",
    # sham shui po
    "sham shui po": "Sham Shui Po",
    "shamshuipo": "Sham Shui Po",
    "cheung sha wan": "Sham Shui Po",
    "laichikok": "Sham Shui Po",
    "lai chi kok": "Sham Shui Po",
    "mei foo": "Sham Shui Po",
    "lai king": "Kwai Tsing",
    "shek kip mei": "Sham Shui Po",
    "kowloon city, kln": "Kowloon City",
    # kowloon city blocks
    "kowloon city": "Kowloon City",
    "kowloon city, kowloon": "Kowloon City",
    # sha tin
    "sha tin": "Sha Tin",
    "shatin": "Sha Tin",
    "tai wai": "Sha Tin",
    "fo tan": "Sha Tin",
    "ma on shan": "Sha Tin",
    "shek mun": "Sha Tin",
    "siu lek yuen": "Sha Tin",
    # tsuen wan
    "tsuen wan": "Tsuen Wan",
    "kwai chung": "Kwai Tsing",
    # kwai tsing
    "kwai tsing": "Kwai Tsing",
    "kwai fong": "Kwai Tsing",
    "tsing yi": "Kwai Tsing",
    # north
    "fanling": "North",
    "sheung shui": "North",
    "shataukok": "North",
    "tai po": "Tai Po",
    "tai wo": "Tai Po",
    "tai po market": "Tai Po",
    # sai kung
    "sai kung": "Sai Kung",
    "tseung kwan o": "Sai Kung",
    "tseung kwan o, hang hau": "Sai Kung",
    "hang hau": "Sai Kung",
    "tko": "Sai Kung",
    "clear water bay": "Sai Kung",
    "loi tung shuen": "Sai Kung",
    "yau tong east": "Kwun Tong",
    "leasehold" : "Kwun Tong",
    # islands
    "tung chung": "Islands",
    "airport": "Islands",
    "lantau": "Islands",
    "discovery bay": "Islands",
    "ma wan": "Islands",
    "yung shue wan": "Islands",
    "mai po": "Yuen Long",
    # tai po/n/yuen long
    "yuen long": "Yuen Long",
    "tien bo": "Yuen Long",
    "tin shui wai": "Yuen Long",
    "yuen long, tien bo": "Yuen Long",
    "tien bo, yuen long": "Yuen Long",
    "yuen long, tienbo": "Yuen Long",
    # tuen mun
    "tuen mun": "Tuen Mun",
    "tuen mun, sam shing": "Tuen Mun",
    "wong tai sin": "Wong Tai Sin",
    "wts": "Wong Tai Sin",
    "choi hung": "Wong Tai Sin",
    "kowloon wall": "Wong Tai Sin",
    # southern
    "southern": "Southern",
    "stanley": "Southern",
    "repulse bay": "Southern",
    "aberdeen": "Southern",
    "ap lei chau": "Southern",
    "wong chuk hang": "Southern",
    "wong chuk hang, ap lei chau": "Southern",
    "wong chuk hang, wong chuk hang": "Southern",
    "chung hom kok": "Southern",
    "shek o": "Southern",
    "cyberport": "Southern",
    # wan chai misc
    "causewaybay": "Wan Chai",
    "wellington st": "Central and Western",
    # island-east borderline
    "cha kwo ling": "Kwun Tong",
    # "its" style: full district name is its own alias
    "central and western": "Central and Western",
    "eastern": "Eastern",
    "kowloon city district": "Kowloon City",
    "kowloon city, kln": "Kowloon City",
    "kowloon city, kowloon, kln": "Kowloon City",
    # whole district names that differ from part-of-name aliases
    "kowloon": None,  # handled specially: ambiguous — mapped below
}

# "Kowloon" alone / "Kln" alone is too generic — per §6.4 it's not one of the
# official districts and there's no safe single mapping; leave unmapped.
GENERIC_KL_TOKENS = re.compile(r"^(kln|kowloon|k\.?l\.?n?)$/")

# clean up meaningless/typo entries from the dict above
ALIAS_TABLE.pop("kempeks", None)
ALIAS_TABLE.pop("kemper", None)
ALIAS_TABLE.pop("cwbb", None)
ALIAS_TABLE.pop("tol yau", None)
ALIAS_TABLE.pop("leasehold", None)
ALIAS_TABLE.pop("kowloon wall", None)
ALIAS_TABLE.pop("shataukok", None)
ALIAS_TABLE.pop("tien bo", None)
ALIAS_TABLE.pop("kowloon city district", None)
ALIAS_TABLE.pop("kowloon city, kln", None)
ALIAS_TABLE.pop("kowloon city, kowloon, kln", None)
ALIAS_TABLE.pop("kowloon city, kowloon", None)
ALIAS_TABLE.pop("tseung kwan o, hang hau", None)
ALIAS_TABLE.pop("wong chuk hang, ap lei chau", None)
ALIAS_TABLE.pop("wong chuk hang, wong chuk hang", None)
ALIAS_TABLE.pop("tuen mun, sam shing", None)
ALIAS_TABLE.pop("yuen long, tien bo", None)
ALIAS_TABLE.pop("tien bo, yuen long", None)
ALIAS_TABLE.pop("yuen long, tienbo", None)
ALIAS_TABLE.pop("kowloon", None)  # special-cased below (ambiguous)
ALIAS_TABLE.pop("ma wan", None)   # ambiguous (Ma Wan is Islands, but "ma" prefix hits)
ALIAS_TABLE.pop("airport", None)  # would false-match e.g. "Airport Station"; leave
ALIAS_TABLE.pop("mai po", None)

# longest-alias-first matching
_SORTED_ALIASES: list[tuple[str, str]] = sorted(
    ((k, v) for k, v in ALIAS_TABLE.items()),
    key=lambda kv: -len(kv[0]),
)


def map_districts(raw_locations: list[str]) -> tuple[list[str], bool, str]:
    """(districts, anywhere_in_hk, region_norm) from raw location strings.

    - Anywhere hints (§6.4 initial aliases) → ``anywhere_in_hk = True``.
    - ``Kln. Peninsula`` / generic ``Kln``/``Kowloon`` → no single district,
      ``districts[]`` stays empty, raw is retained by the caller.
    - Non-HK markers short-circuit (trap "Central - United States").
    - ``region_norm`` = first mapped district, else ``"unknown"``.
    """
    if not raw_locations:
        return [], False, "unknown"

    found: list[str] = []
    anywhere = False
    for raw in raw_locations:
        s = normalize_text(raw)
        low = s.casefold()
        # anywhere hints: exact-match the whole string, or explicit wide hints
        if low in ANYWHERE_HINTS or any(
            h in low for h in ("any district", "anywhere", "hk-wide", "hk wide")
        ):
            anywhere = True
            continue
        # trap: a non-HK marker anywhere in the string disqualifies it
        if any(m in low for m in NON_HK_MARKERS):
            continue
        if "kln. peninsula" in low:
            continue  # deliberately unmapped (§6.4)
        if GENERIC_KL_TOKENS.match(low.strip()):
            continue  # "Kln"/"Kowloon" alone: no single district
        for alias, district in _SORTED_ALIASES:
            if alias in low:
                if district not in found:
                    found.append(district)
                break  # longest alias wins per string

    districts = [d for d in DISTRICTS if d in found]
    region_norm = districts[0] if districts else "unknown"
    return districts, anywhere, region_norm


def normalize_text(s: str) -> str:
    """Unicode NFC + whitespace collapse, for location matching."""
    s = unicodedata.normalize("NFC", s)
    return collapse_ws(s)


# ------------------------------------------------------------------- salary

_SAL_NUMBER_RE = r"((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)([kK])?"

_PERIOD_WORDS: list[tuple[str, str]] = [
    (r"(?i)\bper\s*hour\b|\bhourly\b|/\s*hour|\b/hr\b|時薪", "hour"),
    (r"(?i)\bper\s*day\b|\bdaily\b|日薪", "day"),
    (r"(?i)\bper\s*month\b|\bmonthly\b|月薪", "month"),
    (r"(?i)\bper\s*annum\b|\bp\.a\.?\b|\bannual\b|\bper\s*year\b|\byearly\b|年薪", "year"),
]

_CUR = r"(?:HK\s?\$|\$)?"

_MULTI_SAL_RE = re.compile(
    _CUR + r"\s*" + _SAL_NUMBER_RE +
    r"(\s*(?:-|–|—|to|~)\s*" + _CUR + r"\s*" + _SAL_NUMBER_RE + r")?",
)

def parse_salary(
    raw: str | None,
) -> tuple[float | None, float | None, str | None]:
    """(salary_min, salary_max, salary_period) — all None on regex miss (§6.2).

    Returns *raw-number* values (i.e. per the original period), never the
    month equivalent (computed in ``schema.Job._month_equiv``).
    """
    if raw is None:
        return None, None, None
    s = normalize_text(raw)

    period = None
    for pat, p in _PERIOD_WORDS:
        if re.search(pat, s):
            period = p
            break

    if period is None and re.search(r"[-–—~]?\s*(?:\d)", s):
        # HK default: assume monthly when numbers carry no stated period
        # (documented constant; HK Gov quickview "$15,000" == monthly).
        period = "month"

    m = _MULTI_SAL_RE.search(s)
    if not m:
        return None, None, None

    def _num(numstr: str, suffix: str) -> float:
        v = float(numstr.replace(",", ""))
        if suffix and suffix.lower() == "k":
            v *= 1_000
        return v

    lo = _num(m.group(1), m.group(2))
    hi = None
    if m.group(3):
        hi = _num(m.group(4), m.group(5))
        if hi is not None and hi < lo:
            lo, hi = hi, lo

    # sanity guard: wages under 4/hour or over 800/month are nonsense in HKD
    # (skip — data-driven threshold would need observation; left permissive)
    if lo > 1_000_000 and period != "year":
        return None, None, None  # likely a misparsed value
    return lo, hi, period


# --------------------------------------------------------------- posted-date

_DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%b %d, %Y", "%d-%m-%Y",
    "%Y%m%d",
)


def parse_posted_date(raw: str | None) -> str | None:
    """ISO date (Asia/Hong_Kong) from a published raw date string, or None."""
    if raw is None:
        return None
    s = normalize_text(raw)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


# -------------------------------------------------------------- dedupe norm

_SUFFIXES = {"ltd", "limited", "co", "company", "inc", "llc", "hk",
             "hong kong"}
_PUNCT_KEEP = re.compile(r"[^\w\s&]", re.UNICODE)


def norm_operand(s: str | None) -> str:
    """§6.3 dedupe ``norm()``: casefold, collapse ws, strip punctuation
    except ``&``, drop company suffixes."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", s.casefold())
    s = collapse_ws(s)
    tokens = _PUNCT_KEEP.sub(" ", s).split()
    tokens = [t for t in tokens if t not in _SUFFIXES]
    return " ".join(tokens)
