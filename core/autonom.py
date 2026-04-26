"""Càlculs fiscals i de Seguretat Social per a autònoms — Espanya 2026.

Mòdul pur: sense dependències de Streamlit ni Google Sheets.
Tots els valors monetaris en euros (float). Les funcions que retornen
euros arrodoneixen a 2 decimals per facilitar la presentació.

Font de veritat: RDL 16/2025 + Ordre ESS/2015 (trams RETA 2026 congelats).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------------------
# CONSTANTS 2026
# ---------------------------------------------------------------------------

TARIFA_PLANA_AMB_MEI: float = 88.64
TIPUS_COTITZACIO: float = 0.314
DEDUCCIO_DIFICIL_JUSTIFICACIO: float = 0.07

VENCIMENTS_TRIMESTRALS_2026: dict[int, date] = {
    1: date(2026, 4, 20),
    2: date(2026, 7, 20),
    3: date(2026, 10, 20),
    4: date(2027, 1, 30),
}

# ---------------------------------------------------------------------------
# DATACLASSES
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tram:
    numero: int
    limit_inferior: float
    limit_superior: float
    base_minima: float
    quota_minima: float


@dataclass(frozen=True)
class ProvisioFiscal:
    ingres_brut: float
    iva_repercutit: float
    irpf_provisio: float
    cuota_ss_provisio: float
    net_disponible: float


@dataclass(frozen=True)
class BuffersTrimestre:
    trimestre: int
    any_: int
    iva_acumulat: float
    irpf_acumulat: float
    ss_acumulat: float
    total_ingressos: float
    nombre_factures: int


# ---------------------------------------------------------------------------
# TAULA DE TRAMS 2026 (15 trams, congelats per RDL 16/2025)
# limit_superior: valor fins al qual s'aplica el tram (inclusiu).
# La funció tram_actual() usa "primer tram on rendiment <= limit_superior".
# ---------------------------------------------------------------------------

TAULA_TRAMS_2026: list[Tram] = [
    Tram(1,     0.00,     670.00,   653.59,  200.0),
    Tram(2,   670.00,     900.00,   718.95,  220.0),
    Tram(3,   900.00,   1_166.70,   849.67,  260.0),
    Tram(4, 1_166.70,   1_300.00,   950.98,  291.0),
    Tram(5, 1_300.00,   1_500.00,   960.78,  294.0),
    Tram(6, 1_500.00,   1_700.00,   960.78,  302.0),
    Tram(7, 1_700.00,   1_850.00, 1_143.79,  350.0),
    Tram(8, 1_850.00,   2_030.00, 1_209.15,  370.0),
    Tram(9, 2_030.00,   2_330.00, 1_272.87,  390.0),
    Tram(10, 2_330.00,  2_760.00, 1_382.17,  423.0),
    Tram(11, 2_760.00,  3_190.00, 1_441.75,  441.0),
    Tram(12, 3_190.00,  3_620.00, 1_532.21,  469.0),
    Tram(13, 3_620.00,  4_050.00, 1_633.99,  500.0),
    Tram(14, 4_050.00,  6_000.00, 1_836.76,  562.0),
    Tram(15, 6_000.00,  float("inf"), 1_928.10, 590.0),
]


# ---------------------------------------------------------------------------
# FUNCIONS
# ---------------------------------------------------------------------------


def tram_actual(rendiment_net_mensual: float) -> Tram:
    """Retorna el tram RETA corresponent al rendiment net mensual estimat.

    Usa la primera entrada de TAULA_TRAMS_2026 on
    rendiment <= limit_superior (trams ordenats ascendentment).
    """
    for t in TAULA_TRAMS_2026:
        if rendiment_net_mensual <= t.limit_superior:
            return t
    return TAULA_TRAMS_2026[-1]


def calcular_quota_ss(
    rendiment_net_mensual: float,
    *,
    tarifa_plana_activa: bool = False,
) -> float:
    """Quota mensual de la Seguretat Social (RETA) en euros.

    Si tarifa_plana_activa és True, retorna TARIFA_PLANA_AMB_MEI (88,64 €)
    independentment del rendiment. En cas contrari, retorna la quota mínima
    del tram corresponent.
    """
    if tarifa_plana_activa:
        return TARIFA_PLANA_AMB_MEI
    return tram_actual(rendiment_net_mensual).quota_minima


def rendiment_net_mensual(
    ingressos_anuals: float,
    despeses_anuals: float,
    cuotes_pagades_any: float,
) -> float:
    """Rendiment net mensual estimat per determinar el tram RETA.

    Fórmula oficial (estimació directa simplificada):
        diferència = ingressos − despeses − cuotes_RETA
        deducció 7% = diferència × 0,07  (despeses de difícil justificació)
        rendiment_net_anual = diferència × 0,93
        rendiment_net_mensual = rendiment_net_anual / 12
    """
    diferencia = ingressos_anuals - despeses_anuals - cuotes_pagades_any
    rendiment_net_anual = diferencia * (1.0 - DEDUCCIO_DIFICIL_JUSTIFICACIO)
    return rendiment_net_anual / 12.0


def calcular_provisio_freelance(
    ingres_brut: float,
    *,
    aplica_iva: bool = True,
    retencio_irpf_pct: float = 0.0,
    cuota_ss_mensual: float = TARIFA_PLANA_AMB_MEI,
    factures_aprox_mes: int = 4,
) -> ProvisioFiscal:
    """Calcula els buffers fiscals d'un cobrament freelance.

    Paràmetres:
        ingres_brut: import cobrat (sense IVA si n'hi ha).
        aplica_iva: True si la factura porta IVA al 21%.
        retencio_irpf_pct: retenció ja aplicada pel client (0.0, 0.07 o 0.15).
        cuota_ss_mensual: quota SS mensual vigent.
        factures_aprox_mes: nombre estimat de factures al mes (per prorratejo SS).

    Retorna ProvisioFiscal amb els imports a apartar i el net disponible.
    """
    iva = round(ingres_brut * 0.21, 2) if aplica_iva else 0.0
    ja_retingut = round(ingres_brut * retencio_irpf_pct, 2)
    irpf_objectiu = round(ingres_brut * 0.20, 2)
    irpf_a_apartar = round(max(0.0, irpf_objectiu - ja_retingut), 2)
    ss_proporcional = round(cuota_ss_mensual / max(factures_aprox_mes, 1), 2)
    net = round(ingres_brut - iva - irpf_a_apartar - ss_proporcional, 2)
    return ProvisioFiscal(
        ingres_brut=ingres_brut,
        iva_repercutit=iva,
        irpf_provisio=irpf_a_apartar,
        cuota_ss_provisio=ss_proporcional,
        net_disponible=net,
    )


def trimestre_de(d: date) -> int:
    """Retorna el trimestre (1–4) corresponent a una data."""
    return (d.month - 1) // 3 + 1


def proxim_venciment(d: date | None = None) -> tuple[int, date, int]:
    """Retorna el pròxim venciment fiscal trimestral (130/303).

    Retorna (trimestre, data_venciment, dies_fins).
    Si la data de venciment del trimestre actual ja ha passat,
    retorna el venciment del trimestre següent.
    """
    if d is None:
        d = date.today()
    for trim in sorted(VENCIMENTS_TRIMESTRALS_2026):
        venciment = VENCIMENTS_TRIMESTRALS_2026[trim]
        if venciment > d:
            return (trim, venciment, (venciment - d).days)
    # Tots els venciments de l'any ja han passat
    ultim_trim = max(VENCIMENTS_TRIMESTRALS_2026)
    ultim_venciment = VENCIMENTS_TRIMESTRALS_2026[ultim_trim]
    return (ultim_trim, ultim_venciment, (ultim_venciment - d).days)


def calcular_buffers_trimestre(
    moviments_freelance: list[dict],
    trimestre: int,
    any_: int,
    *,
    cuota_ss_mensual: float = TARIFA_PLANA_AMB_MEI,
) -> BuffersTrimestre:
    """Agrega els buffers fiscals de tots els moviments freelance d'un trimestre.

    Cada dict de moviments_freelance ha de tenir:
        'data': date | str (ISO), 'quantitat': float,
        'aplica_iva': bool, 'retencio_pct': float.

    La quota SS del trimestre és cuota_ss_mensual × 3 (3 mesos).
    """
    iva_total = 0.0
    irpf_total = 0.0
    ingressos_total = 0.0
    nombre = 0

    for mov in moviments_freelance:
        data_mov = mov["data"]
        if isinstance(data_mov, str):
            data_mov = date.fromisoformat(data_mov)
        if data_mov.year != any_ or trimestre_de(data_mov) != trimestre:
            continue

        quant = float(mov["quantitat"])
        iva_total += quant * 0.21 if mov.get("aplica_iva", True) else 0.0
        retencio = quant * float(mov.get("retencio_pct", 0.0))
        irpf_total += max(0.0, quant * 0.20 - retencio)
        ingressos_total += quant
        nombre += 1

    return BuffersTrimestre(
        trimestre=trimestre,
        any_=any_,
        iva_acumulat=round(iva_total, 2),
        irpf_acumulat=round(irpf_total, 2),
        ss_acumulat=round(cuota_ss_mensual * 3, 2),
        total_ingressos=round(ingressos_total, 2),
        nombre_factures=nombre,
    )


def tarifa_plana_estat(
    data_alta: date,
    prorroga_activa: bool = False,
    avui: date | None = None,
) -> dict:
    """Estat de la tarifa plana (primer any o pròrroga).

    Retorna {"activa": bool, "mesos_restants": int, "data_fi": date}.

    Durada: 12 mesos base; 24 si prorroga_activa és True.
    """
    if avui is None:
        avui = date.today()

    mesos = 24 if prorroga_activa else 12
    any_fi = data_alta.year + (data_alta.month + mesos - 1) // 12
    mes_fi = (data_alta.month + mesos - 1) % 12 + 1
    try:
        data_fi = date(any_fi, mes_fi, data_alta.day)
    except ValueError:
        import calendar
        data_fi = date(any_fi, mes_fi, calendar.monthrange(any_fi, mes_fi)[1])

    activa = avui < data_fi
    mesos_restants = (
        max(0, (data_fi.year - avui.year) * 12 + (data_fi.month - avui.month))
        if activa
        else 0
    )
    return {"activa": activa, "mesos_restants": mesos_restants, "data_fi": data_fi}
