"""
Modelo predictivo para la polla mundialista 2026.

Combina dos fuentes de informacion para cada partido:
  1. Elo + cuotas de casas de apuestas -> determinan la probabilidad de
     victoria local / empate / visitante (el "ganador").
  2. Goles totales esperados (xG de mercado, o estimacion propia) -> junto
     con el resultado anterior, determinan la distribucion completa de
     marcadores posibles via un modelo de Poisson.

Logica del modelo
------------------
Paso 1: Se calcula el "expected score" (We) de Elo, igual a la formula
        clasica de Elo (1 = victoria segura, 0.5 = 50-50, 0 = derrota
        segura), con un ajuste opcional de ventaja por sede.

Paso 2: Si hay cuotas de mercado, se "desviguean" (se les quita el margen
        de la casa) para obtener probabilidades implicitas, y se calcula
        su propio We.

Paso 2b: Si hay un xG reciente ya ponderado por el Elo de los rivales
        enfrentados (a_hat_home / a_hat_away), se mete esa pareja de goles
        esperados en la misma formula de Poisson de la Etapa 2 para sacar
        un tercer We (We_xG): "si el local promediara a_hat_home goles y
        el visitante a_hat_away, quien tendria mas puntaje esperado?".

Paso 3: Se combinan los We disponibles (Elo siempre, mercado y xG si hay
        datos) con pesos fijos -> We_final. Si falta algun componente, los
        pesos restantes se renormalizan para seguir sumando 1.

Paso 4: Se toma el total de goles esperados del partido (idealmente del
        mercado de over/under; si no hay dato, se usa un valor por
        defecto razonable).

Paso 5: Se buscan, por busqueda binaria, los goles esperados de cada
        equipo (lambda_local, lambda_visitante) que sumados dan el total
        del paso 4 y que, en un modelo de Poisson independiente,
        reproducen el We_final del paso 3. Esto deja un modelo de Poisson
        totalmente consistente con las dos fuentes de informacion.

Paso 6: Con (lambda_local, lambda_visitante) se construye la distribucion
        completa de marcadores y se calculan los puntos esperados de cada
        prediccion posible bajo las reglas de tu polla, recomendando la de
        mayor valor esperado.

Como usarlo
-----------
1. Llena partidos.csv con los partidos que quieras predecir (una fila por
   partido). Columnas opcionales se pueden dejar vacias.
2. Corre: python modelo_mundial.py partidos.csv
3. Revisa picks_recomendados.csv con el resultado.

De donde saco los datos
------------------------
- elo_home / elo_away: eloratings.net (seleccion nacional, valor actual).
- odds_home / odds_draw / odds_away: cuotas decimales de cualquier casa de
  apuestas (ej. 1.85, no +185 ni 6/5). Deja vacias si no las tienes.
- expected_total_goals: el total esperado de goles del mercado de
  over/under. Si no lo tienes, deja la celda vacia (se usa un valor por
  defecto razonable).
- a_hat_home / a_hat_away: el xG promedio de los ultimos partidos de cada
  equipo, ya ponderado por el Elo de los rivales que enfrentaron. Se
  calcula con weighted_xg_advantage() a partir de una lista de (xg,
  elo_rival). Si no los tienes, deja las celdas vacias.
"""

import csv
import math
import sys
from dataclasses import dataclass

# ---- Reglas de puntaje de tu polla (ajusta aqui si cambian) ----
RESULT_POINTS = 5       # puntos por acertar ganador/empate
EXACT_GOAL_POINTS = 2   # puntos por acertar goles exactos de UN equipo
MARGIN_POINTS = 1        # puntos por acertar la diferencia de gol

# ---- Parametros del modelo (ajustables) ----
ELO_WEIGHT = 0.2              # peso de We_Elo al combinar We_final
MARKET_WEIGHT = 0.6           # peso de We_mercado al combinar We_final
XG_WEIGHT = 0.2                # peso de We_xG al combinar We_final
DEFAULT_TOTAL_GOALS = 2.6     # total esperado si no hay dato de mercado
MAX_GOALS_GRID = 10           # tope de goles para la grilla de Poisson
MAX_GOALS_PREDICTION = 6      # tope de goles a considerar como prediccion


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def build_grid(lambda_home, lambda_away, max_goals=MAX_GOALS_GRID):
    pa = [poisson_pmf(k, lambda_home) for k in range(max_goals + 1)]
    pb = [poisson_pmf(k, lambda_away) for k in range(max_goals + 1)]
    grid = [[pa[h] * pb[a] for a in range(max_goals + 1)] for h in range(max_goals + 1)]
    return grid, pa, pb


def result_probs(grid):
    p_home = p_draw = p_away = 0.0
    n = len(grid)
    for h in range(n):
        for a in range(n):
            if h > a:
                p_home += grid[h][a]
            elif h == a:
                p_draw += grid[h][a]
            else:
                p_away += grid[h][a]
    return p_home, p_draw, p_away


def expected_score(grid):
    p_home, p_draw, _ = result_probs(grid)
    return p_home + 0.5 * p_draw


def elo_we(elo_home, elo_away, home_adv=0.0):
    dr = (elo_home + home_adv) - elo_away
    return 1.0 / (1.0 + 10 ** (-dr / 400.0))


def devig_odds(odds_home, odds_draw, odds_away):
    raw = [1.0 / odds_home, 1.0 / odds_draw, 1.0 / odds_away]
    s = sum(raw)
    return [r / s for r in raw]


def weighted_xg_advantage(matches, avg_elo):
    """a_hat: promedio de xG de los ultimos partidos de un equipo, cada uno
    ajustado por que tan fuerte era el rival al que enfrento.

    matches: lista de tuplas (xg, elo_rival) de los ultimos N partidos.
    avg_elo: Elo promedio de referencia (ej. el promedio de los 48
             equipos del Mundial).
    """
    if not matches or not avg_elo:
        return None
    adjusted = [xg * (rival_elo / avg_elo) for xg, rival_elo in matches]
    return sum(adjusted) / len(adjusted)


def we_from_attack_estimates(a_hat_home, a_hat_away):
    """We_xG: mete (a_hat_home, a_hat_away) en la misma formula de Poisson
    de la Etapa 2 para sacar el expected score que implican esos dos
    numeros de xG ponderado, igual que We_Elo o We_mercado."""
    if a_hat_home is None or a_hat_away is None:
        return None
    grid, _, _ = build_grid(a_hat_home, a_hat_away, max_goals=MAX_GOALS_GRID)
    return expected_score(grid)


def blend_we(components):
    """Combina varios componentes de We con sus pesos.

    components: lista de tuplas (we, peso). Si we es None (no hay datos
    para ese componente), se ignora y los pesos restantes se renormalizan
    para que sigan sumando 1.
    """
    available = [(we, w) for we, w in components if we is not None]
    if not available:
        raise ValueError("Necesitas al menos un componente de We disponible (Elo, mercado o xG).")
    total_w = sum(w for _, w in available)
    return sum(we * w for we, w in available) / total_w


def solve_lambdas(total_goals, we_target, max_iter=60):
    """Busca lambda_home, lambda_away que sumen total_goals y reproduzcan
    we_target en un modelo de Poisson independiente (busqueda binaria)."""
    lo, hi = -total_goals + 1e-3, total_goals - 1e-3
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        lh, la = (total_goals + mid) / 2, (total_goals - mid) / 2
        grid, _, _ = build_grid(lh, la, max_goals=MAX_GOALS_GRID)
        we = expected_score(grid)
        if we < we_target:
            lo = mid
        else:
            hi = mid
    mid = (lo + hi) / 2
    return (total_goals + mid) / 2, (total_goals - mid) / 2


def recommend_scoreline(grid, pa, pb):
    margin_sum = {}
    n = len(grid)
    for h in range(n):
        for a in range(n):
            d = h - a
            margin_sum[d] = margin_sum.get(d, 0.0) + grid[h][a]
    p_home, p_draw, p_away = result_probs(grid)

    candidates = []
    for h in range(MAX_GOALS_PREDICTION + 1):
        for a in range(MAX_GOALS_PREDICTION + 1):
            if h > a:
                p_result = p_home
            elif h == a:
                p_result = p_draw
            else:
                p_result = p_away
            ep = (RESULT_POINTS * p_result
                  + EXACT_GOAL_POINTS * pa[h]
                  + EXACT_GOAL_POINTS * pb[a]
                  + MARGIN_POINTS * margin_sum.get(h - a, 0.0))
            candidates.append((h, a, ep, grid[h][a]))
    candidates.sort(key=lambda c: -c[2])
    return candidates, (p_home, p_draw, p_away)


@dataclass
class MatchInput:
    team_home: str
    team_away: str
    elo_home: float
    elo_away: float
    home_advantage_elo: float = 0.0
    odds_home: float = None
    odds_draw: float = None
    odds_away: float = None
    expected_total_goals: float = None
    a_hat_home: float = None
    a_hat_away: float = None
    knockout: str = "no"


def process_match(m: MatchInput):
    we_elo = elo_we(m.elo_home, m.elo_away, m.home_advantage_elo)

    we_market = None
    if m.odds_home and m.odds_draw and m.odds_away:
        p_h, p_d, p_a = devig_odds(m.odds_home, m.odds_draw, m.odds_away)
        we_market = p_h + 0.5 * p_d

    we_xg = we_from_attack_estimates(m.a_hat_home, m.a_hat_away)

    we_final = blend_we([
        (we_elo, ELO_WEIGHT),
        (we_market, MARKET_WEIGHT),
        (we_xg, XG_WEIGHT),
    ])

    total_goals = m.expected_total_goals if m.expected_total_goals else DEFAULT_TOTAL_GOALS

    lambda_home, lambda_away = solve_lambdas(total_goals, we_final)
    grid, pa, pb = build_grid(lambda_home, lambda_away)
    candidates, (p_home, p_draw, p_away) = recommend_scoreline(grid, pa, pb)
    top = candidates[:3]

    return {
        "team_home": m.team_home,
        "team_away": m.team_away,
        "we_elo": round(we_elo, 3),
        "we_market": round(we_market, 3) if we_market is not None else None,
        "we_xg": round(we_xg, 3) if we_xg is not None else None,
        "we_final": round(we_final, 3),
        "p_home": round(p_home, 3),
        "p_draw": round(p_draw, 3),
        "p_away": round(p_away, 3),
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "pick_1": f"{top[0][0]}-{top[0][1]}",
        "pts_esp_1": round(top[0][2], 2),
        "pick_2": f"{top[1][0]}-{top[1][1]}",
        "pts_esp_2": round(top[1][2], 2),
        "pick_3": f"{top[2][0]}-{top[2][1]}",
        "pts_esp_3": round(top[2][2], 2),
        "knockout": m.knockout,
    }


def read_matches(path):
    matches = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def fnum(key, default=None):
                val = (row.get(key) or "").strip()
                return float(val) if val else default

            matches.append(MatchInput(
                team_home=row["team_home"].strip(),
                team_away=row["team_away"].strip(),
                elo_home=fnum("elo_home"),
                elo_away=fnum("elo_away"),
                home_advantage_elo=fnum("home_advantage_elo", 0.0),
                odds_home=fnum("odds_home"),
                odds_draw=fnum("odds_draw"),
                odds_away=fnum("odds_away"),
                expected_total_goals=fnum("expected_total_goals"),
                a_hat_home=fnum("a_hat_home"),
                a_hat_away=fnum("a_hat_away"),
                knockout=(row.get("knockout") or "no").strip().lower(),
            ))
    return matches


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "partidos.csv"
    matches = read_matches(path)
    results = [process_match(m) for m in matches]

    out_path = "picks_recomendados.csv"
    if results:
        fieldnames = list(results[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    for r in results:
        etiqueta = " (eliminacion)" if r["knockout"] == "si" else ""
        print(f"\n{r['team_home']} vs {r['team_away']}{etiqueta}")
        print(f"  We Elo: {r['we_elo']}  We mercado: {r['we_market']}  We xG: {r['we_xg']}  We final: {r['we_final']}")
        print(f"  P(local) {r['p_home']}  P(empate) {r['p_draw']}  P(visitante) {r['p_away']}")
        print(f"  Goles esperados: local {r['lambda_home']} - visitante {r['lambda_away']}")
        print(f"  Pick recomendado: {r['pick_1']} ({r['pts_esp_1']} pts esp.)")
        print(f"  Alternativas: {r['pick_2']} ({r['pts_esp_2']} pts) / {r['pick_3']} ({r['pts_esp_3']} pts)")

    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
