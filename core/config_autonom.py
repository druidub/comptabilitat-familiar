"""Configuració de l'autònom — pestanya Config_Autonom de Google Sheets."""
from __future__ import annotations

from datetime import date
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

# Tipus esperat per a cada clau — Sheets retorna tot com a string
TIPUS_CONFIG: dict[str, str] = {
    "data_alta_prevista": "date",
    "data_alta_real": "date_optional",
    "tarifa_plana_prorrogada": "bool",
    "iva_per_defecte": "bool",
    "factures_aprox_mes": "int",
    "retencio_irpf_pct": "float",
    "tiquet_rural_estat": "str",
    "tiquet_rural_quantia": "float",
    "tiquet_rural_data_resolucio": "date_optional",
}


def _coerce(valor, tipus: str):
    """Converteix un valor llegit de Sheets al tipus Python esperat."""
    s = str(valor).strip()
    if tipus == "bool":
        return s.lower() in ("true", "1", "yes", "sí", "si")
    if tipus == "int":
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0
    if tipus == "float":
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0
    if tipus == "date":
        try:
            return date.fromisoformat(s)
        except (ValueError, TypeError):
            return None
    if tipus == "date_optional":
        if not s or s.lower() in ("none", "nan", ""):
            return None
        try:
            return date.fromisoformat(s)
        except (ValueError, TypeError):
            return None
    return s  # str per defecte


def _spreadsheet(conn):
    """Retorna el gspread.Spreadsheet via l'API oficial del connector."""
    return conn.client._open_spreadsheet()


def _col_letter(n: int) -> str:
    """Índex de columna 1-based → lletra Excel (A, B, ..., Z, AA, ...)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


@st.cache_resource(show_spinner=False)
def _assegurar_pestanya(_conn) -> bool:
    """Crea Config_Autonom si no existeix. Cached per sessió: s'executa un sol cop."""
    sh = _conn.client._open_spreadsheet()
    try:
        sh.worksheet(PESTANYA)
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=PESTANYA, rows=20, cols=2)
    return True


@st.cache_resource(show_spinner=False)
def _assegurar_columna_aplica_iva(_conn) -> bool:
    """Afegeix aplica_iva a la pestanya principal si no existeix. Cached per sessió."""
    sh = _conn.client._open_spreadsheet()
    ws = sh.get_worksheet(0)
    capçaleres = ws.row_values(1)
    if "aplica_iva" in capçaleres:
        return True
    nova_col = len(capçaleres) + 1
    lletra = _col_letter(nova_col)
    ws.update_cell(1, nova_col, "aplica_iva")
    n_files = len(ws.get_all_values()) - 1
    if n_files > 0:
        ws.update(
            f"{lletra}2:{lletra}{n_files + 1}",
            [["FALSE"]] * n_files,
        )
    return True


def _carregar_config_raw(conn) -> dict:
    """Llegeix Config_Autonom, retorna dict amb valors tipats. Sense cache — testable."""
    try:
        df = conn.read(worksheet=PESTANYA, ttl=0)
        if df is None or df.empty or "clau" not in df.columns:
            return _config_tipada(DEFAULTS)
        config_cru = DEFAULTS.copy()
        for _, row in df.iterrows():
            clau = str(row.get("clau", "")).strip()
            valor_raw = row.get("valor", "")
            valor = "" if str(valor_raw) in ("nan", "None") else str(valor_raw).strip()
            if clau:
                config_cru[clau] = valor
        return _config_tipada(config_cru)
    except Exception:
        return _config_tipada(DEFAULTS)


def _config_tipada(config_cru: dict) -> dict:
    """Aplica coerció de tipus a cada clau coneguda; les desconegudes passen com a str."""
    return {
        clau: _coerce(config_cru.get(clau, ""), TIPUS_CONFIG.get(clau, "str"))
        for clau in TIPUS_CONFIG
    }


@st.cache_data(ttl=300)
def carregar_config(_conn) -> dict:
    """Llegeix Config_Autonom (cached 60s). Usa _conn per evitar hashing de connexió."""
    return _carregar_config_raw(_conn)


def guardar_config(conn, config: dict) -> None:
    """Serialitza config a strings i escriu a Config_Autonom."""
    def _ser(v) -> str:
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, date):
            return v.isoformat()
        if v is None:
            return ""
        return str(v)

    files = [{"clau": k, "valor": _ser(v)} for k, v in config.items()]
    conn.update(worksheet=PESTANYA, data=pd.DataFrame(files))
    st.cache_data.clear()


def inicialitzar_config(conn) -> None:
    """Crea Config_Autonom (si cal) i omple els defaults. Schema cached per sessió."""
    _assegurar_pestanya(conn)
    try:
        df = conn.read(worksheet=PESTANYA, ttl=300)
        if df is not None and not df.empty and "clau" in df.columns:
            return
    except Exception:
        pass
    guardar_config(conn, DEFAULTS.copy())


def es_mode_preview(config: dict) -> bool:
    """Retorna True si data_alta_real és buida o absent (mode preview)."""
    val = config.get("data_alta_real")
    return val is None or (isinstance(val, str) and val.strip() == "")
