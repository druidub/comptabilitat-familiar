"""Tests per a core/anomalies.py."""
from datetime import date

import pandas as pd
import pytest

from core.anomalies import (
    categories_amb_variacio,
    categories_noves,
    despeses_individuals_atipiques,
    detectar_totes_anomalies,
    normalitzar_a_mes_complet,
)


def _mov(data: date, concepte: str, quantitat: float, categoria: str,
         establiment: str = "", tipus: str = "Despesa") -> dict:
    return {
        "data": data, "concepte": concepte, "establiment": establiment,
        "quantitat": quantitat, "categoria": categoria, "tipus": tipus,
    }


def _historic_alimentacio(import_mensual: float = 400.0) -> list[dict]:
    """3 mesos d'historial estable d'Alimentació (gener–març 2026)."""
    return [
        _mov(date(2026, mes, 15), "Supermercat", -import_mensual, "Alimentació")
        for mes in [1, 2, 3]
    ]


# ---------------------------------------------------------------------------
# normalitzar_a_mes_complet
# ---------------------------------------------------------------------------

def test_normalitzar_dia_5_abril():
    # Abril té 30 dies. Dia 5, 100€ → (100/5)*30 = 600
    resultat = normalitzar_a_mes_complet(100.0, date(2026, 4, 5))
    assert resultat == pytest.approx(600.0)


def test_normalitzar_dia_30_mes_complet():
    # Dia 30 d'un mes de 30 dies → sense canvi
    resultat = normalitzar_a_mes_complet(700.0, date(2026, 4, 30))
    assert resultat == pytest.approx(700.0)


def test_normalitzar_febrer():
    # Febrer 2026 té 28 dies. Dia 14, 200€ → (200/14)*28 = 400
    resultat = normalitzar_a_mes_complet(200.0, date(2026, 2, 14))
    assert resultat == pytest.approx(400.0)


# ---------------------------------------------------------------------------
# categories_amb_variacio
# ---------------------------------------------------------------------------

def test_categories_amb_variacio_augment_75pct():
    # Avui = 30 abril (mes complet), históric 400€, actual 700€ → +75%
    avui = date(2026, 4, 30)
    df = pd.DataFrame(_historic_alimentacio(400.0) + [
        _mov(date(2026, 4, 20), "Supermercat", -700.0, "Alimentació")
    ])
    resultat = categories_amb_variacio(df, avui, mesos_historic=3, llindar_pct=30.0)

    assert len(resultat) == 1
    r = resultat[0]
    assert r["categoria"] == "Alimentació"
    assert r["variacio_pct"] == pytest.approx(75.0, abs=0.5)
    assert r["tipus"] == "augment"
    assert r["mitjana_historic"] == pytest.approx(400.0)


def test_categories_amb_variacio_reduccio():
    avui = date(2026, 4, 30)
    df = pd.DataFrame(_historic_alimentacio(400.0) + [
        _mov(date(2026, 4, 20), "Supermercat", -200.0, "Alimentació")
    ])
    resultat = categories_amb_variacio(df, avui, mesos_historic=3, llindar_pct=30.0)

    assert len(resultat) == 1
    assert resultat[0]["tipus"] == "reduccio"
    assert resultat[0]["variacio_pct"] < 0


def test_categories_amb_variacio_normalitza_mes_incomplet():
    # Avui = dia 5 d'abril, gastat 100€, historic 400€/mes
    # Normalitzat = (100/5)*30 = 600 → variació = +50% (no -75%)
    avui = date(2026, 4, 5)
    df = pd.DataFrame(_historic_alimentacio(400.0) + [
        _mov(date(2026, 4, 3), "Supermercat", -100.0, "Alimentació")
    ])
    resultat = categories_amb_variacio(df, avui, mesos_historic=3, llindar_pct=30.0)

    assert len(resultat) == 1
    r = resultat[0]
    assert r["variacio_pct"] == pytest.approx(50.0, abs=1.0)
    assert r["tipus"] == "augment"


def test_categories_amb_variacio_sota_llindar_no_apareix():
    # 15% de variació, llindar 30% → no ha d'aparèixer
    avui = date(2026, 4, 30)
    df = pd.DataFrame(_historic_alimentacio(400.0) + [
        _mov(date(2026, 4, 20), "Supermercat", -460.0, "Alimentació")
    ])
    resultat = categories_amb_variacio(df, avui, mesos_historic=3, llindar_pct=30.0)
    assert resultat == []


def test_categories_amb_variacio_exclou_ingressos():
    # Nòmina amb tipus Ingrés no ha de generar anomalia
    avui = date(2026, 4, 30)
    moviments = _historic_alimentacio(400.0) + [
        _mov(date(2026, 4, 20), "Supermercat", -400.0, "Alimentació"),
        _mov(date(2026, 4, 1), "Nòmina", 2000.0, "Nòmina", tipus="Ingrés"),
    ]
    df = pd.DataFrame(moviments)
    resultat = categories_amb_variacio(df, avui)
    cats = [r["categoria"] for r in resultat]
    assert "Nòmina" not in cats


def test_categories_amb_variacio_df_buit():
    assert categories_amb_variacio(pd.DataFrame(), date(2026, 4, 15)) == []


def test_categories_amb_variacio_historial_insuficient_no_peta():
    # Menys mesos d'historial que els demanats → retorna llista, no peta
    avui = date(2026, 4, 30)
    df = pd.DataFrame([
        _mov(date(2026, 3, 15), "Supermercat", -400.0, "Alimentació"),
        _mov(date(2026, 4, 20), "Supermercat", -700.0, "Alimentació"),
    ])
    resultat = categories_amb_variacio(df, avui, mesos_historic=3, llindar_pct=30.0)
    assert isinstance(resultat, list)


# ---------------------------------------------------------------------------
# despeses_individuals_atipiques
# ---------------------------------------------------------------------------

def test_despeses_individuals_atipiques_detecta():
    # Historic: Restauració ~30€ per moviment; actual: 250€ → factor ≈ 8.3
    avui = date(2026, 4, 30)
    moviments = []
    for mes in [1, 2, 3]:
        for dia in [5, 15, 25]:
            moviments.append(_mov(date(2026, mes, dia), "Restaurant", -30.0, "Restauració"))
    moviments.append(_mov(date(2026, 4, 10), "Sopar gourmet", -250.0, "Restauració", "Restaurant Caríssim"))

    df = pd.DataFrame(moviments)
    resultat = despeses_individuals_atipiques(df, avui, factor_mediana=2.0, mesos_historic=3)

    assert len(resultat) == 1
    r = resultat[0]
    assert r["categoria"] == "Restauració"
    assert r["quantitat"] == pytest.approx(250.0)
    assert r["mediana_categoria"] == pytest.approx(30.0)
    assert r["factor"] == pytest.approx(250.0 / 30.0, abs=0.1)


def test_despeses_individuals_no_atipiques_no_apareixen():
    avui = date(2026, 4, 30)
    moviments = []
    for mes in [1, 2, 3]:
        moviments.append(_mov(date(2026, mes, 15), "Restaurant", -30.0, "Restauració"))
    moviments.append(_mov(date(2026, 4, 10), "Restaurant", -50.0, "Restauració"))  # 50/30 = 1.67 < 2

    df = pd.DataFrame(moviments)
    resultat = despeses_individuals_atipiques(df, avui, factor_mediana=2.0)
    assert resultat == []


def test_despeses_individuals_df_buit():
    assert despeses_individuals_atipiques(pd.DataFrame(), date(2026, 4, 15)) == []


# ---------------------------------------------------------------------------
# categories_noves
# ---------------------------------------------------------------------------

def test_categories_noves_detecta_roba():
    avui = date(2026, 4, 30)
    moviments = []
    for mes in [1, 2, 3]:
        moviments.append(_mov(date(2026, mes, 15), "Supermercat", -400.0, "Alimentació"))
        moviments.append(_mov(date(2026, mes, 10), "Bus", -50.0, "Transport"))
    moviments.append(_mov(date(2026, 4, 20), "Zara", -150.0, "Roba"))
    moviments.append(_mov(date(2026, 4, 22), "Supermercat", -400.0, "Alimentació"))

    df = pd.DataFrame(moviments)
    resultat = categories_noves(df, avui, mesos_historic=3)

    cats = [r["categoria"] for r in resultat]
    assert "Roba" in cats
    assert "Alimentació" not in cats
    assert "Transport" not in cats


def test_categories_noves_retorna_total_correcte():
    avui = date(2026, 4, 30)
    moviments = [
        _mov(date(2026, 4, 20), "Zara", -100.0, "Roba"),
        _mov(date(2026, 4, 25), "H&M", -60.0, "Roba"),
    ]
    df = pd.DataFrame(moviments)
    resultat = categories_noves(df, avui, mesos_historic=3)

    assert len(resultat) == 1
    assert resultat[0]["categoria"] == "Roba"
    assert resultat[0]["total"] == pytest.approx(160.0)
    assert resultat[0]["moviments"] == 2


def test_categories_noves_cap_si_totes_conegudes():
    avui = date(2026, 4, 30)
    moviments = _historic_alimentacio() + [
        _mov(date(2026, 4, 20), "Supermercat", -400.0, "Alimentació")
    ]
    df = pd.DataFrame(moviments)
    assert categories_noves(df, avui) == []


def test_categories_noves_df_buit():
    assert categories_noves(pd.DataFrame(), date(2026, 4, 15)) == []


# ---------------------------------------------------------------------------
# detectar_totes_anomalies — orquestrador
# ---------------------------------------------------------------------------

def test_detectar_totes_anomalies_estructura():
    avui = date(2026, 4, 30)
    df = pd.DataFrame(_historic_alimentacio() + [
        _mov(date(2026, 4, 20), "Supermercat", -700.0, "Alimentació")
    ])
    config_app = {"llindar_anomalia_pct": 30.0, "factor_mediana_atipica": 2.0}
    resultat = detectar_totes_anomalies(df, avui, config_app)

    assert "variacions" in resultat
    assert "individuals" in resultat
    assert "noves" in resultat
    assert isinstance(resultat["variacions"], list)
    assert len(resultat["variacions"]) >= 1


def test_detectar_totes_anomalies_df_buit():
    config_app = {"llindar_anomalia_pct": 30.0, "factor_mediana_atipica": 2.0}
    resultat = detectar_totes_anomalies(pd.DataFrame(), date(2026, 4, 15), config_app)
    assert resultat == {"variacions": [], "individuals": [], "noves": []}
