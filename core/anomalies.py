"""Detecció estadística d'anomalies de despesa — mòdul pur sense Streamlit ni Sheets."""
from __future__ import annotations

import calendar
from datetime import date

import pandas as pd

CATEGORIES_EXCLOSES: frozenset[str] = frozenset({"Freelance", "Ajut_Públic"})


def normalitzar_a_mes_complet(total_acumulat: float, avui: date) -> float:
    """Extrapola el total parcial del mes a mes complet, sense divisió per zero."""
    if avui.day == 0:
        return total_acumulat
    dies_del_mes = calendar.monthrange(avui.year, avui.month)[1]
    return (total_acumulat / avui.day) * dies_del_mes


def _mesos_anteriors(avui: date, n: int) -> list[tuple[int, int]]:
    mesos: list[tuple[int, int]] = []
    any_, mes = avui.year, avui.month
    for _ in range(n):
        mes -= 1
        if mes == 0:
            mes, any_ = 12, any_ - 1
        mesos.append((any_, mes))
    return mesos


def _filtrar_despeses(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna filas de Despesa excloent categories problemàtiques."""
    if df.empty or "tipus" not in df.columns or "categoria" not in df.columns:
        return pd.DataFrame()
    mask = (df["tipus"] == "Despesa") & (~df["categoria"].isin(CATEGORIES_EXCLOSES))
    resultat = df[mask].copy()
    if "quantitat" in resultat.columns:
        resultat["quantitat"] = pd.to_numeric(resultat["quantitat"], errors="coerce").fillna(0.0)
    return resultat


def _df_mes(df: pd.DataFrame, any_: int, mes: int) -> pd.DataFrame:
    if df.empty or "data" not in df.columns:
        return pd.DataFrame()
    try:
        dates_dt = pd.to_datetime(df["data"], errors="coerce")
        mask = (dates_dt.dt.year == any_) & (dates_dt.dt.month == mes)
        return df[mask]
    except Exception:
        return pd.DataFrame()


def categories_amb_variacio(
    df: pd.DataFrame,
    avui: date,
    *,
    mesos_historic: int = 3,
    llindar_pct: float = 30.0,
) -> list[dict]:
    """Compara despeses del mes actual (normalitzades) amb la mitjana dels N mesos previs.

    Retorna [{"categoria", "actual", "actual_normalitzat", "mitjana_historic",
              "variacio_pct", "tipus": "augment"|"reduccio"}]
    Només categories amb |variacio_pct| >= llindar_pct.
    """
    df_d = _filtrar_despeses(df)
    if df_d.empty:
        return []

    mesos_prev = _mesos_anteriors(avui, mesos_historic)
    if not mesos_prev:
        return []

    df_actual = _df_mes(df_d, avui.year, avui.month)
    if df_actual.empty:
        return []

    cats_actual: dict[str, float] = {
        str(cat): abs(float(grp["quantitat"].sum()))
        for cat, grp in df_actual.groupby("categoria")
    }

    # Acumular despeses per categoria per cada mes d'historial (zeros si no n'hi ha)
    hist: dict[str, list[float]] = {cat: [] for cat in cats_actual}
    for any_, mes in mesos_prev:
        df_m = _df_mes(df_d, any_, mes)
        despeses_m: dict[str, float] = {}
        if not df_m.empty:
            for cat, grp in df_m.groupby("categoria"):
                despeses_m[str(cat)] = abs(float(grp["quantitat"].sum()))
        for cat in cats_actual:
            hist[cat].append(despeses_m.get(cat, 0.0))

    resultat: list[dict] = []
    for cat, total_actual in cats_actual.items():
        vals = hist[cat]
        if not vals:
            continue
        mitjana = sum(vals) / len(vals)
        if mitjana == 0:
            continue

        actual_norm = normalitzar_a_mes_complet(total_actual, avui)
        variacio_pct = ((actual_norm - mitjana) / mitjana) * 100

        if abs(variacio_pct) >= llindar_pct:
            resultat.append({
                "categoria": cat,
                "actual": round(total_actual, 2),
                "actual_normalitzat": round(actual_norm, 2),
                "mitjana_historic": round(mitjana, 2),
                "variacio_pct": round(variacio_pct, 1),
                "tipus": "augment" if variacio_pct > 0 else "reduccio",
            })

    resultat.sort(key=lambda x: abs(x["variacio_pct"]), reverse=True)
    return resultat


def despeses_individuals_atipiques(
    df: pd.DataFrame,
    avui: date,
    *,
    factor_mediana: float = 2.0,
    mesos_historic: int = 3,
) -> list[dict]:
    """Detecta despeses del mes actual que superen factor_mediana × mediana histórica.

    Retorna [{"data", "concepte", "establiment", "categoria",
              "quantitat", "mediana_categoria", "factor"}]
    """
    df_d = _filtrar_despeses(df)
    if df_d.empty:
        return []

    mesos_prev = _mesos_anteriors(avui, mesos_historic)
    if not mesos_prev:
        return []

    df_actual = _df_mes(df_d, avui.year, avui.month)
    if df_actual.empty:
        return []

    frames_hist = [_df_mes(df_d, a, m) for a, m in mesos_prev]
    df_hist = pd.concat([f for f in frames_hist if not f.empty], ignore_index=True) \
        if any(not f.empty for f in frames_hist) else pd.DataFrame()

    if df_hist.empty:
        return []

    resultat: list[dict] = []
    for cat in df_actual["categoria"].unique():
        df_cat_hist = df_hist[df_hist["categoria"] == cat]
        if df_cat_hist.empty:
            continue

        mediana = float(df_cat_hist["quantitat"].abs().median())
        if mediana == 0:
            continue

        df_cat_actual = df_actual[df_actual["categoria"] == cat]
        for _, row in df_cat_actual.iterrows():
            abs_q = abs(float(row["quantitat"]))
            factor = abs_q / mediana
            if factor > factor_mediana:
                resultat.append({
                    "data": row["data"],
                    "concepte": str(row.get("concepte", "")),
                    "establiment": str(row.get("establiment", "")),
                    "categoria": str(cat),
                    "quantitat": round(abs_q, 2),
                    "mediana_categoria": round(mediana, 2),
                    "factor": round(factor, 2),
                })

    resultat.sort(key=lambda x: x["factor"], reverse=True)
    return resultat


def categories_noves(
    df: pd.DataFrame,
    avui: date,
    *,
    mesos_historic: int = 3,
) -> list[dict]:
    """Detecta categories presents al mes actual però absents als N mesos previs.

    Retorna [{"categoria", "total", "moviments"}]
    """
    df_d = _filtrar_despeses(df)
    if df_d.empty:
        return []

    df_actual = _df_mes(df_d, avui.year, avui.month)
    if df_actual.empty:
        return []

    cats_actual: set[str] = set(df_actual["categoria"].astype(str))

    cats_historic: set[str] = set()
    for any_, mes in _mesos_anteriors(avui, mesos_historic):
        df_m = _df_mes(df_d, any_, mes)
        if not df_m.empty:
            cats_historic.update(df_m["categoria"].astype(str))

    noves = cats_actual - cats_historic
    if not noves:
        return []

    resultat: list[dict] = []
    for cat in noves:
        df_cat = df_actual[df_actual["categoria"].astype(str) == cat]
        resultat.append({
            "categoria": cat,
            "total": round(abs(float(df_cat["quantitat"].sum())), 2),
            "moviments": int(len(df_cat)),
        })

    resultat.sort(key=lambda x: x["total"], reverse=True)
    return resultat


def detectar_totes_anomalies(
    df: pd.DataFrame,
    avui: date,
    config_app: dict,
) -> dict:
    """Orquestrador: retorna {"variacions": [...], "individuals": [...], "noves": [...]}."""
    llindar_pct = float(config_app.get("llindar_anomalia_pct", 30.0))
    factor_med = float(config_app.get("factor_mediana_atipica", 2.0))
    return {
        "variacions": categories_amb_variacio(df, avui, llindar_pct=llindar_pct),
        "individuals": despeses_individuals_atipiques(df, avui, factor_mediana=factor_med),
        "noves": categories_noves(df, avui),
    }
