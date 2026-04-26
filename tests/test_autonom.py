"""Tests per a core/autonom.py — càlculs fiscals autònom 2026."""
import pytest
from datetime import date

from core.autonom import (
    TARIFA_PLANA_AMB_MEI,
    TAULA_TRAMS_2026,
    BuffersTrimestre,
    ProvisioFiscal,
    Tram,
    calcular_buffers_trimestre,
    calcular_provisio_freelance,
    calcular_quota_ss,
    proxim_venciment,
    rendiment_net_mensual,
    tarifa_plana_estat,
    tram_actual,
    trimestre_de,
)


# ---------------------------------------------------------------------------
# tram_actual
# ---------------------------------------------------------------------------

def test_tram_actual_800():
    t = tram_actual(800)
    assert t.numero == 2
    assert t.quota_minima == 220.0


def test_tram_actual_2500():
    t = tram_actual(2500)
    assert t.numero == 10
    assert t.quota_minima == 423.0


def test_tram_actual_7000():
    t = tram_actual(7000)
    assert t.numero == 15
    assert t.quota_minima == 590.0


def test_tram_actual_zero():
    t = tram_actual(0)
    assert t.numero == 1


def test_tram_actual_limit_exacte_670():
    # 670 és el límit superior del tram 1 (≤670)
    t = tram_actual(670.0)
    assert t.numero == 1


def test_tram_actual_cobreix_tots_els_trams():
    # Cada tram ha de ser assolible
    mostres = [300, 800, 1000, 1200, 1400, 1600, 1750, 1900, 2100,
               2500, 2900, 3400, 3800, 5000, 8000]
    numeros = [tram_actual(v).numero for v in mostres]
    assert numeros == list(range(1, 16))


# ---------------------------------------------------------------------------
# calcular_provisio_freelance
# ---------------------------------------------------------------------------

def test_provisio_amb_iva_i_retencio_15():
    p = calcular_provisio_freelance(
        1000.0,
        aplica_iva=True,
        retencio_irpf_pct=0.15,
    )
    assert p.iva_repercutit == pytest.approx(210.0)
    assert p.irpf_provisio == pytest.approx(50.0)   # 200 - 150 retingut
    assert p.net_disponible == pytest.approx(717.84, abs=0.01)


def test_provisio_sense_iva_sense_retencio():
    p = calcular_provisio_freelance(
        1000.0,
        aplica_iva=False,
        retencio_irpf_pct=0.0,
    )
    assert p.iva_repercutit == 0.0
    assert p.irpf_provisio == pytest.approx(200.0)
    assert p.cuota_ss_provisio == pytest.approx(TARIFA_PLANA_AMB_MEI / 4, abs=0.01)


def test_provisio_retencio_cobreix_irpf():
    # Retenció ≥ 20%: irpf_provisio ha de ser 0
    p = calcular_provisio_freelance(
        1000.0,
        aplica_iva=False,
        retencio_irpf_pct=0.20,
    )
    assert p.irpf_provisio == 0.0


# ---------------------------------------------------------------------------
# tarifa_plana_estat
# ---------------------------------------------------------------------------

def test_tarifa_plana_activa_6_mesos_restants():
    estat = tarifa_plana_estat(date(2026, 5, 1), avui=date(2026, 11, 1))
    assert estat["activa"] is True
    assert estat["mesos_restants"] == 6
    assert estat["data_fi"] == date(2027, 5, 1)


def test_tarifa_plana_expirada():
    estat = tarifa_plana_estat(date(2025, 1, 1), avui=date(2026, 4, 26))
    assert estat["activa"] is False
    assert estat["mesos_restants"] == 0
    assert estat["data_fi"] == date(2026, 1, 1)


def test_tarifa_plana_amb_prorroga_24_mesos():
    estat = tarifa_plana_estat(
        date(2026, 1, 1),
        prorroga_activa=True,
        avui=date(2026, 6, 1),
    )
    assert estat["activa"] is True
    assert estat["data_fi"] == date(2028, 1, 1)
    assert estat["mesos_restants"] == 19


# ---------------------------------------------------------------------------
# proxim_venciment
# ---------------------------------------------------------------------------

def test_proxim_venciment_despres_q1():
    # 2026-04-26: el venciment Q1 (20 abril) ja ha passat → retorna Q2
    trim, data, dies = proxim_venciment(date(2026, 4, 26))
    assert trim == 2
    assert data == date(2026, 7, 20)
    assert dies == (date(2026, 7, 20) - date(2026, 4, 26)).days


def test_proxim_venciment_abans_q1():
    # 2026-04-15: el venciment Q1 (20 abril) encara no ha passat
    trim, data, dies = proxim_venciment(date(2026, 4, 15))
    assert trim == 1
    assert data == date(2026, 4, 20)
    assert dies == 5


def test_proxim_venciment_el_mateix_dia():
    # El dia del venciment ja s'ha passat (venciment > d és False)
    trim, data, dies = proxim_venciment(date(2026, 4, 20))
    assert trim == 2
    assert data == date(2026, 7, 20)


# ---------------------------------------------------------------------------
# trimestre_de
# ---------------------------------------------------------------------------

def test_trimestre_de_abril():
    assert trimestre_de(date(2026, 4, 26)) == 2


def test_trimestre_de_tots_els_mesos():
    esperat = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
    for mes, q in enumerate(esperat, start=1):
        assert trimestre_de(date(2026, mes, 15)) == q


# ---------------------------------------------------------------------------
# calcular_quota_ss
# ---------------------------------------------------------------------------

def test_quota_ss_tarifa_plana():
    q = calcular_quota_ss(800.0, tarifa_plana_activa=True)
    assert q == TARIFA_PLANA_AMB_MEI


def test_quota_ss_sense_tarifa_plana():
    q = calcular_quota_ss(800.0, tarifa_plana_activa=False)
    assert q == 220.0  # tram 2


# ---------------------------------------------------------------------------
# rendiment_net_mensual
# ---------------------------------------------------------------------------

def test_rendiment_net_mensual_exemple_skill():
    # Exemple de la skill: 12.000 ingressos, 1.200 despeses, 1.063,68 cuotes
    rnm = rendiment_net_mensual(12_000.0, 1_200.0, 1_063.68)
    assert rnm == pytest.approx(754.0, abs=2.0)


# ---------------------------------------------------------------------------
# calcular_buffers_trimestre
# ---------------------------------------------------------------------------

def test_buffers_trimestre_basic():
    moviments = [
        {"data": date(2026, 4, 10), "quantitat": 1000.0, "aplica_iva": True, "retencio_pct": 0.0},
        {"data": date(2026, 5, 15), "quantitat": 800.0,  "aplica_iva": True, "retencio_pct": 0.15},
        # Fora del trimestre 2 (aquest és T1)
        {"data": date(2026, 2, 1),  "quantitat": 500.0,  "aplica_iva": True, "retencio_pct": 0.0},
    ]
    buf = calcular_buffers_trimestre(moviments, trimestre=2, any_=2026)
    assert buf.nombre_factures == 2
    assert buf.total_ingressos == pytest.approx(1800.0)
    # IVA: 1000*0.21 + 800*0.21 = 210 + 168 = 378
    assert buf.iva_acumulat == pytest.approx(378.0)
    # IRPF: 1000*0.20 + max(0, 800*0.20 - 800*0.15) = 200 + 40 = 240
    assert buf.irpf_acumulat == pytest.approx(240.0)
    # SS: 88.64 × 3
    assert buf.ss_acumulat == pytest.approx(TARIFA_PLANA_AMB_MEI * 3, abs=0.01)


def test_buffers_trimestre_buit():
    buf = calcular_buffers_trimestre([], trimestre=1, any_=2026)
    assert buf.nombre_factures == 0
    assert buf.total_ingressos == 0.0
    assert buf.iva_acumulat == 0.0
    assert buf.irpf_acumulat == 0.0
