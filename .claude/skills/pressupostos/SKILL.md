# Pressupostos — Lògica i Sistema de Disseny

Aquesta skill descriu com funciona el mòdul de pressupostos (`core/pressupostos.py`) i com s'ha de presentar a la UI.

## Concepte: pressupost "per ritme"

No comparem despesa vs. pressupost en termes absoluts, sinó **relatius al temps transcorregut del mes**. Això evita alarmes falses els primers dies del mes.

### Fórmula

```
pct_consumit = despesa_actual / import_mensual
pct_esperat  = dia_del_mes / dies_del_mes
ratio        = pct_consumit / pct_esperat
```

### Semàfor

| Condició | Estat | Color |
|----------|-------|-------|
| `import_mensual == 0` | `sense_pressupost` | gris |
| `pct_consumit ≥ 1.0` | `vermell` | `--danger` |
| `ratio ≥ 1.10` | `vermell` | `--danger` |
| `0.85 ≤ ratio < 1.10` | `groc` | `--warning` |
| `ratio < 0.85` | `verd` | `--success` |

### Exemple

Dia 15 d'un mes de 30 dies (50% del mes transcorregut):
- Gastat 40€ de 100€ → pct_consumit=40%, ratio=0.80 → **verd** (per sota del ritme)
- Gastat 48€ → ratio=0.96 → **groc** (dins del ritme)
- Gastat 60€ → ratio=1.20 → **vermell** (supera el ritme)
- Gastat 105€ → pct_consumit>100% → **vermell** (absolut)

## Categories de despesa

Les 8 categories fixes: `Alimentació`, `Transport`, `Habitatge`, `Salut`, `Oci`, `Roba`, `Educació`, `Altres_Despesa`.

Definides a `CATEGORIES_DESPESA` a `core/pressupostos.py`. No modificar sense actualitzar la Sheets i els tests.

## Pestanya Google Sheets

- Nom: `Pressupostos`
- Columnes: `categoria`, `import_mensual`
- Esquema creat per `_assegurar_pestanya_pressupostos(conn)` (gspread natiu)
- Lectura/escriptura via `conn.read` / `conn.update` (streamlit-gsheets)
- Import 0.0 significa "sense pressupost configurat" per a aquella categoria

## Funcions del mòdul

```python
# Esquema i inicialització
inicialitzar_pressupostos(conn) -> None       # crea pestanya + defaults si cal (idempotent)

# Lectura
carregar_pressupostos(_conn) -> dict[str, float]   # cached 60s
_carregar_pressupostos_raw(conn) -> dict[str, float]  # sense cache (testable)

# Escriptura
guardar_pressupostos(conn, pressupostos: dict[str, float]) -> None

# Lògica
estat_pressupost(despesa_actual, import_mensual, dia_del_mes, dies_del_mes) -> dict
calcular_estats_categoria(df_mes_actual, pressupostos, avui) -> dict[str, dict]
```

### Estructura del dict retornat per `estat_pressupost`

```python
{
    "estat": "verd" | "groc" | "vermell" | "sense_pressupost",
    "pct_consumit": float | None,    # 0.0 – N (pot superar 1.0)
    "pct_esperat": float | None,     # 0.0 – 1.0
    "ratio": float | None,           # pct_consumit / pct_esperat
    "restant": float | None,         # import_mensual - despesa_actual
}
```

## Presentació a la UI (guia per Fase 3 Pas B)

### Barra de progrés per categoria

```python
color_map = {"verd": "--success", "groc": "--warning", "vermell": "--danger"}

def progress_bar_html(label, pct_consumit, pct_esperat, estat, restant, import_mensual):
    color = f"var({color_map.get(estat, '--text-muted')})"
    bar_width = min(pct_consumit * 100, 100)
    marker_left = pct_esperat * 100
    return f"""
    <div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-weight:600;color:var(--text-primary)">{label}</span>
        <span style="color:var(--text-secondary);font-size:0.85rem">
          {pct_consumit*100:.0f}% · queden {restant:,.0f}€ de {import_mensual:,.0f}€
        </span>
      </div>
      <div style="background:var(--bg-subtle);border-radius:4px;height:8px;position:relative">
        <div style="background:{color};width:{bar_width}%;height:8px;border-radius:4px"></div>
        <div style="position:absolute;top:-2px;left:{marker_left}%;width:2px;height:12px;
                    background:var(--text-muted);opacity:0.6"></div>
      </div>
    </div>
    """
```

La línia vertical al `marker_left` indica el ritme esperat — permet veure visualment si la barra passa o no la marca.

### Layout recomanat

```python
col1, col2 = st.columns([2, 1])
with col1:
    # barres de progrés per categoria (st.markdown amb HTML)
    pass
with col2:
    # resum: categories en vermell, total gastat vs. pressupost total
    pass
```

### Empty state

Si cap categoria té pressupost configurat (tot a 0), mostrar:

```python
st.info("📊 Encara no has configurat cap pressupost. Ves a ⚙️ per establir els imports mensuals.")
```

### Formulari d'edició de pressupostos

Usar `st.number_input` amb `min_value=0.0`, `step=50.0`, `format="%.0f"` per a cada categoria. Agrupar en 2 columnes per estalviar espai.

```python
with st.expander("✏️ Editar pressupostos"):
    cols = st.columns(2)
    nous_pp = {}
    for i, cat in enumerate(CATEGORIES_DESPESA):
        with cols[i % 2]:
            nous_pp[cat] = st.number_input(
                cat, value=float(pressupostos.get(cat, 0)),
                min_value=0.0, step=50.0, format="%.0f", key=f"pp_{cat}"
            )
    if st.button("Guardar pressupostos", type="primary"):
        guardar_pressupostos(conn, nous_pp)
        st.success("Pressupostos guardats.")
        st.rerun()
```

## Integració amb app.py (Fase 3 Pas B)

A l'arrencada, just after `inicialitzar_config(conn)`:
```python
from core.pressupostos import inicialitzar_pressupostos, carregar_pressupostos
inicialitzar_pressupostos(conn)
pressupostos = carregar_pressupostos(conn)
```

`df_mes_actual` és el DataFrame filtrat per any/mes actual, columnes `categoria` i `import` (imports de despeses, valors negatius o positius — `calcular_estats_categoria` usa `abs()`).

## Què no fer

- ❌ No usar ratio per a categories sense pressupost — sempre retornar `"sense_pressupost"`.
- ❌ No assumir que `pct_consumit ≤ 1.0` — pot superar-se (passar de pressupost).
- ❌ No hardcodejar categories fora de `CATEGORIES_DESPESA` — si cal afegir-ne, actualitzar la constant i la Sheets.
- ❌ No mostrar decimals als euros de pressupost — `format="%.0f"` o `f"{v:,.0f}€"`.
