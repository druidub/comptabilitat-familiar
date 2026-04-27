# Cash Flow — Projecció de Saldo i Alertes de Liquiditat

Aquesta skill descriu com funciona el mòdul `core/cash_flow.py`: projecció diària de saldo a partir de moviments recurrents.

**Triggers**: "previsió saldo", "cash flow", "projecció", "saldo previst", "alerta liquiditat", "quan em quedaran diners", "projectar saldo"

---

## Funcions del mòdul

```python
proximes_ocurrencies(recurrent: dict, avui: date, fins: date) -> list[date]
projectar_saldo(saldo_actual, recurrents, avui, dies=60) -> pd.DataFrame
detectar_alertes_saldo(df_projeccio, llindar=500.0) -> list[dict]
saldo_minim_previst(df_projeccio) -> tuple[date, float]
```

---

## Estructura del dict `recurrent`

| Camp | Tipus | Descripció |
|------|-------|------------|
| `nom` | str | Nom del moviment (ex. "Nòmina", "Lloguer") |
| `import` | float | Positiu = ingrés, negatiu = despesa |
| `frequencia` | str | `"Mensual"`, `"Trimestral"`, `"Anual"`, `"Setmanal"` |
| `dia` | int | Dia del mes (1–31) per a Mensual/Trimestral/Anual; dia de la setmana (1=dilluns, 7=diumenge) per a Setmanal |
| `mes` | int | (Només per a Anual) Mes de l'any (1–12). Default: 1 |

---

## Lògica de freqüències

### Mensual
Cada mes el dia `dia`. Si el mes no té aquell dia (ex. dia 31 al febrer), usa l'últim dia del mes:
- dia 31 + febrer 2026 → `date(2026, 2, 28)`
- dia 31 + abril → `date(2026, 4, 30)`

La primera ocurrència és el dia `dia` del mes d'`avui` si `>= avui`, sinó el del mes següent.

### Trimestral
Igual que Mensual però cada 3 mesos. La primera ocurrència es calcula com Mensual (proper dia `dia` ≥ avui), i les següents sumen 3 mesos.

### Anual
Una vegada l'any al dia `dia` del mes `mes`. La primera ocurrència és la de l'any actual si `>= avui`, sinó la de l'any vinent.

### Setmanal
Cada 7 dies. Si `dia` és 1–7, s'interpreta com a dia de la setmana (1=dilluns, 7=diumenge). La primera ocurrència és el primer dia target `>= avui`.

**Edge case crític**: `(target_weekday - avui.weekday()) % 7` garanteix que avui mateix s'inclou si és el dia target (resultat = 0).

---

## DataFrame retornat per `projectar_saldo`

| Columna | Tipus | Descripció |
|---------|-------|------------|
| `data` | `date` | Un dia per fila, des d'avui fins avui+dies (inclusiu) |
| `saldo_previst` | `float` | Saldo acumulat fins aquell dia |
| `esdeveniment` | `str` | Moviments del dia, ex. `"Nòmina (+1300€), Lloguer (-550€)"` — buit si no n'hi ha |

El DataFrame té `dies + 1` files (inclou avui).

---

## Alertes de saldo

`detectar_alertes_saldo` agrupa dies consecutius per sota del llindar en un sol període:

```python
[
    {
        "data": date(2026, 5, 10),      # primer dia del període
        "saldo": 350.0,                  # saldo mínim del període
        "missatge": "Saldo baix del 10/05/2026 al 15/05/2026: mínim 350.00€"
    }
]
```

- Si és un sol dia: `"Saldo baix el DD/MM/YYYY: X.XX€"`
- Si és un període: `"Saldo baix del DD/MM/YYYY al DD/MM/YYYY: mínim X.XX€"`

**Llindar per defecte: 500€**. És configurable per cridar.

---

## `saldo_minim_previst`

Retorna `(data_del_mínim, valor_mínim)` — útil per a la mètrica del dashboard:
```python
data, valor = saldo_minim_previst(df)
# Ex: (date(2026, 6, 3), 127.50)
```

---

## Regles importants

- ❌ No importar `streamlit` ni `gspread` — mòdul 100% pur.
- ❌ No modificar el saldo d'avui si no hi ha moviments avui (el saldo inicial ja reflecteix avui).
- ✅ El saldo s'arrodoneix a 2 decimals per evitar errors de coma flotant acumulats.
- ✅ `proximes_ocurrencies` inclou `avui` i `fins` (rang tancat per ambdós costats).
- ✅ Per a mesos sense el dia configurat, sempre usar `min(dia, max_dia_del_mes)` — mai llançar excepció.

---

## Integració futura amb UI (Fase 4 Pas B)

```python
from core.cash_flow import projectar_saldo, detectar_alertes_saldo, saldo_minim_previst

df_proj = projectar_saldo(saldo_actual, recurrents, date.today(), dies=60)
alertes = detectar_alertes_saldo(df_proj, llindar=500.0)
data_min, val_min = saldo_minim_previst(df_proj)
```

La pestanya "Recurrents" de Sheets proporciona la llista `recurrents`. El saldo actual s'obté sumant tots els moviments de la pestanya principal.
