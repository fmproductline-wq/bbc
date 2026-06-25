"""
Numerology & Astrology Agent
============================
Combines:
  • Three calendar systems: Julian Day Number, March-21-as-Day-1, Jan-1 standard
  • Pythagorean numerology (name + life path numbers)
  • Tropical natal chart (Sun, Moon, planets, Ascendant, Midheaven) via ephem
  • Astrocartography planetary lines (MC / IC / AC / DC)
  • Compatibility scoring for people, brands, companies
  • Claude AI interpretation of every reading
"""
from __future__ import annotations

import math
import os
import re
from datetime import date, datetime, timezone
from typing import Optional

# ── optional heavy imports (fail gracefully so the app still boots) ───────────
try:
    import ephem  # type: ignore
    _EPHEM_OK = True
except ImportError:
    _EPHEM_OK = False

try:
    import anthropic  # type: ignore
    _ANTHROPIC_OK = True
except ImportError:
    _ANTHROPIC_OK = False


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars",
           "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

PLANET_SYMBOLS = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀",
    "Mars": "♂", "Jupiter": "♃", "Saturn": "♄",
    "Uranus": "♅", "Neptune": "♆", "Pluto": "♇",
}

PYTHAGOREAN = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9,
    "S": 1, "T": 2, "U": 3, "V": 4, "W": 5, "X": 6, "Y": 7, "Z": 8,
}

VOWELS = set("AEIOU")

NUMEROLOGY_MEANINGS: dict[int, str] = {
    1: "Leadership, independence, originality, pioneering spirit",
    2: "Partnership, diplomacy, balance, sensitivity, cooperation",
    3: "Creativity, self-expression, joy, communication, optimism",
    4: "Stability, discipline, hard work, practicality, foundation",
    5: "Freedom, adventure, change, versatility, progressive thinking",
    6: "Nurturing, responsibility, home, family, harmony, service",
    7: "Spirituality, introspection, wisdom, analysis, mysticism",
    8: "Power, abundance, authority, ambition, material success",
    9: "Compassion, humanitarianism, completion, universal love",
    11: "Master Number — Intuition, spiritual illumination, inspiration",
    22: "Master Number — Master Builder, visionary pragmatism, manifestation",
    33: "Master Number — Master Teacher, unconditional love, healing",
}

SIGN_MEANINGS: dict[str, str] = {
    "Aries": "Bold, pioneering, competitive, action-oriented",
    "Taurus": "Grounded, sensual, patient, determined, love of beauty",
    "Gemini": "Curious, adaptable, witty, communicative, dual-natured",
    "Cancer": "Nurturing, intuitive, emotional, protective, home-loving",
    "Leo": "Confident, generous, creative, dramatic, leadership",
    "Virgo": "Analytical, precise, helpful, health-conscious, practical",
    "Libra": "Balanced, charming, fair, social, aesthetically inclined",
    "Scorpio": "Intense, perceptive, transformative, passionate, secretive",
    "Sagittarius": "Adventurous, philosophical, optimistic, freedom-loving",
    "Capricorn": "Ambitious, disciplined, responsible, strategic, patient",
    "Aquarius": "Innovative, humanitarian, independent, visionary, eccentric",
    "Pisces": "Empathic, creative, spiritual, compassionate, dreamy",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Calendar Systems
# ═══════════════════════════════════════════════════════════════════════════════

def julian_day_number(d: date) -> int:
    """
    Compute the Julian Day Number (JDN) — the continuous integer day count
    since noon Universal Time, Monday, January 1, 4713 BC (Julian calendar).
    Uses the standard algorithm valid for all Gregorian dates.
    """
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    jdn = d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn


def march21_day_number(d: date) -> int:
    """
    Day number where March 21 = Day 1.
    Models the astrological / vernal-equinox new year.
    Returns 1–365 (or 366 in leap years).
    """
    year = d.year
    new_year = date(year, 3, 21)
    if d < new_year:
        # date falls before this year's March 21 → use previous year's cycle
        new_year = date(year - 1, 3, 21)
    return (d - new_year).days + 1


def jan1_day_number(d: date) -> int:
    """Standard day of year (Jan 1 = 1)."""
    return d.timetuple().tm_yday


def numerology_day_reduce(n: int) -> int:
    """
    Reduce a day-of-year count to a single digit (1–9) or Master Number (11/22/33).
    """
    # Sum all digits repeatedly until ≤ 9, but preserve master numbers
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n


# ═══════════════════════════════════════════════════════════════════════════════
# Numerology Core
# ═══════════════════════════════════════════════════════════════════════════════

def _digit_reduce(n: int) -> int:
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n


def life_path_number(d: date) -> int:
    """Classic life-path: sum day + month + year, then reduce."""
    total = d.day + d.month + sum(int(c) for c in str(d.year))
    return _digit_reduce(total)


def name_to_digits(name: str) -> list[int]:
    clean = re.sub(r"[^A-Z]", "", name.upper())
    return [PYTHAGOREAN[c] for c in clean if c in PYTHAGOREAN]


def expression_number(full_name: str) -> int:
    """All letters of the full birth name."""
    return _digit_reduce(sum(name_to_digits(full_name)))


def soul_urge_number(full_name: str) -> int:
    """Vowels only."""
    clean = re.sub(r"[^A-Z]", "", full_name.upper())
    vals = [PYTHAGOREAN[c] for c in clean if c in VOWELS and c in PYTHAGOREAN]
    return _digit_reduce(sum(vals)) if vals else 0


def personality_number(full_name: str) -> int:
    """Consonants only."""
    clean = re.sub(r"[^A-Z]", "", full_name.upper())
    vals = [PYTHAGOREAN[c] for c in clean if c not in VOWELS and c in PYTHAGOREAN]
    return _digit_reduce(sum(vals)) if vals else 0


def birthday_number(d: date) -> int:
    """The raw day of birth reduced to a single/master digit."""
    return _digit_reduce(d.day)


def personal_year_number(d: date, current_year: int | None = None) -> int:
    """Personal Year = (month + day of birth) + current year, reduced."""
    cy = current_year or date.today().year
    total = d.day + d.month + sum(int(c) for c in str(cy))
    return _digit_reduce(total)


def full_numerology_profile(full_name: str, birth_date: date) -> dict:
    jdn   = julian_day_number(birth_date)
    m21n  = march21_day_number(birth_date)
    j1n   = jan1_day_number(birth_date)
    return {
        "life_path":         life_path_number(birth_date),
        "expression":        expression_number(full_name),
        "soul_urge":         soul_urge_number(full_name),
        "personality":       personality_number(full_name),
        "birthday_num":      birthday_number(birth_date),
        "personal_year":     personal_year_number(birth_date),
        "julian_day_number": jdn,
        "march21_day":       m21n,
        "march21_reduced":   numerology_day_reduce(m21n),
        "jan1_day":          j1n,
        "jan1_reduced":      numerology_day_reduce(j1n),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tropical Natal Chart  (requires ephem)
# ═══════════════════════════════════════════════════════════════════════════════

def _ecliptic_lon(body, d: date, t: str = "12:00", lat: float = 0.0, lon: float = 0.0) -> float:
    """Return tropical ecliptic longitude in degrees (0–360)."""
    obs = ephem.Observer()
    obs.date = f"{d.year}/{d.month}/{d.day} {t}"
    obs.lat  = str(lat)
    obs.lon  = str(lon)
    obs.elevation = 0
    obs.pressure  = 0  # no atmospheric refraction

    body.compute(obs)
    ecl = ephem.Ecliptic(body, epoch=obs.date)
    return math.degrees(float(ecl.lon)) % 360


def _sign_and_degree(lon: float) -> tuple[str, float]:
    idx = int(lon / 30) % 12
    deg = lon % 30
    return ZODIAC_SIGNS[idx], deg


def _ascendant(obs: "ephem.Observer") -> float:
    """Tropical Ascendant longitude in degrees."""
    lst   = float(obs.sidereal_time())  # radians
    eps_r = math.radians(23.4397)       # mean obliquity of ecliptic
    lat_r = float(obs.lat)
    # RAMC = Right Ascension of Midheaven (in radians)
    ramc = lst  # LST in radians

    # Ascendant formula (Placidus):
    # tan(Asc) = -cos(RAMC) / (sin(eps)*tan(lat) + cos(eps)*sin(RAMC))
    num = -math.cos(ramc)
    den = math.sin(eps_r) * math.tan(lat_r) + math.cos(eps_r) * math.sin(ramc)
    asc = math.degrees(math.atan2(num, den)) % 360
    # Ascendant must be on the eastern horizon; adjust quadrant
    if 0 <= ramc < math.pi:
        asc = (asc + 180) % 360
    return asc


def _midheaven(obs: "ephem.Observer") -> float:
    """Tropical Midheaven (MC) longitude in degrees."""
    lst  = float(obs.sidereal_time())
    eps_r = math.radians(23.4397)
    # MC formula: tan(MC) = tan(RAMC) / cos(eps)
    mc = math.degrees(math.atan2(math.tan(lst), math.cos(eps_r))) % 360
    if lst > math.pi:
        mc = (mc + 180) % 360
    return mc


def calculate_natal_chart(
    birth_date: date,
    birth_time: str = "12:00",
    lat: float = 0.0,
    lon: float = 0.0,
) -> dict:
    """
    Compute a full tropical natal chart.
    birth_time: "HH:MM" in local time (user must convert to UTC themselves,
                or pass birth_time="12:00" for solar chart if time is unknown).
    lat/lon: birth location in decimal degrees (S/W negative).
    Returns a dict with planetary positions, Asc, MC, and house data.
    """
    if not _EPHEM_OK:
        return {"error": "ephem library not installed — run: pip install ephem"}

    obs = ephem.Observer()
    obs.date = f"{birth_date.year}/{birth_date.month}/{birth_date.day} {birth_time}"
    obs.lat  = str(lat)
    obs.lon  = str(lon)
    obs.pressure = 0

    planet_bodies = {
        "Sun":     ephem.Sun(),
        "Moon":    ephem.Moon(),
        "Mercury": ephem.Mercury(),
        "Venus":   ephem.Venus(),
        "Mars":    ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn":  ephem.Saturn(),
        "Uranus":  ephem.Uranus(),
        "Neptune": ephem.Neptune(),
        "Pluto":   ephem.Pluto(),
    }

    positions: dict[str, dict] = {}
    for name, body in planet_bodies.items():
        try:
            body.compute(obs)
            ecl  = ephem.Ecliptic(body, epoch=obs.date)
            lon_deg = math.degrees(float(ecl.lon)) % 360
            sign, deg = _sign_and_degree(lon_deg)
            positions[name] = {
                "longitude": round(lon_deg, 4),
                "sign":      sign,
                "degree":    round(deg, 2),
                "symbol":    PLANET_SYMBOLS.get(name, ""),
            }
        except Exception as e:
            positions[name] = {"error": str(e)}

    try:
        asc_lon = _ascendant(obs)
        mc_lon  = _midheaven(obs)
        asc_sign, asc_deg = _sign_and_degree(asc_lon)
        mc_sign,  mc_deg  = _sign_and_degree(mc_lon)
    except Exception:
        asc_lon, asc_sign, asc_deg = 0.0, "Unknown", 0.0
        mc_lon,  mc_sign,  mc_deg  = 0.0, "Unknown", 0.0

    # Whole-sign house cusps (simple: Asc sign = House 1)
    asc_sign_idx = ZODIAC_SIGNS.index(asc_sign) if asc_sign in ZODIAC_SIGNS else 0
    houses = {
        i + 1: ZODIAC_SIGNS[(asc_sign_idx + i) % 12]
        for i in range(12)
    }

    return {
        "planets":    positions,
        "ascendant":  {"longitude": round(asc_lon, 4), "sign": asc_sign, "degree": round(asc_deg, 2)},
        "midheaven":  {"longitude": round(mc_lon,  4), "sign": mc_sign,  "degree": round(mc_deg, 2)},
        "houses":     houses,
        "date":       str(birth_date),
        "time":       birth_time,
        "lat":        lat,
        "lon":        lon,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Astrocartography  (requires ephem)
# ═══════════════════════════════════════════════════════════════════════════════

# Simplified coast/city lookup for nearby-city labelling
MAJOR_CITIES = [
    ("New York",      40.71, -74.01),
    ("Los Angeles",   34.05, -118.24),
    ("Chicago",       41.88, -87.63),
    ("Toronto",       43.65, -79.38),
    ("London",        51.51,  -0.13),
    ("Paris",         48.85,   2.35),
    ("Berlin",        52.52,  13.40),
    ("Rome",          41.90,  12.50),
    ("Madrid",        40.42,  -3.70),
    ("Moscow",        55.75,  37.62),
    ("Dubai",         25.20,  55.27),
    ("Mumbai",        19.08,  72.88),
    ("Delhi",         28.61,  77.21),
    ("Beijing",       39.91, 116.39),
    ("Shanghai",      31.23, 121.47),
    ("Tokyo",         35.69, 139.69),
    ("Seoul",         37.57, 126.98),
    ("Singapore",      1.35, 103.82),
    ("Sydney",       -33.87, 151.21),
    ("Melbourne",    -37.81, 144.96),
    ("Johannesburg", -26.20,  28.04),
    ("Cairo",         30.05,  31.24),
    ("Lagos",          6.52,   3.38),
    ("Nairobi",       -1.29,  36.82),
    ("São Paulo",    -23.55, -46.63),
    ("Buenos Aires", -34.60, -58.38),
    ("Mexico City",   19.43, -99.13),
    ("Miami",         25.77, -80.19),
    ("Vancouver",     49.25, -123.12),
    ("Amsterdam",     52.37,   4.90),
    ("Stockholm",     59.33,  18.07),
    ("Athens",        37.98,  23.73),
    ("Istanbul",      41.01,  28.95),
    ("Tel Aviv",      32.09,  34.79),
    ("Bangkok",       13.76, 100.50),
    ("Jakarta",       -6.21, 106.85),
    ("Karachi",       24.86,  67.01),
    ("Lahore",        31.55,  74.34),
    ("Bogotá",         4.71, -74.07),
    ("Lima",          -12.05, -77.04),
    ("Casablanca",    33.57,  -7.59),
    ("Accra",          5.56,  -0.20),
    ("Addis Ababa",    9.03,  38.74),
    ("Riyadh",        24.69,  46.72),
    ("Kuala Lumpur",   3.14, 101.69),
    ("Manila",        14.60, 120.98),
    ("Ho Chi Minh",   10.82, 106.63),
    ("Dhaka",         23.81,  90.41),
    ("Kathmandu",     27.70,  85.32),
    ("Colombo",        6.93,  79.85),
]


def _greenwich_sidereal_time(obs_date: "ephem.Date") -> float:
    """Return Greenwich Sidereal Time in radians for a given ephem Date."""
    obs_gw = ephem.Observer()
    obs_gw.date = obs_date
    obs_gw.lat = "0"
    obs_gw.lon = "0"
    obs_gw.pressure = 0
    return float(obs_gw.sidereal_time())


def _ra_to_geo_longitude(ra_rad: float, obs_date: "ephem.Date") -> float:
    """Convert RA to geographic longitude for Midheaven (MC line)."""
    gst = _greenwich_sidereal_time(obs_date)
    geo_lon = math.degrees(ra_rad - gst) % 360
    if geo_lon > 180:
        geo_lon -= 360
    return geo_lon


def calculate_astrocartography(
    birth_date: date,
    birth_time: str = "12:00",
    lat_step: float = 5.0,
) -> dict[str, dict]:
    """
    Calculate astrocartography planetary lines.
    Returns a dict keyed by planet name, each with:
      mc_lon   — longitude of MC line (±180)
      ic_lon   — opposite of MC line
      ac_lons  — list of (lat, lon) points for the AC (rising) curve
      dc_lons  — list of (lat, lon) points for the DC (setting) curve
    """
    if not _EPHEM_OK:
        return {}

    obs_date = ephem.Date(f"{birth_date.year}/{birth_date.month}/{birth_date.day} {birth_time}")

    planet_bodies = {
        "Sun":     ephem.Sun(),
        "Moon":    ephem.Moon(),
        "Mercury": ephem.Mercury(),
        "Venus":   ephem.Venus(),
        "Mars":    ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn":  ephem.Saturn(),
        "Uranus":  ephem.Uranus(),
        "Neptune": ephem.Neptune(),
        "Pluto":   ephem.Pluto(),
    }

    result = {}
    for name, body in planet_bodies.items():
        try:
            body.compute(obs_date)
            ra  = float(body.ra)   # radians
            dec = float(body.dec)  # radians

            # ── MC line: geographic longitude where body culminates ───────────
            mc_lon = _ra_to_geo_longitude(ra, obs_date)
            ic_lon = (mc_lon + 180) % 360
            if ic_lon > 180:
                ic_lon -= 360

            # ── AC / DC curves: where body rises / sets at each latitude ─────
            # Rising: Hour Angle H = -arccos(-tan(δ)·tan(φ))
            # Geographic longitude of rising point = LST - H (in degrees)
            gst_deg = math.degrees(_greenwich_sidereal_time(obs_date))
            ra_deg  = math.degrees(ra)
            dec_r   = dec

            ac_pts, dc_pts = [], []
            for lat in range(-80, 81, int(lat_step)):
                lat_r = math.radians(lat)
                cos_h = -math.tan(dec_r) * math.tan(lat_r)
                if abs(cos_h) > 1:
                    continue  # circumpolar or never rises
                h_deg = math.degrees(math.acos(cos_h))
                # AC lon: body is on the Ascendant (rising)
                ac_geolon = (ra_deg - gst_deg - h_deg) % 360
                if ac_geolon > 180: ac_geolon -= 360
                # DC lon: body is on the Descendant (setting)
                dc_geolon = (ra_deg - gst_deg + h_deg) % 360
                if dc_geolon > 180: dc_geolon -= 360
                ac_pts.append((lat, round(ac_geolon, 2)))
                dc_pts.append((lat, round(dc_geolon, 2)))

            result[name] = {
                "mc_lon":  round(mc_lon, 2),
                "ic_lon":  round(ic_lon, 2),
                "ac_pts":  ac_pts,
                "dc_pts":  dc_pts,
                "symbol":  PLANET_SYMBOLS.get(name, ""),
            }
        except Exception:
            result[name] = {}

    return result


def find_cities_on_lines(
    astrocarto: dict,
    threshold_deg: float = 4.0,
    lat_step: int = 5,
) -> dict[str, list[str]]:
    """
    For each planet find major cities within threshold_deg of any line.
    Returns {planet: [city_descriptions]}.
    """
    city_results: dict[str, list[str]] = {}
    for planet, data in astrocarto.items():
        hits = []
        mc = data.get("mc_lon")
        ic = data.get("ic_lon")
        ac_pts = {lat: lon for lat, lon in data.get("ac_pts", [])}
        dc_pts = {lat: lon for lat, lon in data.get("dc_pts", [])}

        for city_name, clat, clon in MAJOR_CITIES:
            tags = []
            # MC/IC are vertical lines — compare longitude only
            if mc is not None and abs(clon - mc) < threshold_deg:
                tags.append("MC")
            if ic is not None and abs(clon - ic) < threshold_deg:
                tags.append("IC")
            # AC/DC — snap city latitude to nearest grid point and neighbours
            nearest = round(clat / lat_step) * lat_step
            for lat_key in [nearest, nearest - lat_step, nearest + lat_step]:
                if lat_key in ac_pts and abs(clon - ac_pts[lat_key]) < threshold_deg:
                    tags.append("AC")
                    break
            for lat_key in [nearest, nearest - lat_step, nearest + lat_step]:
                if lat_key in dc_pts and abs(clon - dc_pts[lat_key]) < threshold_deg:
                    tags.append("DC")
                    break
            if tags:
                hits.append(f"{city_name} ({'/'.join(dict.fromkeys(tags))})")
        city_results[planet] = hits
    return city_results


# ═══════════════════════════════════════════════════════════════════════════════
# Compatibility
# ═══════════════════════════════════════════════════════════════════════════════

def compatibility_score(
    name1: str, date1: date,
    name2: str, date2: date,
) -> dict:
    """
    Numerological + astrological compatibility between two people or entities.
    """
    p1 = full_numerology_profile(name1, date1)
    p2 = full_numerology_profile(name2, date2)

    # Life-path harmony matrix (simplified harmonic relationships)
    HARMONICS = {
        frozenset({1, 5}): 90, frozenset({1, 9}): 85, frozenset({2, 6}): 92,
        frozenset({2, 8}): 80, frozenset({3, 9}): 88, frozenset({3, 6}): 82,
        frozenset({4, 8}): 87, frozenset({1, 2}): 70, frozenset({5, 9}): 85,
        frozenset({6, 9}): 78, frozenset({7, 11}): 90, frozenset({4, 22}): 95,
    }
    lp1, lp2 = p1["life_path"], p2["life_path"]
    base = HARMONICS.get(frozenset({lp1, lp2}), 50 + abs(lp1 - lp2) * 2)
    base = max(30, min(98, base))

    # Expression compatibility
    exp_diff = abs(p1["expression"] - p2["expression"])
    exp_bonus = max(0, 10 - exp_diff * 2)

    # Soul urge resonance
    soul_diff = abs(p1["soul_urge"] - p2["soul_urge"])
    soul_bonus = max(0, 8 - soul_diff * 1.5)

    # Julian day synergy
    jdn_diff = abs(p1["julian_day_number"] - p2["julian_day_number"]) % 365
    jdn_score = 10 if jdn_diff < 30 else 5 if jdn_diff < 90 else 0

    total = min(99, base + exp_bonus + soul_bonus + jdn_score)

    return {
        "score":          round(total),
        "person1_lp":     lp1,
        "person2_lp":     lp2,
        "expression_gap": exp_diff,
        "soul_gap":       soul_diff,
        "jdn_proximity":  jdn_diff,
        "numerology_1":   p1,
        "numerology_2":   p2,
        "summary":        _compatibility_label(total),
    }


def _compatibility_label(score: int) -> str:
    if score >= 90: return "Exceptional — natural soul mates or ideal partners"
    if score >= 80: return "Excellent — strong alignment and mutual support"
    if score >= 70: return "Good — solid connection with minor friction areas"
    if score >= 60: return "Moderate — meaningful bond; requires communication"
    if score >= 50: return "Challenging — opposites; growth through tension"
    return "Difficult — significant karmic lessons ahead"


# ═══════════════════════════════════════════════════════════════════════════════
# AI Interpretation via Claude
# ═══════════════════════════════════════════════════════════════════════════════

def _build_numerology_prompt(
    full_name: str,
    birth_date: date,
    profile: dict,
    natal: dict | None = None,
    astrocarto_cities: dict | None = None,
    mode: str = "full",
) -> str:
    lines = [
        f"You are an expert numerologist and tropical astrologer. Give a warm, insightful, "
        f"and actionable reading. Speak directly to {full_name.split()[0]}.",
        "",
        f"=== SUBJECT ===",
        f"Name: {full_name}",
        f"Birth date: {birth_date.strftime('%B %d, %Y')}",
        "",
        f"=== THREE-CALENDAR BIRTHDAY NUMBERS ===",
        f"Julian Day Number (JDN):    {profile['julian_day_number']}",
        f"March-21 Day (Day 1=Mar21): {profile['march21_day']} → numerology reduced: {profile['march21_reduced']}",
        f"Jan-1 Day (standard DOY):   {profile['jan1_day']} → numerology reduced: {profile['jan1_reduced']}",
        "",
        f"=== NUMEROLOGY CORE NUMBERS ===",
        f"Life Path:      {profile['life_path']} — {NUMEROLOGY_MEANINGS.get(profile['life_path'], '')}",
        f"Expression:     {profile['expression']} — {NUMEROLOGY_MEANINGS.get(profile['expression'], '')}",
        f"Soul Urge:      {profile['soul_urge']} — {NUMEROLOGY_MEANINGS.get(profile['soul_urge'], '')}",
        f"Personality:    {profile['personality']} — {NUMEROLOGY_MEANINGS.get(profile['personality'], '')}",
        f"Birthday #:     {profile['birthday_num']}",
        f"Personal Year:  {profile['personal_year']} (current year cycle)",
    ]

    if natal and "planets" in natal:
        lines += [
            "",
            "=== TROPICAL NATAL CHART ===",
            f"Ascendant: {natal['ascendant']['sign']} {natal['ascendant']['degree']:.1f}°",
            f"Midheaven: {natal['midheaven']['sign']} {natal['midheaven']['degree']:.1f}°",
        ]
        for pname, pdata in natal["planets"].items():
            if "sign" in pdata:
                sym = pdata.get("symbol", "")
                lines.append(
                    f"{sym} {pname:8}: {pdata['sign']:13} {pdata['degree']:.1f}°"
                )

    if astrocarto_cities:
        lines += ["", "=== ASTROCARTOGRAPHY — KEY CITIES ON POWER LINES ==="]
        for planet, cities in astrocarto_cities.items():
            if cities:
                lines.append(f"{planet}: {', '.join(cities[:5])}")

    if mode == "full":
        lines += [
            "",
            "Please provide:",
            "1. A 2-3 paragraph overall life reading weaving ALL THREE birthday calendar numbers.",
            "2. What each core numerology number reveals about their path, gifts, and challenges.",
            "3. Key astrological themes from the natal chart (if provided).",
            "4. Top 3–5 astrocartography power cities (if provided) and what they offer.",
            "5. Practical advice for the current Personal Year cycle.",
            "Keep the tone warm, empowering, and specific. Avoid generic horoscope language.",
        ]
    elif mode == "quick":
        lines += [
            "",
            "Give a concise 3-5 sentence highlight reading covering the most important insights.",
        ]

    return "\n".join(lines)


def _build_compatibility_prompt(
    name1: str, date1: date,
    name2: str, date2: date,
    compat: dict,
    entity_type: str = "people",
) -> str:
    p1 = compat["numerology_1"]
    p2 = compat["numerology_2"]
    return "\n".join([
        f"You are an expert numerologist. Analyze the compatibility between these two {entity_type}.",
        "",
        f"=== {name1.upper()} ===",
        f"Birth/founding: {date1.strftime('%B %d, %Y')}",
        f"Life Path: {p1['life_path']}  |  Expression: {p1['expression']}  |  Soul Urge: {p1['soul_urge']}",
        f"Julian Day Number: {p1['julian_day_number']}",
        f"March-21 Day Num: {p1['march21_day']} (reduced: {p1['march21_reduced']})",
        f"Jan-1 Day Number: {p1['jan1_day']} (reduced: {p1['jan1_reduced']})",
        "",
        f"=== {name2.upper()} ===",
        f"Birth/founding: {date2.strftime('%B %d, %Y')}",
        f"Life Path: {p2['life_path']}  |  Expression: {p2['expression']}  |  Soul Urge: {p2['soul_urge']}",
        f"Julian Day Number: {p2['julian_day_number']}",
        f"March-21 Day Num: {p2['march21_day']} (reduced: {p2['march21_reduced']})",
        f"Jan-1 Day Number: {p2['jan1_day']} (reduced: {p2['jan1_reduced']})",
        "",
        f"=== COMPATIBILITY SCORE: {compat['score']}/100 — {compat['summary']} ===",
        f"Life Path resonance: {compat['person1_lp']} ↔ {compat['person2_lp']}",
        f"Expression gap: {compat['expression_gap']}  |  Soul gap: {compat['soul_gap']}",
        f"Julian Day proximity: {compat['jdn_proximity']} days",
        "",
        "Please provide:",
        "1. An overall compatibility reading (2 paragraphs).",
        "2. Strengths of this pairing based on numerology.",
        "3. Potential friction areas and how to navigate them.",
        "4. If these are companies/brands — what business synergies exist.",
        "5. A final actionable recommendation.",
    ])


def ai_interpret(
    prompt: str,
    api_key: str | None = None,
    max_tokens: int = 1200,
) -> str:
    """Send prompt to Claude and return the interpretation text."""
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return (
            "[AI reading requires an Anthropic API key.\n"
            "Set ANTHROPIC_API_KEY in your environment or Settings tab.]"
        )
    if not _ANTHROPIC_OK:
        return "[anthropic Python package not installed — run: pip install anthropic]"

    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"[AI error: {e}]"


# ═══════════════════════════════════════════════════════════════════════════════
# High-level public functions used by the UI
# ═══════════════════════════════════════════════════════════════════════════════

def full_reading(
    full_name: str,
    birth_date: date,
    birth_time: str = "12:00",
    birth_lat: float = 0.0,
    birth_lon: float = 0.0,
    api_key: str | None = None,
) -> dict:
    """
    Complete reading: numerology + natal chart + astrocartography + AI text.
    Returns a single dict with all data and the AI narrative.
    """
    profile  = full_numerology_profile(full_name, birth_date)
    natal    = calculate_natal_chart(birth_date, birth_time, birth_lat, birth_lon)
    astro    = calculate_astrocartography(birth_date, birth_time)
    cities   = find_cities_on_lines(astro)
    prompt   = _build_numerology_prompt(full_name, birth_date, profile, natal, cities, mode="full")
    ai_text  = ai_interpret(prompt, api_key=api_key)
    return {
        "profile":       profile,
        "natal_chart":   natal,
        "astrocartography": astro,
        "city_lines":    cities,
        "ai_reading":    ai_text,
    }


def compatibility_reading(
    name1: str, date1: date,
    name2: str, date2: date,
    entity_type: str = "people",
    api_key: str | None = None,
) -> dict:
    compat  = compatibility_score(name1, date1, name2, date2)
    prompt  = _build_compatibility_prompt(name1, date1, name2, date2, compat, entity_type)
    ai_text = ai_interpret(prompt, api_key=api_key)
    compat["ai_reading"] = ai_text
    return compat
