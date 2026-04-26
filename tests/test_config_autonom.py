"""Tests per a core/config_autonom.py."""
import pandas as pd
import pytest
from unittest.mock import MagicMock

from core.config_autonom import DEFAULTS, _carregar_config_raw, es_mode_preview


# ---------------------------------------------------------------------------
# es_mode_preview — funció pura, sense Sheets
# ---------------------------------------------------------------------------

def test_es_mode_preview_buit():
    assert es_mode_preview({"data_alta_real": ""}) is True


def test_es_mode_preview_clau_absent():
    assert es_mode_preview({}) is True


def test_es_mode_preview_none_explicit():
    assert es_mode_preview({"data_alta_real": None}) is True


def test_es_mode_preview_amb_data():
    assert es_mode_preview({"data_alta_real": "2026-09-01"}) is False


def test_es_mode_preview_amb_data_qualsevol():
    assert es_mode_preview({"data_alta_real": "2025-01-15"}) is False


# ---------------------------------------------------------------------------
# _carregar_config_raw — mock de Sheets
# ---------------------------------------------------------------------------

def test_carregar_config_llegeix_clau_valor():
    df_mock = pd.DataFrame([
        {"clau": "data_alta_real", "valor": "2026-09-01"},
        {"clau": "iva_per_defecte", "valor": "FALSE"},
    ])
    mock_conn = MagicMock()
    mock_conn.read.return_value = df_mock

    config = _carregar_config_raw(mock_conn)

    assert config["data_alta_real"] == "2026-09-01"
    assert config["iva_per_defecte"] == "FALSE"


def test_carregar_config_fallback_defaults_si_sheet_buit():
    mock_conn = MagicMock()
    mock_conn.read.return_value = pd.DataFrame()

    config = _carregar_config_raw(mock_conn)

    assert config == DEFAULTS


def test_carregar_config_fallback_defaults_si_connexio_falla():
    mock_conn = MagicMock()
    mock_conn.read.side_effect = Exception("Sheets unavailable")

    config = _carregar_config_raw(mock_conn)

    assert config == DEFAULTS


def test_carregar_config_manté_defaults_per_claus_no_presents():
    df_mock = pd.DataFrame([
        {"clau": "data_alta_real", "valor": "2026-09-01"},
    ])
    mock_conn = MagicMock()
    mock_conn.read.return_value = df_mock

    config = _carregar_config_raw(mock_conn)

    assert config["iva_per_defecte"] == DEFAULTS["iva_per_defecte"]
    assert config["factures_aprox_mes"] == DEFAULTS["factures_aprox_mes"]


def test_carregar_config_valor_nan_es_buit():
    df_mock = pd.DataFrame([
        {"clau": "data_alta_real", "valor": float("nan")},
    ])
    mock_conn = MagicMock()
    mock_conn.read.return_value = df_mock

    config = _carregar_config_raw(mock_conn)

    assert config["data_alta_real"] == ""
    assert es_mode_preview(config) is True
