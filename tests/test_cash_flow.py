"""Tests per a core/cash_flow.py."""
from datetime import date, timedelta

import pandas as pd
import pytest

from core.cash_flow import (
    detectar_alertes_saldo,
    projectar_saldo,
    proximes_ocurrencies,
    saldo_minim_previst,
)


# ---------------------------------------------------------------------------
# proximes_ocurrencies — Mensual
# ---------------------------------------------------------------------------

def test_mensual_dia_15():
    result = proximes_ocurrencies(
        {"frequencia": "Mensual", "dia": 15},
        date(2026, 4, 26),
        date(2026, 7, 26),
    )
    assert result == [date(2026, 5, 15), date(2026, 6, 15), date(2026, 7, 15)]


def test_mensual_dia_31_ajusta_al_darrer_dia():
    result = proximes_ocurrencies(
        {"frequencia": "Mensual", "dia": 31},
        date(2026, 1, 15),
        date(2026, 3, 31),
    )
    assert result == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_mensual_avui_mateix_dia_inclou():
    # Si avui és el dia configurat, l'inclou
    result = proximes_ocurrencies(
        {"frequencia": "Mensual", "dia": 26},
        date(2026, 4, 26),
        date(2026, 5, 26),
    )
    assert date(2026, 4, 26) in result
    assert date(2026, 5, 26) in result


# ---------------------------------------------------------------------------
# proximes_ocurrencies — Trimestral
# ---------------------------------------------------------------------------

def test_trimestral_tres_ocurrencies():
    result = proximes_ocurrencies(
        {"frequencia": "Trimestral", "dia": 1},
        date(2026, 4, 26),
        date(2026, 12, 31),
    )
    # Apr 1 < Apr 26 → primera és May 1, després Aug 1, Nov 1
    assert len(result) == 3
    assert result[0] == date(2026, 5, 1)
    assert result[1] == date(2026, 8, 1)
    assert result[2] == date(2026, 11, 1)


# ---------------------------------------------------------------------------
# proximes_ocurrencies — Setmanal
# ---------------------------------------------------------------------------

def test_setmanal_tots_els_dilluns():
    # 2026-04-26 és diumenge, el primer dilluns és 2026-04-27
    result = proximes_ocurrencies(
        {"frequencia": "Setmanal", "dia": 1},
        date(2026, 4, 26),
        date(2026, 5, 26),
    )
    expected = [
        date(2026, 4, 27),
        date(2026, 5, 4),
        date(2026, 5, 11),
        date(2026, 5, 18),
        date(2026, 5, 25),
    ]
    assert result == expected
    # Tots han de ser dilluns (weekday 0)
    assert all(d.weekday() == 0 for d in result)


def test_setmanal_avui_es_el_dia_target():
    # 2026-04-27 és dilluns, ha d'incloure avui
    result = proximes_ocurrencies(
        {"frequencia": "Setmanal", "dia": 1},
        date(2026, 4, 27),
        date(2026, 5, 4),
    )
    assert result[0] == date(2026, 4, 27)
    assert result[1] == date(2026, 5, 4)


# ---------------------------------------------------------------------------
# projectar_saldo
# ---------------------------------------------------------------------------

def test_projectar_saldo_creix_correctament():
    avui = date(2026, 4, 26)
    recurrents = [
        {"nom": "Nòmina", "import": 1300.0, "frequencia": "Mensual", "dia": 1},
        {"nom": "Lloguer", "import": -550.0, "frequencia": "Mensual", "dia": 5},
    ]
    df = projectar_saldo(1000.0, recurrents, avui, dies=60)

    assert list(df.columns) == ["data", "saldo_previst", "esdeveniment"]
    assert len(df) == 61  # avui + 60 dies

    # Dia 1 de maig: +1300 → saldo 2300
    fila_may1 = df[df["data"] == date(2026, 5, 1)].iloc[0]
    assert fila_may1["saldo_previst"] == pytest.approx(2300.0)
    assert "Nòmina" in fila_may1["esdeveniment"]

    # Dia 5 de maig: -550 → saldo 1750
    fila_may5 = df[df["data"] == date(2026, 5, 5)].iloc[0]
    assert fila_may5["saldo_previst"] == pytest.approx(1750.0)

    # Dia 1 de juny: +1300 → saldo 3050
    fila_jun1 = df[df["data"] == date(2026, 6, 1)].iloc[0]
    assert fila_jun1["saldo_previst"] == pytest.approx(3050.0)

    # Dia 5 de juny: -550 → saldo 2500 > 1000 inicial
    fila_jun5 = df[df["data"] == date(2026, 6, 5)].iloc[0]
    assert fila_jun5["saldo_previst"] == pytest.approx(2500.0)
    assert fila_jun5["saldo_previst"] > 1000.0


def test_projectar_saldo_sense_recurrents():
    avui = date(2026, 4, 26)
    df = projectar_saldo(500.0, [], avui, dies=10)
    assert (df["saldo_previst"] == 500.0).all()
    assert (df["esdeveniment"] == "").all()


# ---------------------------------------------------------------------------
# detectar_alertes_saldo
# ---------------------------------------------------------------------------

def test_detectar_alertes_periode_consecutiu():
    # Saldo baixa de 500€ entre 10–15 de maig → 1 alerta agrupada
    avui = date(2026, 5, 1)
    dates = [avui + timedelta(days=i) for i in range(30)]
    saldos = []
    for d in dates:
        if date(2026, 5, 10) <= d <= date(2026, 5, 15):
            saldos.append(350.0)
        else:
            saldos.append(800.0)

    df = pd.DataFrame({
        "data": dates,
        "saldo_previst": saldos,
        "esdeveniment": [""] * 30,
    })

    alertes = detectar_alertes_saldo(df, llindar=500.0)

    assert len(alertes) == 1
    alerta = alertes[0]
    assert alerta["data"] == date(2026, 5, 10)
    assert alerta["saldo"] == pytest.approx(350.0)
    assert "10/05/2026" in alerta["missatge"]
    assert "15/05/2026" in alerta["missatge"]


def test_detectar_alertes_cap_si_sobre_llindar():
    df = pd.DataFrame({
        "data": [date(2026, 5, 1), date(2026, 5, 2)],
        "saldo_previst": [600.0, 700.0],
        "esdeveniment": ["", ""],
    })
    assert detectar_alertes_saldo(df, llindar=500.0) == []


def test_detectar_alertes_dies_no_consecutius_dos_alertes():
    # Dos períodes separats → 2 alertes
    dates = [date(2026, 5, i) for i in range(1, 11)]
    saldos = [300.0 if d.day in (3, 7) else 800.0 for d in dates]
    df = pd.DataFrame({"data": dates, "saldo_previst": saldos, "esdeveniment": [""] * 10})
    alertes = detectar_alertes_saldo(df, llindar=500.0)
    assert len(alertes) == 2


# ---------------------------------------------------------------------------
# saldo_minim_previst
# ---------------------------------------------------------------------------

def test_saldo_minim_previst():
    df = pd.DataFrame({
        "data": [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)],
        "saldo_previst": [800.0, 200.0, 600.0],
        "esdeveniment": ["", "", ""],
    })
    data_min, valor_min = saldo_minim_previst(df)
    assert data_min == date(2026, 5, 2)
    assert valor_min == pytest.approx(200.0)
