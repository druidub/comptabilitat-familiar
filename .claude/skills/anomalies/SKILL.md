# Anomalies — Detecció Estadística de Despeses Atípiques

Mòdul `core/anomalies.py`. Detecció pura sense Streamlit ni Sheets. L'IA s'invoca al Pas B per generar el resum; aquí només estadística.

**Triggers**: "anomalia", "despesa atípica", "variació", "alerta despesa inusual", "patró estrany", "detecció automàtica", "despesa fora del normal"

---

## Les 3 estratègies de detecció

### 1. Variació per categoria (`categories_amb_variacio`)

Compara la despesa del mes actual (normalitzada a mes complet) amb la mitjana dels N mesos previs.

```python
categories_amb_variacio(df, avui, *, mesos_historic=3, llindar_pct=30.0) -> list[dict]
```

Retorna:
```python
[{
    "categoria": "Alimentació",
    "actual": 700.0,              # despesa real acumulada fins avui
    "actual_normalitzat": 700.0,  # extrapolat a mes complet
    "mitjana_historic": 400.0,    # mitjana dels N mesos previs
    "variacio_pct": 75.0,         # (actual_norm - mitjana) / mitjana * 100
    "tipus": "augment",           # "augment" | "reduccio"
}]
```

Regla: `abs(variacio_pct) >= llindar_pct` per incloure. Ordenat per `|variacio_pct|` descendent.

Si la `mitjana_historic == 0` (categoria nova als mesos previs), s'omet — usa `categories_noves` per a aquest cas.

### 2. Despesa individual atípica (`despeses_individuals_atipiques`)

Detecta transaccions individuals del mes actual que superen `factor_mediana × mediana histórica` de la mateixa categoria.

```python
despeses_individuals_atipiques(df, avui, *, factor_mediana=2.0, mesos_historic=3) -> list[dict]
```

Retorna:
```python
[{
    "data": date(2026, 4, 10),
    "concepte": "Sopar gourmet",
    "establiment": "Restaurant Caríssim",
    "categoria": "Restauració",
    "quantitat": 250.0,          # valor absolut
    "mediana_categoria": 30.0,   # mediana de les transaccions históriques de la cat.
    "factor": 8.33,              # quantitat / mediana
}]
```

Ordenat per `factor` descendent. La mediana es calcula sobre transaccions individuals (no totals mensuals).

### 3. Categoria nova (`categories_noves`)

Detecta categories que apareixen al mes actual però no als N mesos previs.

```python
categories_noves(df, avui, *, mesos_historic=3) -> list[dict]
```

Retorna:
```python
[{"categoria": "Roba", "total": 160.0, "moviments": 2}]
```

---

## Regla de normalització de mes incomplet

**Problema**: Si avui és dia 5 i s'han gastat 100€, comparar-ho directament amb 400€/mes donaria -75% (fals negatiu). La normalització evita falses alarmes a principi de mes.

```python
def normalitzar_a_mes_complet(total_acumulat: float, avui: date) -> float:
    dies_del_mes = calendar.monthrange(avui.year, avui.month)[1]
    return (total_acumulat / avui.day) * dies_del_mes
```

Exemple: dia 5 d'abril (30 dies), 100€ → `(100/5)*30 = 600€`. Comparat amb 400€ históric: **+50%** (detecta augment real), no -75%.

La normalització s'aplica **sempre** a `categories_amb_variacio`. No s'aplica a `despeses_individuals_atipiques` (compara transaccions, no totals mensuals).

---

## Filtres obligatoris

Totes les funcions apliquen internament `_filtrar_despeses`:

1. **Només `tipus == "Despesa"`** — ingressos no generen alertes (un pagament gran és bona notícia).
2. **Excloure `CATEGORIES_EXCLOSES`** = `{"Freelance", "Ajut_Públic"}` — categories que podrien estar mal etiquetades com a Despesa.

```python
CATEGORIES_EXCLOSES: frozenset[str] = frozenset({"Freelance", "Ajut_Públic"})
```

---

## Filtres de qualitat (només `despeses_individuals_atipiques`)

Aplicats després de `_filtrar_despeses` per reduir falsos positius:

1. **Excloure `es_periodic == True`** — les despeses recurrents (hipoteca, subscripcions) no són anomalies per definició. Si el camp no existeix al DataFrame, no s'aplica el filtre.

2. **Llindar mínim de `LLINDAR_MINIM_DESPESA = 5€`** al càlcul de mediana i detecció — les despeses petites distorsionen la mediana cap avall i no aporten valor diagnòstic.

3. **Llindar absolut de `LLINDAR_ABSOLUT_ATIPICA = 30€`** per marcar una despesa com atípica — una despesa que sigui 10× la mediana però de 8€ és irrellevant per a la salut financera.

Condició de detecció completa: `factor > factor_mediana AND quantitat >= 30€`

```python
LLINDAR_MINIM_DESPESA: float = 5.0
LLINDAR_ABSOLUT_ATIPICA: float = 30.0
```

---

## Paràmetres configurables (`Config_App`)

| Clau | Tipus | Default | Descripció |
|------|-------|---------|------------|
| `llindar_anomalia_pct` | float | 30.0 | % de variació mínim per alertar a `categories_amb_variacio` |
| `factor_mediana_atipica` | float | 2.0 | Multiplicador de mediana per a `despeses_individuals_atipiques` |

`detectar_totes_anomalies(df, avui, config_app)` llegeix aquests valors automàticament.

---

## Orquestrador

```python
detectar_totes_anomalies(df, avui, config_app) -> dict
# Retorna:
{
    "variacions": [...],   # categories_amb_variacio(...)
    "individuals": [...],  # despeses_individuals_atipiques(...)
    "noves": [...],        # categories_noves(...)
}
```

---

## Casos límit

| Situació | Comportament esperat |
|----------|---------------------|
| DataFrame buit | Totes les funcions retornen `[]` sense excepció |
| < `mesos_historic` mesos de dades | Els mesos sense dades compten com 0€ |
| Categoria amb `mitjana_historic == 0` | S'omet de `categories_amb_variacio` (usa `categories_noves`) |
| Mediana histórica == 0 | S'omet de `despeses_individuals_atipiques` |
| `avui.day == 0` (impossible, però defensiu) | `normalitzar_a_mes_complet` retorna `total_acumulat` sense dividir |

---

## Integració futura (Pas B)

Al Pas B, `detectar_totes_anomalies` s'envia a Gemini per generar un resum en llenguatge natural. El mòdul actual és la font de dades estructurades; la IA afegeix context i to narratiu.

```python
from core.anomalies import detectar_totes_anomalies
anomalies = detectar_totes_anomalies(df, date.today(), config_app)
# anomalies["variacions"], anomalies["individuals"], anomalies["noves"]
# → prompt a Gemini per a resum familiar
```
