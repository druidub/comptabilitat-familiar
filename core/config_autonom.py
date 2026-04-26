"""Configuració de l'autònom — pestanya Config_Autonom de Google Sheets."""
from __future__ import annotations

import gspread
import pandas as pd
import streamlit as st

PESTANYA = "Config_Autonom"

DEFAULTS: dict[str, str] = {
    "data_alta_prevista": "2026-09-01",
    "data_alta_real": "",
    "tarifa_plana_prorrogada": "FALSE",
    "iva_per_defecte": "TRUE",
    "factures_aprox_mes": "4",
    "retencio_irpf_pct": "0.15",
    "tiquet_rural_estat": "sollicitat",
    "tiquet_rural_quantia": "0",
    "tiquet_rural_data_resolucio": "",
}


def _spreadsheet(conn):
    """Retorna l'objecte gspread Spreadsheet via l'API nativa."""
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    try:
        # streamlit-gsheets >= 0.0.9: conn.client.client és el gspread.Client
        return conn.client.client.open_by_url(url)
    except AttributeError:
        # fallback per a versions anteriors
        return conn.client._open_spreadsheet_url(url)


def _col_letter(n: int) -> str:
    """Índex de columna 1-based → lletra Excel (A, B, ..., Z, AA, ...)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _assegurar_pestanya(conn) -> None:
    """Crea Config_Autonom al Sheet si no existeix (operació d'esquema via gspread)."""
    sh = _spreadsheet(conn)
    try:
        sh.worksheet(PESTANYA)
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=PESTANYA, rows=20, cols=2)


def _assegurar_columna_aplica_iva(conn) -> None:
    """Afegeix aplica_iva a la pestanya principal si no existeix (gspread natiu)."""
    sh = _spreadsheet(conn)
    ws = sh.get_worksheet(0)
    capçaleres = ws.row_values(1)
    if "aplica_iva" in capçaleres:
        return
    nova_col = len(capçaleres) + 1
    lletra = _col_letter(nova_col)
    ws.update_cell(1, nova_col, "aplica_iva")
    n_files = len(ws.get_all_values()) - 1
    if n_files > 0:
        ws.update(
            f"{lletra}2:{lletra}{n_files + 1}",
            [["FALSE"]] * n_files,
        )


def _carregar_config_raw(conn) -> dict:
    """Llegeix Config_Autonom i retorna un dict clau→valor. Sense cache — testable."""
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is None or df.empty or "clau" not in df.columns:
            return DEFAULTS.copy()
        config = DEFAULTS.copy()
        for _, row in df.iterrows():
            clau = str(row.get("clau", "")).strip()
            valor_raw = row.get("valor", "")
            valor = "" if str(valor_raw) in ("nan", "None") else str(valor_raw).strip()
            if clau:
                config[clau] = valor
        return config
    except Exception:
        return DEFAULTS.copy()


@st.cache_data(ttl=60)
def carregar_config(_conn) -> dict:
    """Llegeix Config_Autonom (cached 60s). Usa _conn per evitar hashing de connexió."""
    return _carregar_config_raw(_conn)


def guardar_config(conn, config: dict) -> None:
    """Escriu el dict config a Config_Autonom com a taula clau/valor."""
    files = [{"clau": k, "valor": v} for k, v in config.items()]
    conn.update(worksheet=PESTANYA, data=pd.DataFrame(files))
    st.cache_data.clear()


def inicialitzar_config(conn) -> None:
    """Crea Config_Autonom (si cal) i omple els defaults."""
    _assegurar_pestanya(conn)
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is not None and not df.empty and "clau" in df.columns:
            return
    except Exception:
        pass
    guardar_config(conn, DEFAULTS.copy())


def es_mode_preview(config: dict) -> bool:
    """Retorna True si data_alta_real és buida o absent (mode preview)."""
    val = config.get("data_alta_real")
    if val is None:
        return True
    return str(val).strip() == ""
