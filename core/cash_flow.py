"""Projecció de saldo i alertes de liquiditat — mòdul pur sense Streamlit ni Sheets."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import pandas as pd


def _dia_segur(any_: int, mes: int, dia: int) -> date:
    """Retorna la data ajustada al darrer dia vàlid del mes si dia > dies del mes."""
    max_dia = calendar.monthrange(any_, mes)[1]
    return date(any_, mes, min(dia, max_dia))


def _ocurrencies_mensuals(dia: int, avui: date, fins: date) -> list[date]:
    resultat = []
    d = _dia_segur(avui.year, avui.month, dia)
    if d < avui:
        mes = avui.month + 1
        any_ = avui.year
        if mes > 12:
            mes, any_ = 1, any_ + 1
        d = _dia_segur(any_, mes, dia)
    while d <= fins:
        resultat.append(d)
        mes = d.month + 1
        any_ = d.year
        if mes > 12:
            mes, any_ = 1, any_ + 1
        d = _dia_segur(any_, mes, dia)
    return resultat


def _ocurrencies_trimestrals(dia: int, avui: date, fins: date) -> list[date]:
    resultat = []
    d = _dia_segur(avui.year, avui.month, dia)
    if d < avui:
        mes = avui.month + 1
        any_ = avui.year
        if mes > 12:
            mes, any_ = 1, any_ + 1
        d = _dia_segur(any_, mes, dia)
    while d <= fins:
        resultat.append(d)
        mes = d.month + 3
        any_ = d.year
        while mes > 12:
            mes -= 12
            any_ += 1
        d = _dia_segur(any_, mes, dia)
    return resultat


def _ocurrencies_anuals(dia: int, mes: int, avui: date, fins: date) -> list[date]:
    resultat = []
    any_ = avui.year
    d = _dia_segur(any_, mes, dia)
    if d < avui:
        any_ += 1
        d = _dia_segur(any_, mes, dia)
    while d <= fins:
        resultat.append(d)
        any_ += 1
        d = _dia_segur(any_, mes, dia)
    return resultat


def _ocurrencies_setmanals(dia: int, avui: date, fins: date) -> list[date]:
    resultat = []
    if 1 <= dia <= 7:
        target_weekday = dia - 1  # 1=dilluns → Python weekday 0
        dies_offset = (target_weekday - avui.weekday()) % 7
        d = avui + timedelta(days=dies_offset)
    else:
        d = avui
    while d <= fins:
        resultat.append(d)
        d += timedelta(days=7)
    return resultat


def proximes_ocurrencies(recurrent: dict, avui: date, fins: date) -> list[date]:
    """Retorna totes les dates d'ocurrència del recurrent en el rang [avui, fins]."""
    freq = recurrent.get("frequencia", "Mensual")
    dia = int(recurrent.get("dia", 1))

    if freq == "Mensual":
        return _ocurrencies_mensuals(dia, avui, fins)
    if freq == "Trimestral":
        return _ocurrencies_trimestrals(dia, avui, fins)
    if freq == "Anual":
        mes = int(recurrent.get("mes", 1))
        return _ocurrencies_anuals(dia, mes, avui, fins)
    if freq == "Setmanal":
        return _ocurrencies_setmanals(dia, avui, fins)
    return []


def projectar_saldo(
    saldo_actual: float,
    recurrents: list[dict],
    avui: date,
    dies: int = 60,
) -> pd.DataFrame:
    """Retorna DataFrame diari (data, saldo_previst, esdeveniment) per als propers `dies` dies."""
    fins = avui + timedelta(days=dies)

    moviments_per_dia: dict[date, list[tuple[str, float]]] = {}
    for rec in recurrents:
        ocurrencies = proximes_ocurrencies(rec, avui, fins)
        nom = rec.get("nom", rec.get("descripcio", "Recurrent"))
        import_ = float(rec.get("import", rec.get("quantitat", 0.0)))
        for d in ocurrencies:
            moviments_per_dia.setdefault(d, []).append((nom, import_))

    files = []
    saldo = saldo_actual
    for i in range(dies + 1):
        d = avui + timedelta(days=i)
        moviments = moviments_per_dia.get(d, [])
        for _, imp in moviments:
            saldo += imp
        sdev = ", ".join(f"{nom} ({imp:+.0f}€)" for nom, imp in moviments) if moviments else ""
        files.append({"data": d, "saldo_previst": round(saldo, 2), "esdeveniment": sdev})

    return pd.DataFrame(files)


def detectar_alertes_saldo(
    df_projeccio: pd.DataFrame,
    llindar: float = 500.0,
) -> list[dict]:
    """Detecta períodes on saldo_previst < llindar i els agrupa si són consecutius.

    Retorna [{"data": date, "saldo": float, "missatge": str}] — una entrada per període.
    """
    sota = df_projeccio[df_projeccio["saldo_previst"] < llindar].copy()
    if sota.empty:
        return []

    dates = sorted(sota["data"].tolist())
    saldos = {row["data"]: row["saldo_previst"] for _, row in sota.iterrows()}

    alertes: list[dict] = []
    i = 0
    while i < len(dates):
        start = dates[i]
        end = dates[i]
        min_saldo = saldos[start]

        j = i + 1
        while j < len(dates) and dates[j] == end + timedelta(days=1):
            end = dates[j]
            min_saldo = min(min_saldo, saldos[end])
            j += 1

        if start == end:
            missatge = f"Saldo baix el {start.strftime('%d/%m/%Y')}: {min_saldo:.2f}€"
        else:
            missatge = (
                f"Saldo baix del {start.strftime('%d/%m/%Y')} "
                f"al {end.strftime('%d/%m/%Y')}: mínim {min_saldo:.2f}€"
            )

        alertes.append({"data": start, "saldo": min_saldo, "missatge": missatge})
        i = j

    return alertes


def saldo_minim_previst(df_projeccio: pd.DataFrame) -> tuple[date, float]:
    """Retorna (data_del_mínim, valor_mínim) de la projecció."""
    idx = df_projeccio["saldo_previst"].idxmin()
    row = df_projeccio.loc[idx]
    return (row["data"], float(row["saldo_previst"]))
