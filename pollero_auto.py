"""
Pollero Automatizado - Mundial 2026
====================================
Fuentes de datos:
  - ELO: eloratings.net  (scraping, se actualiza diariamente)
  - Cuotas: The Odds API  (free tier: 500 req/mes)
             -> Registrate en https://the-odds-api.com y pega tu key abajo
  - xG: opcional, se puede ingresar a mano en el CLI

Uso:
    python pollero_auto.py

La primera vez pedira tu API key de The Odds API.
Puedes pegarla en la variable ODDS_API_KEY de abajo para no ingresarla cada vez.
"""

import csv
import json
import math
import sys
import urllib.request
import urllib.parse

# Mapeo de codigos eloratings.net -> nombres de selecciones
_CODE_TO_NAME = {
    "AF": "Afghanistan", "AL": "Albania", "DZ": "Algeria", "AD": "Andorra",
    "AO": "Angola", "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia",
    "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan", "BS": "Bahamas",
    "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus",
    "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BT": "Bhutan",
    "BO": "Bolivia", "BA": "Bosnia-Herzegovina", "BW": "Botswana", "BR": "Brazil",
    "BN": "Brunei", "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi",
    "CV": "Cape Verde", "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada",
    "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CO": "Colombia", "KM": "Comoros", "CG": "Congo", "CD": "DR Congo",
    "CR": "Costa Rica", "CI": "Ivory Coast", "HR": "Croatia", "CU": "Cuba",
    "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark", "DJ": "Djibouti",
    "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador", "EG": "Egypt",
    "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia",
    "SZ": "Eswatini", "ET": "Ethiopia", "FJ": "Fiji", "FI": "Finland",
    "FR": "France", "GA": "Gabon", "GM": "Gambia", "GE": "Georgia",
    "DE": "Germany", "GH": "Ghana", "GR": "Greece", "GD": "Grenada",
    "GT": "Guatemala", "GN": "Guinea", "GW": "Guinea-Bissau", "GY": "Guyana",
    "HT": "Haiti", "HN": "Honduras", "HU": "Hungary", "IS": "Iceland",
    "IN": "India", "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq",
    "IE": "Republic of Ireland", "IL": "Israel", "IT": "Italy", "JM": "Jamaica",
    "JP": "Japan", "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya",
    "KI": "Kiribati", "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos",
    "LV": "Latvia", "LB": "Lebanon", "LS": "Lesotho", "LR": "Liberia",
    "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg",
    "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia", "MV": "Maldives",
    "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands", "MR": "Mauritania",
    "MU": "Mauritius", "MX": "Mexico", "FM": "Micronesia", "MD": "Moldova",
    "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro", "MA": "Morocco",
    "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru",
    "NP": "Nepal", "NL": "Netherlands", "NZ": "New Zealand", "NI": "Nicaragua",
    "NE": "Niger", "NG": "Nigeria", "MK": "North Macedonia", "NO": "Norway",
    "OM": "Oman", "PK": "Pakistan", "PW": "Palau", "PA": "Panama",
    "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru", "PH": "Philippines",
    "PL": "Poland", "PT": "Portugal", "QA": "Qatar", "RO": "Romania",
    "RU": "Russia", "RW": "Rwanda", "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia", "VC": "Saint Vincent and the Grenadines", "WS": "Samoa",
    "SM": "San Marino", "ST": "Sao Tome and Principe", "SA": "Saudi Arabia",
    "SN": "Senegal", "RS": "Serbia", "SL": "Sierra Leone", "SG": "Singapore",
    "SK": "Slovakia", "SI": "Slovenia", "SB": "Solomon Islands", "SO": "Somalia",
    "ZA": "South Africa", "SS": "South Sudan", "ES": "Spain", "LK": "Sri Lanka",
    "SD": "Sudan", "SR": "Suriname", "SE": "Sweden", "CH": "Switzerland",
    "SY": "Syria", "TW": "Chinese Taipei", "TJ": "Tajikistan", "TZ": "Tanzania",
    "TH": "Thailand", "TL": "Timor-Leste", "TG": "Togo", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TN": "Tunisia", "TR": "Turkey",
    "TM": "Turkmenistan", "TV": "Tuvalu", "UG": "Uganda", "UA": "Ukraine",
    "AE": "United Arab Emirates", "EN": "England", "US": "United States",
    "UY": "Uruguay", "UZ": "Uzbekistan", "VU": "Vanuatu", "VE": "Venezuela",
    "VN": "Vietnam", "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe",
    "KP": "North Korea", "KR": "South Korea", "PS": "Palestine",
    "XK": "Kosovo", "GB-SCO": "Scotland", "GB-WAL": "Wales", "GB-NIR": "Northern Ireland",
    "SC": "Scotland", "WL": "Wales", "NI2": "Northern Ireland",
    "CW": "Curacao",
}

# -----------------------------------------------------------------------
# CONFIGURACION  (edita aqui)
# -----------------------------------------------------------------------
ODDS_API_KEY = "66792ac538749b335af8beb37c4a669e"  # the-odds-api.com
ODDS_API_SPORT = "soccer_fifa_world_cup"   # deporte en la API
ODDS_API_REGIONS = "eu"                    # eu = cuotas europeas (decimales)
ODDS_API_MARKETS = "h2h,totals"            # head-to-head: 1X2 + over/under

FD_API_KEY = "fd_a497537cbd0284f82d3ab59d5a7ed923bee005f04d97689d"  # footballdata.io
FD_WC_LEAGUE_ID = 50   # World Cup en footballdata.io

# Cuantos partidos recientes usar por equipo para calcular xG promedio
XG_RECENT_MATCHES = 5

# Pesos del modelo
ELO_WEIGHT    = 0.15
MARKET_WEIGHT = 0.55
XG_WEIGHT     = 0.30

# Puntos de tu polla
RESULT_POINTS     = 5
EXACT_GOAL_POINTS = 2
MARGIN_POINTS     = 1

DEFAULT_TOTAL_GOALS = 2.6
MAX_GOALS_GRID      = 10
MAX_GOALS_PREDICT   = 6

# Cache en memoria para no hacer dos veces el mismo request
_elo_cache: dict = {}
_odds_cache: list = []
_fd_results_cache: list = []


# -----------------------------------------------------------------------
# MODELO DE POISSON (identico al original)
# -----------------------------------------------------------------------
def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def build_grid(lh, la, n=MAX_GOALS_GRID):
    pa = [poisson_pmf(k, lh) for k in range(n + 1)]
    pb = [poisson_pmf(k, la) for k in range(n + 1)]
    grid = [[pa[h] * pb[a] for a in range(n + 1)] for h in range(n + 1)]
    return grid, pa, pb


def result_probs(grid):
    ph = pd = pa = 0.0
    for h, row in enumerate(grid):
        for a, p in enumerate(row):
            if h > a:   ph += p
            elif h == a: pd += p
            else:        pa += p
    return ph, pd, pa


def expected_score(grid):
    ph, pd, _ = result_probs(grid)
    return ph + 0.5 * pd


def elo_we(elo_home, elo_away, adv=0.0):
    return 1.0 / (1.0 + 10 ** (-((elo_home + adv) - elo_away) / 400.0))


def devig(oh, od, oa):
    raw = [1 / oh, 1 / od, 1 / oa]
    s = sum(raw)
    return [r / s for r in raw]


def blend_we(components):
    avail = [(we, w) for we, w in components if we is not None]
    if not avail:
        raise ValueError("Sin datos suficientes para calcular We.")
    tw = sum(w for _, w in avail)
    return sum(we * w for we, w in avail) / tw


def solve_lambdas(total, we_target, iters=60):
    lo, hi = -total + 1e-3, total - 1e-3
    for _ in range(iters):
        mid = (lo + hi) / 2
        lh, la = (total + mid) / 2, (total - mid) / 2
        we = expected_score(build_grid(lh, la)[0])
        if we < we_target: lo = mid
        else:              hi = mid
    mid = (lo + hi) / 2
    return (total + mid) / 2, (total - mid) / 2


def recommend(grid, pa, pb):
    margin_sum = {}
    for h, row in enumerate(grid):
        for a, p in enumerate(row):
            d = h - a
            margin_sum[d] = margin_sum.get(d, 0.0) + p
    ph, pd, paw = result_probs(grid)
    cands = []
    for h in range(MAX_GOALS_PREDICT + 1):
        for a in range(MAX_GOALS_PREDICT + 1):
            pr = ph if h > a else (pd if h == a else paw)
            ep = (RESULT_POINTS * pr
                  + EXACT_GOAL_POINTS * pa[h]
                  + EXACT_GOAL_POINTS * pb[a]
                  + MARGIN_POINTS * margin_sum.get(h - a, 0.0))
            cands.append((h, a, ep))
    cands.sort(key=lambda c: -c[2])
    return cands, (ph, pd, paw)


# -----------------------------------------------------------------------
# SCRAPER ELO  (eloratings.net/World.tsv)
# -----------------------------------------------------------------------
def _fetch_elo_table() -> dict[str, float]:
    """Descarga World.tsv de eloratings.net y retorna {nombre_pais: elo}.

    El TSV tiene columnas: rank rank2 CODE elo ...
    Los nombres se resuelven con el mapeo _CODE_TO_NAME embebido.
    """
    global _elo_cache
    if _elo_cache:
        return _elo_cache

    print("  [ELO] Descargando ratings desde eloratings.net...")
    url = "https://www.eloratings.net/World.tsv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"No se pudo descargar eloratings.net: {e}")

    result = {}
    for line in raw.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 4:
            continue
        code = cols[2].strip()
        try:
            elo = float(cols[3].strip())
        except ValueError:
            continue
        name = _CODE_TO_NAME.get(code, code)  # si no hay nombre, usa el codigo
        result[name] = elo

    if not result:
        raise RuntimeError("No se pudo extraer ningun equipo del TSV de eloratings.net.")

    print(f"  [ELO] {len(result)} selecciones cargadas.")
    _elo_cache = result
    return result


_NAME_ALIASES = {
    "usa": "United States",
    "united states of america": "United States",
    "curacao": "Curacao",
    "curaçao": "Curacao",
    "bosnia & herzegovina": "Bosnia-Herzegovina",
    "bosnia and herzegovina": "Bosnia-Herzegovina",
    "ir iran": "Iran",
    "korea republic": "South Korea",
    "korea dpr": "North Korea",
    "czech republic": "Czech Republic",
}

def get_elo(team_name: str) -> float | None:
    table = _fetch_elo_table()
    # Alias conocidos
    alias = _NAME_ALIASES.get(team_name.lower())
    if alias and alias in table:
        return table[alias]
    # Busqueda exacta
    if team_name in table:
        return table[team_name]
    # Busqueda case-insensitive
    low = team_name.lower()
    for k, v in table.items():
        if k.lower() == low:
            return v
    # Busqueda parcial
    for k, v in table.items():
        if low in k.lower() or k.lower() in low:
            return v
    return None


def search_team_elo(query: str) -> list[tuple[str, float]]:
    """Retorna lista de (nombre, elo) que hacen match con la busqueda."""
    table = _fetch_elo_table()
    q = query.lower()
    return [(k, v) for k, v in table.items() if q in k.lower()]


# -----------------------------------------------------------------------
# THE ODDS API
# -----------------------------------------------------------------------
def _fetch_odds(api_key: str) -> list[dict]:
    """Descarga los mercados H2H del Mundial 2026 desde The Odds API."""
    global _odds_cache
    if _odds_cache:
        return _odds_cache

    print("  [ODDS] Consultando The Odds API...")
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": ODDS_API_REGIONS,
        "markets": ODDS_API_MARKETS,
        "oddsFormat": "decimal",
    })
    url = f"https://api.the-odds-api.com/v4/sports/{ODDS_API_SPORT}/odds/?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            remaining = resp.headers.get("x-requests-remaining", "?")
            data = json.loads(resp.read().decode())
            print(f"  [ODDS] {len(data)} partidos encontrados. Requests restantes: {remaining}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"The Odds API error {e.code}: {body}")
    except Exception as e:
        raise RuntimeError(f"No se pudo conectar con The Odds API: {e}")

    _odds_cache = data
    return data


def get_odds_for_match(home: str, away: str, api_key: str) -> tuple[float, float, float] | None:
    """Retorna (odds_home, odds_draw, odds_away) o None si no hay partido."""
    if not api_key:
        return None
    try:
        events = _fetch_odds(api_key)
    except RuntimeError as e:
        print(f"  [ODDS] Advertencia: {e}")
        return None

    home_low = home.lower()
    away_low = away.lower()

    for event in events:
        eh = event.get("home_team", "").lower()
        ea = event.get("away_team", "").lower()
        if (home_low in eh or eh in home_low) and (away_low in ea or ea in away_low):
            return _extract_h2h(event)
        # tambien prueba invertido (por si el fixture esta al reves)
        if (away_low in eh or eh in away_low) and (home_low in ea or ea in home_low):
            res = _extract_h2h(event)
            if res:
                return res[2], res[1], res[0]  # invertir home/away
    return None


def _extract_h2h(event: dict) -> tuple[float, float, float] | None:
    """Saca la mejor linea H2H (promedio de casas) de un evento."""
    home_team = event.get("home_team", "")
    bookmakers = event.get("bookmakers", [])
    all_odds = {"home": [], "draw": [], "away": []}

    for bm in bookmakers:
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name", "")
                price = float(outcome.get("price", 0))
                if price <= 1.0:
                    continue
                if name == home_team:
                    all_odds["home"].append(price)
                elif name == "Draw":
                    all_odds["draw"].append(price)
                else:
                    all_odds["away"].append(price)

    if all_odds["home"] and all_odds["draw"] and all_odds["away"]:
        avg = lambda lst: sum(lst) / len(lst)
        return avg(all_odds["home"]), avg(all_odds["draw"]), avg(all_odds["away"])
    return None


def _extract_totals(event: dict) -> tuple[float, float, float] | None:
    """Saca la linea over/under mas comun y sus probabilidades desviguadas."""
    lines = {}
    for bm in event.get("bookmakers", []):
        for market in bm.get("markets", []):
            if market.get("key") != "totals":
                continue
            for o in market.get("outcomes", []):
                pt = o.get("point")
                name = o.get("name", "")
                price = float(o.get("price", 0))
                if pt is None or price <= 1.0:
                    continue
                if pt not in lines:
                    lines[pt] = {"over": [], "under": []}
                if name == "Over":
                    lines[pt]["over"].append(price)
                elif name == "Under":
                    lines[pt]["under"].append(price)

    if not lines:
        return None

    # Elegir la linea con mas casas disponibles
    best = max(lines.items(), key=lambda x: len(x[1]["over"]) + len(x[1]["under"]))
    pt, odds = best
    if not odds["over"] or not odds["under"]:
        return None

    avg_over  = sum(odds["over"])  / len(odds["over"])
    avg_under = sum(odds["under"]) / len(odds["under"])
    raw = [1 / avg_over, 1 / avg_under]
    s = sum(raw)
    p_over, p_under = raw[0] / s, raw[1] / s
    return float(pt), round(p_over, 3), round(p_under, 3)


def get_full_odds(home: str, away: str, api_key: str) -> dict | None:
    """Retorna dict con h2h, totals y fecha para un partido, o None."""
    if not api_key:
        return None
    try:
        events = _fetch_odds(api_key)
    except RuntimeError as e:
        print(f"  [ODDS] Advertencia: {e}")
        return None

    home_low = home.lower()
    away_low = away.lower()

    for event in events:
        eh = event.get("home_team", "").lower()
        ea = event.get("away_team", "").lower()
        flipped = False
        if (home_low in eh or eh in home_low) and (away_low in ea or ea in away_low):
            pass
        elif (away_low in eh or eh in away_low) and (home_low in ea or ea in home_low):
            flipped = True
        else:
            continue

        h2h = _extract_h2h(event)
        if h2h and flipped:
            h2h = (h2h[2], h2h[1], h2h[0])

        totals = _extract_totals(event)
        fecha = event.get("commence_time", "")[:10]

        return {"h2h": h2h, "totals": totals, "fecha": fecha}
    return None


def list_available_matches(api_key: str) -> list[dict]:
    """Lista los partidos disponibles con h2h, totals y fecha."""
    if not api_key:
        return []
    try:
        events = _fetch_odds(api_key)
    except RuntimeError:
        return []

    result = []
    for e in events:
        h2h = _extract_h2h(e)
        totals = _extract_totals(e)
        fecha = e.get("commence_time", "")[:10]
        if h2h:
            ph, pd, pa = devig(*h2h)
        else:
            ph = pd = pa = None
        result.append({
            "local": e.get("home_team", ""),
            "visitante": e.get("away_team", ""),
            "fecha": fecha,
            "p_local": round(ph, 3) if ph else None,
            "p_empate": round(pd, 3) if pd else None,
            "p_visit": round(pa, 3) if pa else None,
            "ou_linea": totals[0] if totals else None,
            "ou_over": totals[1] if totals else None,
            "ou_under": totals[2] if totals else None,
        })
    return result


# -----------------------------------------------------------------------
# CLI INTERACTIVO
# -----------------------------------------------------------------------
def _input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def _resolve_team(label: str, table: dict) -> tuple[str, float]:
    """Pide un equipo al usuario y resuelve su ELO."""
    while True:
        query = _input(f"  Equipo {label}: ")
        matches = [(k, v) for k, v in table.items() if query.lower() in k.lower()]
        if not matches:
            print("    No encontrado. Intenta con otro nombre.")
            continue
        if len(matches) == 1:
            name, elo = matches[0]
            print(f"    -> {name}  (ELO: {elo:.0f})")
            return name, elo
        # Mostrar opciones
        print("    Varias coincidencias:")
        for i, (n, e) in enumerate(matches[:8], 1):
            print(f"      {i}. {n}  ({e:.0f})")
        sel = _input("    Elige numero (o Enter para buscar de nuevo): ")
        if sel.isdigit() and 1 <= int(sel) <= len(matches[:8]):
            name, elo = matches[int(sel) - 1]
            print(f"    -> {name}  (ELO: {elo:.0f})")
            return name, elo


# -----------------------------------------------------------------------
# FOOTBALLDATA.IO — resultados y xG del Mundial
# -----------------------------------------------------------------------
def _fetch_fd_results() -> list:
    """Descarga todos los resultados del WC desde footballdata.io."""
    global _fd_results_cache
    if _fd_results_cache:
        return _fd_results_cache

    print("  [FD] Descargando resultados del Mundial desde footballdata.io...")
    url = f"https://footballdata.io/api/v1/fixtures/results?league_id={FD_WC_LEAGUE_ID}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"Bearer {FD_API_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [FD] Advertencia: no se pudieron descargar resultados ({e})")
        return []

    matches = data.get("data", {}).get("matches", [])
    print(f"  [FD] {len(matches)} resultados cargados.")
    _fd_results_cache = matches
    return matches


def _normalize_fd_name(name: str) -> str:
    """Normaliza nombres de footballdata.io para comparar con los del modelo."""
    aliases = {
        "usa": "United States",
        "united states": "United States",
        "bosnia and herzegovina": "Bosnia-Herzegovina",
        "bosnia & herzegovina": "Bosnia-Herzegovina",
        "congo dr": "DR Congo",
        "dr congo": "DR Congo",
        "ir iran": "Iran",
        "korea republic": "South Korea",
        "republic of ireland": "Republic of Ireland",
        "curacao": "Curacao",
        "curaçao": "Curacao",
    }
    return aliases.get(name.lower(), name)


_ELO_PROMEDIO_WC = 1850.0  # ELO promedio de los equipos del Mundial 2026

def get_team_recent_xg(team_name: str, elo_table: dict, n: int = XG_RECENT_MATCHES) -> dict | None:
    """Retorna xG ajustado por calidad del rival.

    El xG crudo se escala por el ratio ELO_promedio / ELO_rival:
      - Si el rival era débil (ELO 1500), el xG generado se divide ~1.23  (se penaliza)
      - Si el rival era fuerte (ELO 2100), el xG generado se multiplica ~1.14 (se premia)
    Esto evita que golear a un rival malo infle el lambda del equipo.
    """
    results = _fetch_fd_results()
    if not results:
        return None

    team_low = team_name.lower()
    team_matches = []

    for m in results:
        if m.get("season", {}).get("season_id") != 618:
            continue
        if m.get("game_week", 0) == 0:
            continue
        ht_raw = m["home_team"]["team_name"]
        at_raw = m["away_team"]["team_name"]
        ht = _normalize_fd_name(ht_raw).lower()
        at = _normalize_fd_name(at_raw).lower()
        xg = m.get("stats", {}).get("xg")
        if xg is None or (xg["home"] == 0 and xg["away"] == 0):
            continue
        score = m.get("score", {})

        rival_name = None
        xg_scored = xg_conceded = goals_scored = goals_conceded = None

        if ht == team_low or team_low in ht or ht in team_low:
            rival_name    = _normalize_fd_name(at_raw)
            xg_scored     = xg["home"]
            xg_conceded   = xg["away"]
            goals_scored  = score.get("home", 0)
            goals_conceded= score.get("away", 0)
        elif at == team_low or team_low in at or at in team_low:
            rival_name    = _normalize_fd_name(ht_raw)
            xg_scored     = xg["away"]
            xg_conceded   = xg["home"]
            goals_scored  = score.get("away", 0)
            goals_conceded= score.get("home", 0)

        if rival_name is None:
            continue

        # Peso por ELO del rival (ratio respecto al promedio del torneo)
        rival_elo = get_elo(rival_name) or _ELO_PROMEDIO_WC
        elo_weight = rival_elo / _ELO_PROMEDIO_WC  # >1 si rival fuerte, <1 si débil

        team_matches.append({
            "xg_scored":     xg_scored,
            "xg_conceded":   xg_conceded,
            "goals_scored":  goals_scored,
            "goals_conceded":goals_conceded,
            "elo_weight":    elo_weight,
            "rival_elo":     rival_elo,
            "rival_name":    rival_name,
            "date":          m["match_date"],
        })

    if not team_matches:
        return None

    team_matches.sort(key=lambda x: x["date"], reverse=True)
    recent = team_matches[:n]

    # Promedio ponderado por ELO del rival
    total_w = sum(r["elo_weight"] for r in recent)
    xg_scored_adj   = sum(r["xg_scored"]    * r["elo_weight"] for r in recent) / total_w
    xg_conceded_adj = sum(r["xg_conceded"]  * r["elo_weight"] for r in recent) / total_w

    return {
        "xg_scored":    round(xg_scored_adj, 3),
        "xg_conceded":  round(xg_conceded_adj, 3),
        "goals_scored":  round(sum(r["goals_scored"]   for r in recent) / len(recent), 2),
        "goals_conceded":round(sum(r["goals_conceded"] for r in recent) / len(recent), 2),
        "partidos": len(recent),
    }


def xg_we(xg_home: float, xg_away: float) -> float:
    """We basado en xG usando la formula de ELO adaptada a goles esperados."""
    # Convertir xG a probabilidades via grilla de Poisson
    grid, _, _ = build_grid(xg_home, xg_away)
    return expected_score(grid)


def calc_match(home_name: str, away_name: str, elo_table: dict, api_key: str) -> dict | None:
    """Calcula el pick para un partido automaticamente sin input del usuario."""
    elo_home = get_elo(home_name)
    elo_away = get_elo(away_name)

    if elo_home is None or elo_away is None:
        print(f"  [SKIP] Sin ELO para {home_name} o {away_name}")
        return None

    full   = get_full_odds(home_name, away_name, api_key)
    odds   = full["h2h"]    if full else None
    totals = full["totals"] if full else None
    fecha  = full["fecha"]  if full else ""

    # xG reciente del WC ajustado por calidad de rivales
    xg_home_stats = get_team_recent_xg(home_name, elo_table)
    xg_away_stats = get_team_recent_xg(away_name, elo_table)

    we_elo = elo_we(elo_home, elo_away)

    we_market = None
    market_p_local = market_p_empate = market_p_visit = None
    if odds:
        mp_h, mp_d, mp_a = devig(*odds)
        market_p_local  = round(mp_h, 3)
        market_p_empate = round(mp_d, 3)
        market_p_visit  = round(mp_a, 3)
        we_market = mp_h + 0.5 * mp_d

    # xG We: promedio de xG anotado del local vs xG concedido del visitante (y viceversa)
    we_xg = None
    xg_lambda_home = xg_lambda_away = None
    if xg_home_stats and xg_away_stats:
        # Lambda estimado: promedio entre xG anotado propio y xG concedido del rival
        xg_lambda_home = (xg_home_stats["xg_scored"] + xg_away_stats["xg_conceded"]) / 2
        xg_lambda_away = (xg_away_stats["xg_scored"] + xg_home_stats["xg_conceded"]) / 2
        xg_lambda_home = max(0.3, xg_lambda_home)
        xg_lambda_away = max(0.3, xg_lambda_away)
        we_xg = xg_we(xg_lambda_home, xg_lambda_away)

    we_final = blend_we([
        (we_elo,    ELO_WEIGHT),
        (we_market, MARKET_WEIGHT),
        (we_xg,     XG_WEIGHT),
    ])

    # Total de goles: si hay xG reciente, usarlo; si no, usar O/U del mercado
    if xg_lambda_home and xg_lambda_away:
        total_goals = xg_lambda_home + xg_lambda_away
    elif totals:
        total_goals = totals[0]
    else:
        total_goals = DEFAULT_TOTAL_GOALS

    lh, la = solve_lambdas(total_goals, we_final)
    grid, pa_dist, pb_dist = build_grid(lh, la)
    cands, (ph, pd, paw) = recommend(grid, pa_dist, pb_dist)
    top = cands[:3]

    xg_info = ""
    if xg_lambda_home and xg_lambda_away:
        xg_info = f" | xG {xg_lambda_home:.2f}-{xg_lambda_away:.2f}"
    print(f"  {home_name} vs {away_name}  ->  {top[0][0]}-{top[0][1]}  ({top[0][2]:.2f} pts){xg_info}")

    return {
        "local": home_name, "visitante": away_name,
        "fecha": fecha,
        "elo_local": round(elo_home), "elo_visit": round(elo_away),
        "we_elo": round(we_elo, 3),
        "we_market": round(we_market, 3) if we_market else None,
        "we_xg": round(we_xg, 3) if we_xg else None,
        "we_final": round(we_final, 3),
        # xG reciente por equipo
        "xg_local_scored":   xg_home_stats["xg_scored"]   if xg_home_stats else None,
        "xg_local_conceded": xg_home_stats["xg_conceded"] if xg_home_stats else None,
        "xg_visit_scored":   xg_away_stats["xg_scored"]   if xg_away_stats else None,
        "xg_visit_conceded": xg_away_stats["xg_conceded"] if xg_away_stats else None,
        "xg_partidos_local": xg_home_stats["partidos"]    if xg_home_stats else None,
        "xg_partidos_visit": xg_away_stats["partidos"]    if xg_away_stats else None,
        # Probabilidades del modelo Poisson (para Consolidado)
        "p_local": round(ph, 3), "p_empate": round(pd, 3), "p_visit": round(paw, 3),
        # Probabilidades desviguadas del mercado (para Odds)
        "market_p_local": market_p_local, "market_p_empate": market_p_empate, "market_p_visit": market_p_visit,
        "lambda_local": round(lh, 2), "lambda_visit": round(la, 2),
        "ou_linea": totals[0] if totals else None,
        "ou_over": totals[1] if totals else None,
        "ou_under": totals[2] if totals else None,
        "pick_1": f"{top[0][0]}-{top[0][1]}", "pts_1": round(top[0][2], 2),
        "pick_2": f"{top[1][0]}-{top[1][1]}", "pts_2": round(top[1][2], 2),
        "pick_3": f"{top[2][0]}-{top[2][1]}", "pts_3": round(top[2][2], 2),
    }


def save_results(results: list[dict], path="picks_pollero.csv"):
    if not results:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"  Resultados guardados en {path}")


def _build_partidos_jugados() -> list[dict]:
    """Retorna lista de partidos jugados del WC con resultado y xG, ordenados por fecha desc."""
    results = _fetch_fd_results()
    partidos = []
    for m in results:
        if m.get("season", {}).get("season_id") != 618:
            continue
        if m.get("game_week", 0) == 0:
            continue
        xg = m.get("stats", {}).get("xg", {})
        score = m.get("score", {})
        # Filtrar partidos incompletos (sin ganador definido o marcador 0-0 con xG alto)
        if not score.get("winner"):
            continue
        partidos.append({
            "fecha":      m["match_date"][:10],
            "local":      m["home_team"]["team_name"],
            "visitante":  m["away_team"]["team_name"],
            "goles_local":    score.get("home"),
            "goles_visit":    score.get("away"),
            "xg_local":   round(xg.get("home", 0), 2),
            "xg_visit":   round(xg.get("away", 0), 2),
            "ganador":    score.get("winner"),  # "home" | "away" | "draw"
            "game_week":  m.get("game_week", 0),
        })
    partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return partidos


def export_json(results: list[dict], elo_table: dict, available_matches: list[tuple[str, str]]):
    """Exporta picks_data.json en la carpeta del repo git (Modelo_Pollero)."""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(script_dir, "Modelo_Pollero")
    out_path = os.path.join(repo_dir, "picks_data.json")

    from datetime import datetime
    payload = {
        "picks": results,
        "equipos": sorted(elo_table.keys()),
        "partidos_con_odds": available_matches,
        "partidos_jugados": _build_partidos_jugados(),
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  JSON exportado en {out_path}")
    print("  Abre GitHub Desktop -> commit -> push y la web se actualiza.")


def main():
    print("\n" + "#"*55)
    print("#   POLLERO AUTOMATIZADO - MUNDIAL 2026            #")
    print("#"*55)

    try:
        elo_table = _fetch_elo_table()
    except RuntimeError as e:
        print(f"\nERROR al cargar ELO: {e}")
        sys.exit(1)

    print("  [ODDS] Descargando partidos y cuotas...")
    available = list_available_matches(ODDS_API_KEY)

    if not available:
        print("  Sin partidos disponibles en The Odds API.")
        sys.exit(0)

    print(f"  {len(available)} partidos encontrados. Calculando picks...\n")

    results = []
    for p in available:
        result = calc_match(p["local"], p["visitante"], elo_table, ODDS_API_KEY)
        if result:
            results.append(result)

    save_results(results)
    export_json(results, elo_table, available)
    print(f"\n  Listo! {len(results)} picks calculados y exportados.\n")


if __name__ == "__main__":
    main()
