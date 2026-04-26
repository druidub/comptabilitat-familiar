"""Configuració de l'autònom — pestanya Config_Autonom de Google Sheets."""
from __future__ import annotations

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
    """Crea la pestanya Config_Autonom amb defaults si no existeix o és buida."""
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is not None and not df.empty:
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
