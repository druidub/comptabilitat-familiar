"""Tests per a core/config_autonom.py."""
from datetime import date
import pandas as pd
import pytest
from unittest.mock import MagicMock

from core.config_autonom import DEFAULTS, _carregar_config_raw, _coerce, es_mode_preview


# ---------------------------------------------------------------------------
# _coerce — conversió de tipus des de strings de Sheets
# ---------------------------------------------------------------------------

def test_coerce_bool_false_string():
    assert _coerce("False", "bool") is False

def test_coerce_bool_true_string():
    assert _coerce("TRUE", "bool") is True

def test_coerce_bool_true_lowercase():
    assert _coerce("true", "bool") is True

def test_coerce_float_valid():
    assert _coerce("1500.50", "float") == pytest.approx(1500.5)

def test_coerce_float_from_bool_string():
    assert _coerce("False", "float") == 0.0

def test_coerce_float_zero_string():
    assert _coerce("0", "float") == 0.0

def test_coerce_int_valid():
    assert _coerce("4", "int") == 4

def test_coerce_int_from_float_string():
    assert _coerce("3.9", "int") == 3

def test_coerce_date_valid():
    assert _coerce("2026-09-01", "date") == date(2026, 9, 1)

def test_coerce_date_invalid_returns_none():
    assert _coerce("not-a-date", "date") is None

def test_coerce_date_optional_empty():
    assert _coerce("", "date_optional") is None

def test_coerce_date_optional_nan():
    assert _coerce("nan", "date_optional") is None

def test_coerce_date_optional_valid():
    assert _coerce("2026-09-01", "date_optional") == date(2026, 9, 1)

def test_coerce_str_passthrough():
    assert _coerce("sollicitat", "str") == "sollicitat"


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

    # Ara retorna valors tipats, no strings crus
    assert config["data_alta_real"] == date(2026, 9, 1)
    assert config["iva_per_defecte"] is False


def test_carregar_config_fallback_defaults_si_sheet_buit():
    mock_conn = MagicMock()
    mock_conn.read.return_value = pd.DataFrame()

    config = _carregar_config_raw(mock_conn)

    # Els defaults passen per coerció, ja no són strings purs
    assert config["iva_per_defecte"] is True
    assert config["factures_aprox_mes"] == 4
    assert config["retencio_irpf_pct"] == pytest.approx(0.15)
    assert config["data_alta_real"] is None


def test_carregar_config_fallback_defaults_si_connexio_falla():
    mock_conn = MagicMock()
    mock_conn.read.side_effect = Exception("Sheets unavailable")

    config = _carregar_config_raw(mock_conn)

    assert config["iva_per_defecte"] is True
    assert config["tarifa_plana_prorrogada"] is False
    assert config["tiquet_rural_quantia"] == 0.0


def test_carregar_config_manté_defaults_per_claus_no_presents():
    df_mock = pd.DataFrame([
        {"clau": "data_alta_real", "valor": "2026-09-01"},
    ])
    mock_conn = MagicMock()
    mock_conn.read.return_value = df_mock

    config = _carregar_config_raw(mock_conn)

    # Default "TRUE" → True (bool tipat)
    assert config["iva_per_defecte"] is True
    assert config["factures_aprox_mes"] == 4


def test_carregar_config_valor_nan_es_buit():
    df_mock = pd.DataFrame([
        {"clau": "data_alta_real", "valor": float("nan")},
    ])
    mock_conn = MagicMock()
    mock_conn.read.return_value = df_mock

    config = _carregar_config_raw(mock_conn)

    # nan → date_optional → None
    assert config["data_alta_real"] is None
    assert es_mode_preview(config) is True
