"""Tests per a core/pressupostos.py."""
import pandas as pd
import pytest

from core.pressupostos import estat_pressupost, calcular_estats_categoria, CATEGORIES_DESPESA


# ---------------------------------------------------------------------------
# estat_pressupost — lògica "per ritme"
# ---------------------------------------------------------------------------

def test_sense_pressupost_quan_import_zero():
    r = estat_pressupost(0.0, 0.0, 15, 30)
    assert r["estat"] == "sense_pressupost"
    assert r["pct_consumit"] is None


def test_verd_quan_per_sota_ritme():
    # Dia 15/30 (50% esperat), gastats 40% → ratio 0.80 < 0.85 → verd
    r = estat_pressupost(despesa_actual=40.0, import_mensual=100.0, dia_del_mes=15, dies_del_mes=30)
    assert r["estat"] == "verd"
    assert r["pct_consumit"] == pytest.approx(0.4)
    assert r["pct_esperat"] == pytest.approx(0.5)


def test_groc_quan_ritme_acceptable():
    # Dia 15/30 (50% esperat), gastats 48% → ratio 0.96 ∈ [0.85, 1.10) → groc
    r = estat_pressupost(despesa_actual=48.0, import_mensual=100.0, dia_del_mes=15, dies_del_mes=30)
    assert r["estat"] == "groc"


def test_vermell_quan_supera_ritme():
    # Dia 15/30 (50% esperat), gastats 60% → ratio 1.20 ≥ 1.10 → vermell
    r = estat_pressupost(despesa_actual=60.0, import_mensual=100.0, dia_del_mes=15, dies_del_mes=30)
    assert r["estat"] == "vermell"


def test_vermell_quan_supera_100_pct():
    # 110€ gastat de 100€ pressupost → pct_consumit ≥ 1.0 → always vermell
    r = estat_pressupost(despesa_actual=110.0, import_mensual=100.0, dia_del_mes=10, dies_del_mes=30)
    assert r["estat"] == "vermell"


def test_restant_calcul_correcte():
    r = estat_pressupost(despesa_actual=30.0, import_mensual=100.0, dia_del_mes=10, dies_del_mes=31)
    assert r["restant"] == pytest.approx(70.0)


def test_ratio_calcul_correcte():
    # 40% consumit / 50% esperat = 0.80
    r = estat_pressupost(despesa_actual=40.0, import_mensual=100.0, dia_del_mes=15, dies_del_mes=30)
    assert r["ratio"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# calcular_estats_categoria — integració amb DataFrame
# ---------------------------------------------------------------------------

def test_calcular_estats_categories_buides():
    from datetime import date
    df = pd.DataFrame(columns=["categoria", "import"])
    pressupostos = {cat: 200.0 for cat in CATEGORIES_DESPESA}
    estats = calcular_estats_categoria(df, pressupostos, date(2026, 4, 15))
    # Tots han de tenir pct_consumit == 0.0 i estat verd (0% / ~48% esperat = ratio 0)
    for cat in CATEGORIES_DESPESA:
        assert estats[cat]["estat"] == "verd"
        assert estats[cat]["pct_consumit"] == pytest.approx(0.0)


def test_calcular_estats_categoria_amb_dades():
    from datetime import date
    df = pd.DataFrame([
        {"categoria": "Alimentació", "import": -80.0},
        {"categoria": "Transport", "import": -10.0},
    ])
    pressupostos = {"Alimentació": 100.0, "Transport": 100.0}
    # Dia 15 d'abril (30 dies) → 50% esperat
    estats = calcular_estats_categoria(df, pressupostos, date(2026, 4, 15))
    # Alimentació: 80% consumit / 50% esperat = ratio 1.60 → vermell
    assert estats["Alimentació"]["estat"] == "vermell"
    # Transport: 10% consumit / 50% esperat = ratio 0.20 → verd
    assert estats["Transport"]["estat"] == "verd"


def test_calcular_estats_categoria_sense_pressupost():
    from datetime import date
    df = pd.DataFrame([{"categoria": "Oci", "import": -50.0}])
    pressupostos = {cat: 0.0 for cat in CATEGORIES_DESPESA}
    estats = calcular_estats_categoria(df, pressupostos, date(2026, 4, 15))
    assert estats["Oci"]["estat"] == "sense_pressupost"
