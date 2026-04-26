---
name: streamlit-component
description: Sistema de disseny per a components Streamlit del projecte Família Finances. Activa aquesta skill sempre que es modifiqui o creï qualsevol element visual de l'app — mètriques, gràfics, formularis, pestanyes, sidebar, botons, contenidors, CSS, layouts. Inclou variables CSS, estils responsives, regles de mòbil, patrons de mètriques amb delta, pills de selecció, i empty states. Fes-la servir TAMBÉ quan l'usuari demani només "millora la UI", "fes-ho més bonic", "reorganitza el dashboard", o qualsevol canvi estètic, encara que no anomeni explícitament cap component.
---

# Streamlit Component — Sistema de disseny

Aquesta skill conté les regles visuals i de comportament per a qualsevol component visible de l'app Família Finances. Si has de tocar HTML, CSS, layout, mètrica o gràfic, llegeix-la sencera abans.

## Variables CSS (canòniques)

Sempre usar variables, mai colors hardcoded. Aquest és l'únic bloc que defineix la paleta:

```css
:root {
    --bg-card: #ffffff;
    --bg-card-hover: #f8f9fb;
    --bg-subtle: #f3f4f6;
    --border: #e5e7eb;
    --text-primary: #111827;
    --text-secondary: #6b7280;
    --text-muted: #9ca3af;
    --accent: #6366f1;
    --accent-soft: #eef2ff;
    --success: #10b981;
    --success-soft: #d1fae5;
    --danger: #ef4444;
    --danger-soft: #fee2e2;
    --warning: #f59e0b;
    --warning-soft: #fef3c7;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03);
    --shadow-lg: 0 4px 12px rgba(0,0,0,0.08);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --transition: 0.15s ease;
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg-card: #1f2937;
        --bg-card-hover: #252f3f;
        --bg-subtle: #111827;
        --border: #374151;
        --text-primary: #f9fafb;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;
        --accent: #818cf8;
        --accent-soft: #312e81;
        --success-soft: #064e3b;
        --danger-soft: #7f1d1d;
        --warning-soft: #78350f;
        --shadow-md: 0 1px 3px rgba(0,0,0,0.3);
        --shadow-lg: 0 4px 12px rgba(0,0,0,0.4);
    }
}
```

## Tipografia

```css
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                 "Helvetica Neue", Arial, sans-serif;
    font-feature-settings: "kern", "liga", "tnum";
}
```

Mai imports de Google Fonts — alenteixen la càrrega i Streamlit Cloud té latència extra.

## Mètriques (`st.metric`)

Aquest és el patró únic per a totes les mètriques de l'app:

```css
div[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 18px 22px;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    transition: transform var(--transition), box-shadow var(--transition);
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}
div[data-testid="stMetricLabel"] {
    color: var(--text-secondary);
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
div[data-testid="stMetricValue"] {
    color: var(--text-primary);
    font-weight: 700;
    font-size: 1.6rem;
    font-variant-numeric: tabular-nums;
}
```

**Regla d'ús:**
- Sempre amb `delta` quan tinguem comparativa temporal disponible.
- Format de números: `f"{valor:,.2f} €"` per separador de milers.
- Per percentatges: `f"{p:.1f}%"`, sense decimals si ≥ 100%.

## Responsive (mòbil)

L'app ha de funcionar bé al mòbil de Pepe i de l'Alba. Streamlit no fa responsive per defecte, així que cal CSS dirigit:

```css
@media (max-width: 640px) {
    div[data-testid="stMetric"] {
        padding: 12px 14px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem;
        padding: 0 12px;
        height: 42px;
    }
    /* Reduir gaps entre seccions per aprofitar pantalla */
    .block-container { padding-top: 1rem !important; }
}
```

Quan facis 3 columnes amb `st.columns(3)` que continguin mètriques, considera si en mòbil és millor `st.columns([1])` o un layout 2x2. Per fer 2x2:

```python
if mobile_or_responsive:  # detecció heurística pels filtres elegits
    c1, c2 = st.columns(2)
    with c1: st.metric("Ingressos", ...)
    with c2: st.metric("Despeses", ...)
    c3, c4 = st.columns(2)
    with c3: st.metric("Saldo", ...)
    with c4: st.metric("Taxa estalvi", ...)
```

> Streamlit no exposa la mida de viewport, però es pot usar `streamlit-js-eval` per detectar-ho. Per defecte, dissenya amb CSS responsive i deixa que el navegador faci la resta.

## Pestanyes (`st.tabs`)

```css
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    height: 48px;
    background: transparent;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    color: var(--text-secondary);
    font-weight: 600;
    transition: all var(--transition);
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
    background: var(--bg-subtle);
}
.stTabs [aria-selected="true"] {
    background: var(--accent-soft);
    color: var(--accent);
}
```

## Pills de selecció (alternativa a `st.radio`)

`st.radio(horizontal=True)` queda lleig. Per fer pills, opció 1 (segmentat oficial des de Streamlit ≥1.32):

```python
opcio = st.segmented_control(
    "Visualització",
    ["Evolució Saldo", "Despeses per Categoria", "Detall Ingressos"],
    default="Evolució Saldo",
    label_visibility="collapsed",
)
```

Opció 2 (manual amb columnes i estat):
```python
if "vista_grafic" not in st.session_state:
    st.session_state.vista_grafic = "Evolució Saldo"
opcions = ["Evolució Saldo", "Despeses per Categoria", "Detall Ingressos"]
cols = st.columns(len(opcions))
for col, op in zip(cols, opcions):
    actiu = st.session_state.vista_grafic == op
    if col.button(op, type="primary" if actiu else "secondary",
                  use_container_width=True, key=f"pill_{op}"):
        st.session_state.vista_grafic = op
        st.rerun()
```

## Cards personalitzades

Quan calgui agrupar info que `st.metric` no cobreix (ex: hero card del saldo, llistes, insights):

```python
def card(content_fn, *, title=None, accent=False):
    """Wrapper que pinta una card amb estil. Crida content_fn() dins del bloc."""
    accent_class = "accent" if accent else ""
    st.markdown(f'<div class="custom-card {accent_class}">', unsafe_allow_html=True)
    if title:
        st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    content_fn()
    st.markdown('</div>', unsafe_allow_html=True)
```

```css
.custom-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    box-shadow: var(--shadow-md);
    margin-bottom: 12px;
}
.custom-card.accent {
    background: linear-gradient(135deg, var(--accent-soft) 0%, var(--bg-card) 100%);
    border-color: var(--accent);
}
.custom-card .card-title {
    color: var(--text-secondary);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin-bottom: 12px;
}
```

> **Avís**: usar `unsafe_allow_html=True` només per estructures purament visuals. Mai per renderitzar dades de l'usuari (XSS).

## Plotly: tema unificat

Tots els gràfics han d'usar la mateixa paleta:

```python
import plotly.express as px
import plotly.graph_objects as go

PALETTE = {
    "ingres": "#10b981",
    "despesa": "#ef4444",
    "neutral": "#6366f1",
    "warm": px.colors.qualitative.Pastel,
    "cool": px.colors.qualitative.Set2,
}

def aplicar_tema(fig: go.Figure, titol: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=titol, font=dict(size=16, color="#111827")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, Inter, sans-serif", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb"),
        yaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb"),
        hoverlabel=dict(bgcolor="#1f2937", font_color="white"),
    )
    return fig
```

Cridar `st.plotly_chart(aplicar_tema(fig, "Títol"), use_container_width=True)`.

## Empty states

Quan una secció no té dades, mai mostrar gràfic buit. Usa `st.info` amb missatge útil i acció:

```python
if df_filtrat.empty:
    st.info("📭 Cap moviment en aquest període. Prova canviant el filtre o afegint un moviment.")
else:
    # render normal
```

Per mòbil, fer servir emojis frontals ajuda a la jerarquia visual ràpidament.

## Botons

Streamlit per defecte ja és correcte. Regles:
- **Botó primari** (`type="primary"`) només per a accions principals (Guardar, Processar, Generar).
- **Botó secundari** (per defecte) per a accions auxiliars (Cancel·lar, Tancar Sessió).
- **Botó destructiu**: usar emoji 🗑 + secondary, o color amb CSS si cal.
- Sempre `use_container_width=True` quan estiguin dins de `st.columns`.

## Iconografia

Emojis sí, però amb mesura. Lloc i regla:
- 🏦 Brand de l'app.
- 🟢 Ingressos.
- 🔴 Despeses.
- 💰 Saldo.
- 📅 Filtres.
- ⚙️ Configuració.
- 🧠 IA / Assessor.
- ✏️ Edició.
- 🚀 Acció completada.
- 🔒 Seguretat.
- 🔔 Avisos.

Mai posar més de 1 emoji per element. Mai emoji a noms de variable.

## Què no fer

- ❌ Colors hardcoded fora del bloc de variables.
- ❌ `st.markdown(f"<style>...{value}</style>")` amb interpolació — perilla XSS i no es pot cachear.
- ❌ Fonts pesades (`@import` Google Fonts).
- ❌ Animacions complexes (translate3d amb keyframes). Streamlit fa rerender constant, queden ridícules.
- ❌ Modals amb `st.dialog` per coses simples — usar `st.expander` o `st.popover`.
- ❌ Mètriques amb >5 dígits sense format de milers.
- ❌ `st.radio` horitzontal per a >3 opcions — usar `st.segmented_control` o pills.
