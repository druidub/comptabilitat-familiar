"""Configuració general de l'app — pestanya Config_App de Google Sheets."""
from __future__ import annotations

import gspread
import pandas as pd
import streamlit as st

from core.config_autonom import _coerce

PESTANYA = "Config_App"

DEFAULTS: dict[str, str] = {
    "llindar_alerta_saldo": "500",
    "horitzo_projeccio_dies": "60",
    "llindar_anomalia_pct": "30.0",
    "factor_mediana_atipica": "2.0",
}

TIPUS_CONFIG_APP: dict[str, str] = {
    "llindar_alerta_saldo": "float",
    "horitzo_projeccio_dies": "int",
    "llindar_anomalia_pct": "float",
    "factor_mediana_atipica": "float",
}


def _spreadsheet(conn):
    return conn.client._open_spreadsheet()


@st.cache_resource(show_spinner=False)
def _assegurar_pestanya_config_app(_conn) -> bool:
    """Crea la pestanya Config_App si no existeix. Cached per sessió."""
    sh = _conn.client._open_spreadsheet()
    try:
        sh.worksheet(PESTANYA)
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=PESTANYA, rows=10, cols=2)
    return True


def _carregar_config_app_raw(conn) -> dict:
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is None or df.empty or "clau" not in df.columns:
            return _config_app_tipada(DEFAULTS)
        config_cru = DEFAULTS.copy()
        for _, row in df.iterrows():
            clau = str(row.get("clau", "")).strip()
            valor_raw = row.get("valor", "")
            valor = "" if str(valor_raw) in ("nan", "None") else str(valor_raw).strip()
            if clau:
                config_cru[clau] = valor
        return _config_app_tipada(config_cru)
    except Exception:
        return _config_app_tipada(DEFAULTS)


def _config_app_tipada(config_cru: dict) -> dict:
    return {
        clau: _coerce(config_cru.get(clau, ""), TIPUS_CONFIG_APP.get(clau, "str"))
        for clau in TIPUS_CONFIG_APP
    }


@st.cache_data(ttl=300)
def carregar_config_app(_conn) -> dict:
    return _carregar_config_app_raw(_conn)


def guardar_config_app(conn, config: dict) -> None:
    files = [{"clau": k, "valor": str(v)} for k, v in config.items()]
    conn.update(worksheet=PESTANYA, data=pd.DataFrame(files))
    st.cache_data.clear()


def inicialitzar_config_app(conn) -> None:
    _assegurar_pestanya_config_app(conn)
    try:
        df = conn.read(worksheet=PESTANYA, ttl=300)
        if df is not None and not df.empty and "clau" in df.columns:
            return
    except Exception:
        pass
    guardar_config_app(conn, DEFAULTS.copy())
