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
}

# -----------------------------------------------------------------------
# CONFIGURACION  (edita aqui)
# -----------------------------------------------------------------------
ODDS_API_KEY = "66792ac538749b335af8beb37c4a669e"  # the-odds-api.com
ODDS_API_SPORT = "soccer_fifa_world_cup"   # deporte en la API
ODDS_API_REGIONS = "eu"                    # eu = cuotas europeas (decimales)
ODDS_API_MARKETS = "h2h"                   # head-to-head: 1X2

# Pesos del modelo
ELO_WEIGHT    = 0.20
MARKET_WEIGHT = 0.60
XG_WEIGHT     = 0.20

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


def get_elo(team_name: str) -> float | None:
    table = _fetch_elo_table()
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


def list_available_matches(api_key: str) -> list[tuple[str, str]]:
    """Lista los partidos disponibles en la API."""
    if not api_key:
        return []
    try:
        events = _fetch_odds(api_key)
        return [(e.get("home_team", ""), e.get("away_team", "")) for e in events]
    except RuntimeError:
        return []


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


def _get_api_key() -> str:
    if ODDS_API_KEY:
        return ODDS_API_KEY
    print("\n  Para obtener cuotas necesitas una API key gratuita de the-odds-api.com")
    key = _input("  API Key (Enter para omitir cuotas): ")
    return key


def run_match(elo_table: dict, api_key: str):
    print("\n" + "="*55)
    print("  NUEVO PARTIDO")
    print("="*55)

    home_name, elo_home = _resolve_team("LOCAL", elo_table)
    away_name, elo_away = _resolve_team("VISITANTE", elo_table)

    # Ventaja de sede
    adv_raw = _input("  Ventaja ELO por sede para el local (Enter = 0): ")
    home_adv = float(adv_raw) if adv_raw.replace(".", "").lstrip("-").isdigit() else 0.0

    # Cuotas
    odds = get_odds_for_match(home_name, away_name, api_key)
    if odds:
        oh, od, oa = odds
        print(f"  [ODDS] {home_name} {oh:.2f} / Empate {od:.2f} / {away_name} {oa:.2f}")
    else:
        print("  [ODDS] Sin cuotas disponibles para este partido.")

    # Total goles
    tg_raw = _input(f"  Total goles esperados del mercado over/under (Enter = {DEFAULT_TOTAL_GOALS}): ")
    total_goals = float(tg_raw) if tg_raw.replace(".", "").isdigit() else DEFAULT_TOTAL_GOALS

    # xG opcional
    xg_raw_h = _input(f"  xG ponderado de {home_name} (Enter = omitir): ")
    xg_raw_a = _input(f"  xG ponderado de {away_name} (Enter = omitir): ")
    a_hat_home = float(xg_raw_h) if xg_raw_h.replace(".", "").isdigit() else None
    a_hat_away = float(xg_raw_a) if xg_raw_a.replace(".", "").isdigit() else None

    # ---- Calcular ----
    we_elo = elo_we(elo_home, elo_away, home_adv)

    we_market = None
    if odds:
        ph, pd, pa = devig(*odds)
        we_market = ph + 0.5 * pd

    we_xg = None
    if a_hat_home is not None and a_hat_away is not None:
        we_xg = expected_score(build_grid(a_hat_home, a_hat_away)[0])

    we_final = blend_we([
        (we_elo,    ELO_WEIGHT),
        (we_market, MARKET_WEIGHT),
        (we_xg,     XG_WEIGHT),
    ])

    lh, la = solve_lambdas(total_goals, we_final)
    grid, pa_dist, pb_dist = build_grid(lh, la)
    cands, (ph, pd, paw) = recommend(grid, pa_dist, pb_dist)
    top = cands[:3]

    # ---- Mostrar resultados ----
    print()
    print(f"  {'='*50}")
    print(f"  {home_name}  vs  {away_name}")
    print(f"  {'='*50}")
    print(f"  We Elo     : {we_elo:.3f}")
    if we_market is not None:
        print(f"  We mercado : {we_market:.3f}")
    if we_xg is not None:
        print(f"  We xG      : {we_xg:.3f}")
    print(f"  We FINAL   : {we_final:.3f}")
    print()
    print(f"  P(local)   : {ph:.1%}")
    print(f"  P(empate)  : {pd:.1%}")
    print(f"  P(visit.)  : {paw:.1%}")
    print()
    print(f"  λ local    : {lh:.2f} goles esperados")
    print(f"  λ visita.  : {la:.2f} goles esperados")
    print()
    print(f"  PICK RECOMENDADO : {top[0][0]}-{top[0][1]}  ({top[0][2]:.2f} pts esp.)")
    print(f"  Alternativa 2    : {top[1][0]}-{top[1][1]}  ({top[1][2]:.2f} pts esp.)")
    print(f"  Alternativa 3    : {top[2][0]}-{top[2][1]}  ({top[2][2]:.2f} pts esp.)")
    print()

    return {
        "local": home_name, "visitante": away_name,
        "we_elo": round(we_elo, 3),
        "we_market": round(we_market, 3) if we_market else None,
        "we_xg": round(we_xg, 3) if we_xg else None,
        "we_final": round(we_final, 3),
        "p_local": round(ph, 3), "p_empate": round(pd, 3), "p_visit": round(paw, 3),
        "lambda_local": round(lh, 2), "lambda_visit": round(la, 2),
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


def export_json(results: list[dict], elo_table: dict, available_matches: list[tuple[str, str]]):
    """Exporta picks_data.json para que lo consuma index.html."""
    payload = {
        "picks": results,
        "equipos": sorted(elo_table.keys()),
        "partidos_con_odds": [{"local": h, "visitante": a} for h, a in available_matches],
    }
    with open("picks_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("  JSON exportado en picks_data.json  ->  abre index.html en el navegador")


def main():
    print("\n" + "#"*55)
    print("#   POLLERO AUTOMATIZADO - MUNDIAL 2026            #")
    print("#"*55)

    # Cargar ELO una sola vez
    try:
        elo_table = _fetch_elo_table()
    except RuntimeError as e:
        print(f"\nERROR al cargar ELO: {e}")
        print("Verifica tu conexion a internet e intenta de nuevo.")
        sys.exit(1)

    api_key = _get_api_key()
    available = list_available_matches(api_key)

    if available:
        print(f"\n  Partidos con cuotas disponibles ({len(available)}):")
        for h, a in available:
            print(f"    {h}  vs  {a}")

    results = []
    while True:
        try:
            result = run_match(elo_table, api_key)
            results.append(result)
        except (KeyboardInterrupt, EOFError):
            break

        again = _input("  Predecir otro partido? (s/n): ")
        if again.lower() not in ("s", "si", "y", "yes"):
            break

    save_results(results)
    export_json(results, elo_table, available)
    print("\n  Hasta la proxima!\n")


if __name__ == "__main__":
    main()
