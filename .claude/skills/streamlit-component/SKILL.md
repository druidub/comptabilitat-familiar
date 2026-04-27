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

## Layout global

Regles que afecten tota l'app (van al bloc CSS principal, secció `/* === LAYOUT GLOBAL === */`):

```css
/* Header transparent: no tapa contingut en mòbil ni en la pantalla de login */
header[data-testid="stHeader"] { background: transparent; height: 0; }
header[data-testid="stHeader"]::before { display: none; }

/* Limitar amplada a escriptori per evitar cards estirades */
.block-container { max-width: 1280px; margin: 0 auto; padding-top: 2rem; }
```

**Nota**: `padding-top: 2rem` al `.block-container` global; dins `@media (max-width: 640px)` es sobreescriu a `0.5rem !important`.

## Inputs

Inputs i textareas coherents amb la paleta. Afegir a la secció `/* === INPUTS === */`:

```css
div[data-baseweb="textarea"] textarea,
div[data-baseweb="input"] input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    transition: border-color var(--transition), box-shadow var(--transition);
}
div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="input"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
    border-radius: var(--radius-md) !important;
}
```

## Responsive (mòbil)

L'app ha de funcionar bé al mòbil de Pepe i de l'Alba. Streamlit no fa responsive per defecte, així que cal CSS dirigit:

```css
@media (max-width: 640px) {
    div[data-testid="stMetric"] { padding: 12px 14px; }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem;
        padding: 0 12px;
        height: 42px;
    }
    .block-container { padding-top: 0.5rem !important; }

    /* Grid 2×2: ATENCIÓ — afecta TOTES les st.columns() de l'app.
       Selector correcte (Streamlit ≥1.40): data-testid="column" (NO "stColumn").
       Efecte col·lateral conegut: st.columns(2) queda 50%/50% en comptes de stack.
       Si cal excepció per a un bloc concret, afegir regla específica que sobreescrigui. */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: 8px;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 calc(50% - 8px) !important;
        min-width: calc(50% - 8px) !important;
        width: calc(50% - 8px) !important;
    }
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
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    color: var(--text-primary);
    background: var(--bg-subtle);
}
.stTabs [aria-selected="true"] {
    background: var(--accent-soft);
    color: var(--text-primary);
    font-weight: 700;
    box-shadow: inset 0 -2px 0 var(--accent);
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
                  width="stretch", key=f"pill_{op}"):
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

Cridar `st.plotly_chart(aplicar_tema(fig, "Títol"), width="stretch")`.

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
- Sempre `width="stretch"` quan estiguin dins de `st.columns`.

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

## Google Sheets — Operacions d'esquema

> **Regla fonamental**: `streamlit-gsheets` (`conn.read` / `conn.update`) **no crea pestanyes ni columnes**. Qualsevol operació d'esquema (crear pestanya, afegir columna, migrar dades) requereix baixar a **gspread natiu**.

### Accedir al gspread Spreadsheet

```python
def _spreadsheet(conn):
    # API oficial de streamlit-gsheets — confirmat al repo oficial
    # El connector ja sap quin spreadsheet és des de secrets.toml
    return conn.client._open_spreadsheet()
```

> `_open_spreadsheet()` és semi-privada (subratllat simple) però és el patró documentat pel propi Streamlit. No cal agafar la URL dels secrets ni usar `conn.client._client.open_by_url(...)` directament.

### Crear pestanya si no existeix

```python
import gspread

def _assegurar_pestanya(conn, nom: str, rows: int = 20, cols: int = 2) -> None:
    sh = _spreadsheet(conn)
    try:
        sh.worksheet(nom)
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=nom, rows=rows, cols=cols)
```

### Afegir columna a pestanya existent

```python
def _assegurar_columna(conn, nom_col: str, valor_defecte: str = "") -> None:
    sh = _spreadsheet(conn)
    ws = sh.get_worksheet(0)   # pestanya principal = índex 0
    capçaleres = ws.row_values(1)
    if nom_col in capçaleres:
        return
    nova_col = len(capçaleres) + 1
    lletra = _col_letter(nova_col)
    ws.update_cell(1, nova_col, nom_col)
    n_files = len(ws.get_all_values()) - 1
    if n_files > 0:
        ws.update(f"{lletra}2:{lletra}{n_files + 1}", [[valor_defecte]] * n_files)

def _col_letter(n: int) -> str:
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result
```

### Pauta d'ús a app.py

Cridar les funcions d'esquema **una sola vegada a l'arrencada**, just després de `conn = st.connection(...)` i **abans** de `conn.read()`:

```python
conn = st.connection("gsheets", type=GSheetsConnection)
inicialitzar_config(conn)          # crea Config_Autonom si cal
_assegurar_columna_aplica_iva(conn) # migració idempotent de columna
config_autonom = carregar_config(conn)
```

### Coerció tipada obligatòria en llegir config clau-valor

> **Regla**: Sheets retorna **tot com a string**. Els booleans es serialitzen `"TRUE"`/`"FALSE"` (majúscules), no com Python `True`/`False`. Qualsevol config clau-valor llegida des de Sheets ha de passar per coerció explícita.

```python
TIPUS_CONFIG = {
    "clau_bool": "bool",       # "TRUE"/"FALSE"/"1" → bool
    "clau_int": "int",         # "4" → 4
    "clau_float": "float",     # "0.15" → 0.15; "False" → 0.0 (robust)
    "clau_date": "date",       # "2026-09-01" → date(2026,9,1)
    "clau_date_opt": "date_optional",  # "" / "nan" → None
    "clau_str": "str",         # passthrough
}

def _coerce(valor, tipus: str):
    s = str(valor).strip()
    if tipus == "bool":
        return s.lower() in ("true", "1", "yes", "sí", "si")
    if tipus == "float":
        try: return float(s)
        except (ValueError, TypeError): return 0.0
    # ... (veure core/config_autonom.py per implementació completa)
```

**Mai** comparar directament `config["iva_per_defecte"] == "TRUE"` — usar `config["iva_per_defecte"] is True` després de la coerció.

### Quan NO cal gspread

- Llegir dades → `conn.read(worksheet=..., ttl=N)`
- Escriure/actualitzar dades existents → `conn.update(worksheet=..., data=df)`
- Gspread **només** per a: crear worksheets, afegir/eliminar columnes, canviar format.

---

## Gestió de quota Google Sheets

Google Sheets API limita **60 operacions/minut/usuari**. Streamlit rerenderitza l'script sencer a cada interacció, de manera que qualsevol crida sense cache s'executa N vegades per sessió.

### Regla 1 — Operacions d'efecte secundari (schema): `@st.cache_resource`

Funcions que creen pestanyes o afegeixen columnes s'han d'executar **exactament un cop per sessió**:

```python
@st.cache_resource(show_spinner=False)
def _assegurar_pestanya(_conn) -> bool:
    """_conn amb subratllat: Streamlit omet el hash d'aquest argument."""
    sh = _conn.client._open_spreadsheet()
    try:
        sh.worksheet(NOM_PESTANYA)
    except gspread.WorksheetNotFound:
        sh.add_worksheet(title=NOM_PESTANYA, rows=20, cols=2)
    return True
```

> **Per què `_conn` i no `conn`?** Streamlit no sap fer hash d'objectes de connexió. El subratllat li diu "no facis hash d'aquest argument" — convenció obligatòria per a `cache_resource` i `cache_data`.

> **Per què `cache_resource` i no `cache_data`?** `cache_resource` és per a recursos amb estat (connexions, models carregats, garanties d'esquema). No es serialitza. `cache_data` és per a dades pures que es poden serialitzar i comparar.

### Regla 2 — Lectures de dades: `@st.cache_data(ttl=300)`

TTL de 5 minuts equilibra frescor i quota. La invalidació explícita amb `st.cache_data.clear()` garanteix consistència immediatament després d'escriure:

```python
@st.cache_data(ttl=300)
def carregar_config(_conn) -> dict:
    return _carregar_config_raw(_conn)

def guardar_config(conn, config: dict) -> None:
    conn.update(worksheet=PESTANYA, data=pd.DataFrame(files))
    st.cache_data.clear()  # invalida totes les lectures per a la propera rerenderització
```

### Regla 3 — Mai `ttl=0` a l'arrencada

`conn.read(ttl=0)` força una lectura fresca a cada rerun. A les funcions `inicialitzar_*`, usar `ttl=300`:

```python
def inicialitzar_config(conn) -> None:
    _assegurar_pestanya(conn)           # cached: 0 crides extra
    try:
        df = conn.read(worksheet=PESTANYA, ttl=300)  # cached: 1 crida/5 min
        if df is not None and not df.empty and "clau" in df.columns:
            return
    except Exception:
        pass
    guardar_config(conn, DEFAULTS.copy())
```

### Patró de diagnòstic si apareix quota 429

1. Buscar totes les crides a `_open_spreadsheet()`, `worksheet()`, `row_values()` sense `@st.cache_resource`.
2. Buscar tots els `conn.read(ttl=0)` o `conn.read()` sense TTL.
3. Verificar que totes les `_assegurar_*` retornen `bool` (el valor retornat és el que `cache_resource` guarda).
4. Esperar 60 s per deixar que la quota es recuperi abans de reiniciar.
