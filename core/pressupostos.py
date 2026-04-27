"""Pressupostos mensuals per categoria — pestanya Pressupostos de Google Sheets."""
from __future__ import annotations

import calendar
from datetime import date

import gspread
import pandas as pd
import streamlit as st

PESTANYA = "Pressupostos"

CATEGORIES_DESPESA = [
    "Alimentació",
    "Transport",
    "Habitatge",
    "Salut",
    "Oci",
    "Roba",
    "Educació",
    "Altres_Despesa",
]

FILES_INICIALS: dict[str, float] = {cat: 0.0 for cat in CATEGORIES_DESPESA}


def _spreadsheet(conn):
    return conn.client._open_spreadsheet()


@st.cache_resource(show_spinner=False)
def _assegurar_pestanya_pressupostos(_conn) -> bool:
    """Crea la pestanya Pressupostos si no existeix. Cached per sessió."""
    sh = _conn.client._open_spreadsheet()
    try:
        sh.worksheet(PESTANYA)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=PESTANYA, rows=20, cols=2)
        ws.update_cell(1, 1, "categoria")
        ws.update_cell(1, 2, "import_mensual")
    return True


def inicialitzar_pressupostos(conn) -> None:
    _assegurar_pestanya_pressupostos(conn)
    try:
        df = conn.read(worksheet=PESTANYA, ttl=300)
        if df is not None and not df.empty and "categoria" in df.columns:
            return
    except Exception:
        pass
    guardar_pressupostos(conn, FILES_INICIALS.copy())


def _carregar_pressupostos_raw(conn) -> dict[str, float]:
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is None or df.empty or "categoria" not in df.columns:
            return FILES_INICIALS.copy()
        result = FILES_INICIALS.copy()
        for _, row in df.iterrows():
            cat = str(row.get("categoria", "")).strip()
            val_raw = row.get("import_mensual", 0)
            try:
                val = float(val_raw)
            except (ValueError, TypeError):
                val = 0.0
            if cat in result:
                result[cat] = val
        return result
    except Exception:
        return FILES_INICIALS.copy()


@st.cache_data(ttl=300)
def carregar_pressupostos(_conn) -> dict[str, float]:
    return _carregar_pressupostos_raw(_conn)


def guardar_pressupostos(conn, pressupostos: dict[str, float]) -> None:
    files = [{"categoria": k, "import_mensual": v} for k, v in pressupostos.items()]
    conn.update(worksheet=PESTANYA, data=pd.DataFrame(files))
    st.cache_data.clear()


def estat_pressupost(
    despesa_actual: float,
    import_mensual: float,
    dia_del_mes: int,
    dies_del_mes: int,
) -> dict:
    """Retorna l'estat 'per ritme' d'una categoria.

    Returns:
        dict amb claus: estat, pct_consumit, pct_esperat, ratio, restant
    """
    if import_mensual <= 0:
        return {
            "estat": "sense_pressupost",
            "pct_consumit": None,
            "pct_esperat": None,
            "ratio": None,
            "restant": None,
        }

    pct_consumit = despesa_actual / import_mensual
    pct_esperat = dia_del_mes / dies_del_mes

    if pct_consumit >= 1.0:
        estat = "vermell"
    else:
        ratio = pct_consumit / pct_esperat if pct_esperat > 0 else 0.0
        if ratio < 0.85:
            estat = "verd"
        elif ratio < 1.10:
            estat = "groc"
        else:
            estat = "vermell"

    ratio_final = (pct_consumit / pct_esperat) if pct_esperat > 0 else 0.0
    return {
        "estat": estat,
        "pct_consumit": pct_consumit,
        "pct_esperat": pct_esperat,
        "ratio": ratio_final,
        "restant": import_mensual - despesa_actual,
    }


def calcular_estats_categoria(
    df_mes_actual: pd.DataFrame,
    pressupostos: dict[str, float],
    avui: date,
) -> dict[str, dict]:
    """Calcula l'estat de cada categoria per al mes actual.

    Args:
        df_mes_actual: DataFrame filtrat pel mes en curs (columna 'categoria' i 'import')
        pressupostos: dict categoria → import mensual
        avui: data d'avui (per calcular dia_del_mes i dies_del_mes)

    Returns:
        dict categoria → estat_pressupost(...)
    """
    dies_del_mes = calendar.monthrange(avui.year, avui.month)[1]
    dia_del_mes = avui.day

    despeses_per_cat: dict[str, float] = {}
    if not df_mes_actual.empty and "categoria" in df_mes_actual.columns:
        for cat, grup in df_mes_actual.groupby("categoria"):
            despeses_per_cat[str(cat)] = abs(float(grup["quantitat"].sum()))

    return {
        cat: estat_pressupost(
            despesa_actual=despeses_per_cat.get(cat, 0.0),
            import_mensual=pressupostos.get(cat, 0.0),
            dia_del_mes=dia_del_mes,
            dies_del_mes=dies_del_mes,
        )
        for cat in CATEGORIES_DESPESA
    }
