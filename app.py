import streamlit as st
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types
import json
import time
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import uuid
from core.config_autonom import (
    carregar_config, guardar_config, inicialitzar_config,
    _assegurar_columna_aplica_iva, es_mode_preview,
)
from core.autonom import (
    tram_actual, calcular_quota_ss, calcular_provisio_freelance,
    calcular_buffers_trimestre, tarifa_plana_estat, proxim_venciment,
    trimestre_de, TARIFA_PLANA_AMB_MEI,
)
from core.pressupostos import (
    inicialitzar_pressupostos, carregar_pressupostos, guardar_pressupostos,
    calcular_estats_categoria, CATEGORIES_DESPESA,
)
from core.config_app import (
    carregar_config_app, guardar_config_app, inicialitzar_config_app,
)
from core.cash_flow import (
    projectar_saldo, detectar_alertes_saldo, saldo_minim_previst, proximes_ocurrencies,
)
from core.anomalies import detectar_totes_anomalies


APP_VERSION = "v3.0 - Insights Edition"
GEMINI_MODEL = "gemini-2.5-flash"
GSHEETS_TTL = 60
MAX_IMG_BYTES = 5 * 1024 * 1024

# --- 1. CONFIGURACIÓ DE PÀGINA I ESTILS PREMIUM ---
st.set_page_config(page_title=f"Família Finances {APP_VERSION}", page_icon="🏦", layout="wide")

# CSS CUSTOM — Sistema de disseny complet (Fase 1)
st.markdown("""
<style>
    /* === VARIABLES DE PALETA === */
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

    /* === TIPOGRAFIA === */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                     "Helvetica Neue", Arial, sans-serif;
        font-feature-settings: "kern", "liga", "tnum";
    }
    h1, h2, h3 { color: var(--text-primary); }

    /* === LAYOUT GLOBAL === */
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    header[data-testid="stHeader"]::before { display: none; }
    .block-container { max-width: 1280px; margin: 0 auto; padding-top: 2rem; }

    /* === MÈTRIQUES === */
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

    /* === PESTANYES === */
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

    /* === CARDS PERSONALITZADES === */
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

    /* === COLORS UTILITARIS === */
    .text-success { color: var(--success); }
    .text-danger  { color: var(--danger); }
    .text-muted-cls { color: var(--text-muted); }

    /* === INPUTS === */
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

    /* === RESPONSIVE MÒBIL === */
    @media (max-width: 640px) {
        div[data-testid="stMetric"] { padding: 12px 14px; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.85rem;
            padding: 0 12px;
            height: 42px;
        }
        .block-container { padding-top: 0.5rem !important; }
        /* Grid 2×2 — afecta totes les st.columns(); st.columns(2) queda 50%/50% */
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 8px; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 calc(50% - 8px) !important;
            min-width: calc(50% - 8px) !important;
            width: calc(50% - 8px) !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 🔒 SISTEMA DE SEGURETAT ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Accés Restringit")
    st.text_input("Contrasenya", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contrasenya incorrecta")
    return False

if not check_password():
    st.stop()

# --- CONNEXIONS ---
API_KEY = st.secrets["GEMINI_API_KEY"]
conn = st.connection("gsheets", type=GSheetsConnection)
client = genai.Client(api_key=API_KEY)
inicialitzar_config(conn)
_assegurar_columna_aplica_iva(conn)
config_autonom = carregar_config(conn)
inicialitzar_pressupostos(conn)
inicialitzar_config_app(conn)
config_app = carregar_config_app(conn)

# --- HELPERS DE RESILIÈNCIA ---
def amb_reintents(fn, *args, intents=3, base=1.0, **kwargs):
    """Executa fn amb backoff exponencial. Reintenta només en errors de quota/xarxa."""
    ultim_error = None
    for i in range(intents):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            ultim_error = e
            msg = str(e).lower()
            transitori = any(t in msg for t in ["429", "quota", "rate", "timeout", "unavailable", "503", "500"])
            if not transitori or i == intents - 1:
                raise
            time.sleep(base * (2 ** i))
    raise ultim_error

def parsejar_json_ia(text):
    """Neteja la resposta de Gemini i la converteix sempre a llista de dicts."""
    txt = text.replace("```json", "").replace("```", "").strip()
    dades = json.loads(txt)
    if isinstance(dades, dict):
        dades = [dades]
    return dades

# --- FUNCIONS DE DADES (AMB PROTECCIÓ D'API) ---
def carregar_dades():
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "aplica_iva", "es_periodic", "id_grup"]
    try:
        df = amb_reintents(conn.read, ttl=GSHEETS_TTL)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnes_base)

        for col in columnes_base:
            if col not in df.columns:
                df[col] = ""

        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df['quantitat'] = pd.to_numeric(df['quantitat'], errors='coerce')
        df = df.dropna(subset=['data', 'quantitat'])
        df['data'] = df['data'].dt.date

        cols_str = ['establiment', 'concepte', 'categoria', 'tipus', 'id_grup']
        for c in cols_str:
            df[c] = df[c].fillna("").astype(str)

        df['es_periodic'] = df['es_periodic'].astype(str).map(
            {'TRUE': True, 'True': True, 'true': True, '1': True, '1.0': True}
        ).fillna(False).astype(bool)

        df['aplica_iva'] = df['aplica_iva'].astype(str).map(
            {'TRUE': True, 'True': True, 'true': True, '1': True, '1.0': True}
        ).fillna(False).astype(bool)

        return df
    except Exception as e:
        msg = str(e).lower()
        if any(t in msg for t in ["429", "quota", "rate"]):
            st.warning("⏳ Google Sheets té massa peticions ara mateix. Reintenta en uns segons.")
        else:
            st.error(f"⚠️ No s'han pogut carregar les dades: {str(e)[:200]}")
        return pd.DataFrame(columns=columnes_base)

def carregar_recurrents():
    columnes_req = ["concepte", "quantitat", "categoria", "tipus", "dia", "frequencia"]
    try:
        df_rec = amb_reintents(conn.read, worksheet="Recurrents", ttl=GSHEETS_TTL)
        if df_rec is None or df_rec.empty:
            return pd.DataFrame(columns=columnes_req)

        if "frequencia" not in df_rec.columns:
            df_rec["frequencia"] = "Mensual"

        return df_rec
    except Exception:
        st.warning("⚠️ No s'ha pogut carregar la pestanya de Recurrents o no existeix.")
        return pd.DataFrame(columns=columnes_req)

def guardar_dades(df_nou):
    amb_reintents(conn.update, data=df_nou)
    st.cache_data.clear()

def guardar_recurrents(df_rec_nou):
    amb_reintents(conn.update, worksheet="Recurrents", data=df_rec_nou)
    st.cache_data.clear()

# --- LÒGICA AUTOMÀTICA ---
FREQ_MESOS = {
    "Mensual": set(range(1, 13)),
    "Trimestral": {1, 4, 7, 10},
    "Semestral": {1, 7},
    "Anual": {1},
}

def comprovar_recurrents_pendents(df_actual, df_config):
    if df_config.empty or df_actual.empty:
        return []

    avui = date.today()
    mes_actual, any_actual = avui.month, avui.year

    # Vectoritzem la conversió de dates un sol cop
    dates_dt = pd.to_datetime(df_actual['data'], errors='coerce')
    mask_periode = (dates_dt.dt.month == mes_actual) & (dates_dt.dt.year == any_actual)
    df_periode = df_actual[mask_periode]

    moviments_a_afegir = []

    for rec in df_config.to_dict('records'):
        try:
            freq = rec.get('frequencia', 'Mensual')
            if mes_actual not in FREQ_MESOS.get(freq, set()):
                continue

            dia_fix = int(rec['dia'])
            try:
                data_tocaria = date(any_actual, mes_actual, dia_fix)
            except ValueError:
                # Dia inexistent en el mes (ex: 31 de febrer) → últim dia del mes
                seguent = date(any_actual, mes_actual, 28) + timedelta(days=4)
                data_tocaria = seguent.replace(day=1) - timedelta(days=1)

            if avui < data_tocaria:
                continue

            concepte = rec['concepte']
            quantitat = rec['quantitat']

            duplicat = (df_periode['concepte'] == concepte) & \
                       ((df_periode['quantitat'] - quantitat).abs() < 0.01)
            saltat = df_periode['concepte'] == f"SALTAT: {concepte}"

            if (duplicat | saltat).any():
                continue

            moviments_a_afegir.append({
                "data": data_tocaria,
                "concepte": concepte,
                "establiment": "Recurrent Automàtic",
                "quantitat": quantitat,
                "categoria": rec['categoria'],
                "tipus": rec['tipus'],
                "es_periodic": True,
                "Acció": "Afegir"
            })
        except Exception:
            continue

    return moviments_a_afegir

# Carreguem dades globals
df = carregar_dades()
df_recurrents_config = carregar_recurrents()

# --- PROTECCIÓ DE SIGNE DE QUANTITAT (ROBUSTA) ---
PARAULES_INGRES = {"ingrés", "ingres", "ingressos", "nòmina", "nomina", "bizum rebut", "income"}

def corregir_signe(quantitat, tipus):
    try:
        if quantitat is None:
            return 0.0
        q_abs = abs(float(quantitat))
    except (ValueError, TypeError):
        return 0.0

    if q_abs == 0:
        return 0.0

    tipus_norm = str(tipus or "").strip().lower()
    es_ingres = tipus_norm in PARAULES_INGRES or any(p in tipus_norm for p in PARAULES_INGRES)
    return q_abs if es_ingres else -q_abs

# --- ANALYTICS HELPERS ---
def saldo_mes(df: pd.DataFrame, any_: int, mes: int) -> float:
    if df.empty:
        return 0.0
    dates_dt = pd.to_datetime(df['data'], errors='coerce')
    mask = (dates_dt.dt.year == any_) & (dates_dt.dt.month == mes)
    return float(df.loc[mask, 'quantitat'].sum())

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

def prompt_resum_anomalies(anomalies: dict) -> str:
    n_var = len(anomalies.get("variacions", []))
    n_ind = len(anomalies.get("individuals", []))
    n_nov = len(anomalies.get("noves", []))
    if n_var + n_ind + n_nov == 0:
        return ""
    linies = []
    for v in anomalies.get("variacions", []):
        signe = "+" if v["variacio_pct"] > 0 else ""
        linies.append(
            f"- Categoria {v['categoria']}: {signe}{v['variacio_pct']:.0f}% vs mesos anteriors "
            f"(actual {v['actual_normalitzat']:.0f}€, mitjana {v['mitjana_historic']:.0f}€)"
        )
    for i in anomalies.get("individuals", []):
        linies.append(
            f"- Despesa individual alta: {i['concepte']} de {i['quantitat']:.0f}€ "
            f"({i['factor']:.1f}x la mediana de {i['categoria']})"
        )
    for n in anomalies.get("noves", []):
        linies.append(
            f"- Categoria nova aquest mes: {n['categoria']} ({n['total']:.0f}€, {n['moviments']} moviments)"
        )
    return (
        "Ets un assessor financer per a la família Jose Manuel i Alba.\n"
        "Has detectat les següents anomalies de despesa aquest mes:\n\n"
        + "\n".join(linies)
        + "\n\nGenera un resum breu (màxim 150 paraules) en català, to proper, amb:\n"
        "1. Una frase de context global (preocupant o no?).\n"
        "2. La 1 o 2 anomalies més rellevants amb consell concret.\n"
        "3. Una frase de tancament positiu o d'acció.\n\n"
        "Sense introduccions ni salutacions. Markdown amb ** per a èmfasis."
    )


@st.cache_data(ttl=3600)
def _generar_resum_ia_cached(_client, model: str, prompt: str) -> str:
    if not prompt:
        return ""
    try:
        res = amb_reintents(_client.models.generate_content, model=model, contents=prompt)
        return res.text
    except Exception as e:
        return f"⚠️ No s'ha pogut generar el resum: {str(e)[:100]}"


# --- CALLBACK PER AL TEXT ---
def processar_text_callback():
    text_val = st.session_state.get("input_text_key", "")
    if not text_val:
        return

    prompt_comu = (
        f"AVUI ÉS: {date.today()}. Analitza text. Retorna LLISTA JSON: "
        "'data' (YYYY-MM-DD), 'concepte', 'establiment', 'quantitat' (Número), "
        "'categoria', 'tipus' (Despesa/Ingrés), 'es_periodic' (bool). "
        "Si usuari diu 'Ahir', calcula data."
    )

    try:
        res = amb_reintents(client.models.generate_content, model=GEMINI_MODEL, contents=[prompt_comu, text_val])
        dades = parsejar_json_ia(res.text)

        noves = []
        msg_resum = ""
        grup = "TXT_" + str(uuid.uuid4())[:8]

        _iva_per_defecte = config_autonom.get("iva_per_defecte", True)
        for item in dades:
            tipus_final = item.get('tipus', 'Despesa')
            quant_final = corregir_signe(item.get('quantitat', 0), tipus_final)

            noves.append({
                "data": item.get('data') or date.today(),
                "concepte": item.get('concepte', 'Varies'),
                "establiment": item.get('establiment', ''),
                "quantitat": quant_final,
                "categoria": item.get('categoria', 'Altres'),
                "tipus": tipus_final,
                "aplica_iva": _iva_per_defecte if tipus_final == "Ingrés" else False,
                "es_periodic": bool(item.get('es_periodic', False)),
                "id_grup": grup,
            })
            msg_resum += f"- {item.get('concepte')}: {quant_final}€\n"

        df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
        guardar_dades(df_final)

        st.session_state["ultim_moviment"] = msg_resum
        st.session_state.input_text_key = ""
        st.success("Afegit correctament!")

    except json.JSONDecodeError:
        st.error("La IA no ha retornat un JSON vàlid. Prova a reformular el text.")
    except Exception as e:
        st.error(f"Error processant: {str(e)[:200]}")

# --- BARRA LATERAL (part 1: filtres) ---
avui = date.today()
with st.sidebar:
    st.title("🏦 Família Finances")
    st.caption(f"{APP_VERSION} - Jose & Alba Edition")
    st.divider()

    st.subheader("📅 Filtres")
    opcio_data = st.selectbox("Període", ["Aquest Mes", "Mes Anterior", "Tot l'any", "Personalitzat"])

    if opcio_data == "Aquest Mes":
        inici = avui.replace(day=1)
        fi = avui
    elif opcio_data == "Mes Anterior":
        primer = avui.replace(day=1)
        fi = primer - timedelta(days=1)
        inici = fi.replace(day=1)
    elif opcio_data == "Tot l'any":
        inici = avui.replace(month=1, day=1)
        fi = avui
    else:
        c1, c2 = st.columns(2)
        with c1:
            inici = st.date_input("Inici", avui - timedelta(days=30))
        with c2:
            fi = st.date_input("Fi", avui)

if not df.empty:
    mask = (df['data'] >= inici) & (df['data'] <= fi)
    df_filtrat = df.loc[mask]
else:
    df_filtrat = df

pressupostos = carregar_pressupostos(conn)
if opcio_data == "Aquest Mes":
    estats = calcular_estats_categoria(df_filtrat, pressupostos, avui)
else:
    estats = {}

# --- PREVISIÓ DE SALDO (global, per a sidebar i dashboard) ---
saldo_actual = float(df["quantitat"].sum()) if not df.empty else 0.0
llindar_alerta = config_app["llindar_alerta_saldo"]
horitzo_defecte = config_app["horitzo_projeccio_dies"]


def _rec_a_dict(df_rec: pd.DataFrame) -> list[dict]:
    if df_rec.empty:
        return []
    freqs_suportades = {"Mensual", "Trimestral", "Anual", "Setmanal"}
    result = []
    for rec in df_rec.to_dict("records"):
        try:
            dia = int(float(str(rec.get("dia", 1))))
            import_ = float(str(rec.get("quantitat", 0)))
            freq = str(rec.get("frequencia", "Mensual"))
            nom = str(rec.get("concepte", "Recurrent"))
            if dia >= 1 and freq in freqs_suportades:
                result.append({"nom": nom, "import": import_, "frequencia": freq, "dia": dia})
        except (ValueError, TypeError):
            continue
    return result


recurrents_llista = _rec_a_dict(df_recurrents_config)
df_proj_full = projectar_saldo(saldo_actual, recurrents_llista, avui, dies=90)
alertes_saldo = detectar_alertes_saldo(df_proj_full, llindar=llindar_alerta)
anomalies = detectar_totes_anomalies(df, avui, config_app)

# --- BARRA LATERAL (part 2: alertes + notificacions) ---
with st.sidebar:
    _n_anomalies = sum(len(anomalies.get(k, [])) for k in ("variacions", "individuals", "noves"))
    if _n_anomalies > 0:
        st.markdown("### 🔍 Anomalies detectades")
        st.warning(f"{_n_anomalies} anomalia(es) aquest mes · Veure pestanya Insights")

    if alertes_saldo:
        st.markdown("### 💧 Alertes liquiditat")
        primera = alertes_saldo[0]
        st.error(f"Saldo sota {llindar_alerta:.0f}€ a partir del {primera['data'].strftime('%d %b')}")
        if len(alertes_saldo) > 1:
            st.caption(f"+ {len(alertes_saldo) - 1} períodes més")

    if opcio_data == "Aquest Mes":
        estats_alerta = [(cat, e) for cat, e in estats.items() if e["estat"] == "vermell"]
        if estats_alerta:
            st.markdown("### ⚠️ Alertes pressupost")
            for cat, e in estats_alerta:
                st.error(
                    f"**{cat}**: {e['pct_consumit']*100:.0f}% consumit "
                    f"(esperat {e['pct_esperat']*100:.0f}%)"
                )
            st.divider()

    # Avisos Recurrents
    pendents = comprovar_recurrents_pendents(df, df_recurrents_config)
    if pendents:
        st.warning(f"🔔 {len(pendents)} Avisos pendents")
        with st.expander("Gestionar", expanded=True):
            df_pendents = pd.DataFrame(pendents)
            editat_pendents = st.data_editor(
                df_pendents,
                column_config={
                    "Acció": st.column_config.SelectboxColumn("Acció", options=["Afegir", "Saltar (Ignorar)", "Deixar Pendent"], required=True),
                    "concepte": st.column_config.TextColumn("Concepte", disabled=True),
                    "quantitat": st.column_config.NumberColumn("€", format="%.2f €", disabled=True),
                    "data": None, "establiment": None, "categoria": None, "tipus": None, "es_periodic": None, "id_grup": None
                },
                hide_index=True, key="side_editor"
            )

            if st.button("🚀 Processar"):
                noves = []
                for index, row in editat_pendents.iterrows():
                    if row['Acció'] == "Afegir":
                        nou_mov = row.to_dict()
                        del nou_mov['Acció']
                        nou_mov['id_grup'] = "AUTO_" + str(uuid.uuid4())[:8]
                        noves.append(nou_mov)

                    elif row['Acció'] == "Saltar (Ignorar)":
                        noves.append({
                            "data": row['data'],
                            "concepte": f"SALTAT: {row['concepte']}",
                            "establiment": "Sistema",
                            "quantitat": 0.0,
                            "categoria": row['categoria'],
                            "tipus": row['tipus'],
                            "es_periodic": False,
                            "id_grup": "SKIP_" + str(uuid.uuid4())[:8]
                        })

                if noves:
                    df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
                    guardar_dades(df_final)
                    st.rerun()
    elif not df.empty:
        st.success("✅ Tot al dia")

    st.divider()
    if "ultim_moviment" in st.session_state and st.session_state["ultim_moviment"]:
        st.info(f"🚀 **Últims afegits:**\n\n{st.session_state['ultim_moviment']}")
        if st.button("Netejar avís"):
            del st.session_state["ultim_moviment"]
            st.rerun()
    st.divider()

    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()

# =================================================
# 1. DASHBOARD PREMIUM
# =================================================

ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum() if not df_filtrat.empty else 0.0
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum() if not df_filtrat.empty else 0.0
saldo = df_filtrat['quantitat'].sum() if not df_filtrat.empty else 0.0

# --- Hero card amb delta vs període anterior ---
if opcio_data in ("Aquest Mes", "Mes Anterior"):
    period_mes = inici.month
    period_any = inici.year
    prev_mes = period_mes - 1 if period_mes > 1 else 12
    prev_any = period_any if period_mes > 1 else period_any - 1
    saldo_ant = saldo_mes(df, prev_any, prev_mes)
    if saldo_ant != 0:
        delta_eur = saldo - saldo_ant
        delta_pct = (delta_eur / abs(saldo_ant)) * 100
        signe = "▲" if delta_eur >= 0 else "▼"
        cls = "text-success" if delta_eur >= 0 else "text-danger"
        delta_html = (
            f'<span class="{cls}" style="font-size:0.95rem;font-weight:600">'
            f'{signe} {delta_eur:+,.2f} € ({delta_pct:+.1f}%)</span>'
        )
    else:
        delta_html = '<span class="text-muted-cls" style="font-size:0.9rem">Sense dades del mes anterior</span>'
else:
    delta_html = '<span class="text-muted-cls" style="font-size:0.9rem">—</span>'

st.markdown(
    f'<div class="custom-card accent" style="text-align:center;padding:28px 24px;margin-bottom:20px;">'
    f'<div class="card-title">💰 Saldo del Període</div>'
    f'<div style="font-size:2.8rem;font-weight:700;font-variant-numeric:tabular-nums;margin:8px 0;">'
    f'{saldo:,.2f} €</div>'
    f'<div style="margin-top:6px;">{delta_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# --- 4 mètriques ---
taxa_estalvi = ((ingr + desp) / ingr * 100) if ingr > 0 else None

avui_metrics = date.today()
if avui_metrics.month == 12:
    ultim_dia_mes = date(avui_metrics.year + 1, 1, 1) - timedelta(days=1)
else:
    ultim_dia_mes = date(avui_metrics.year, avui_metrics.month + 1, 1) - timedelta(days=1)
dies_restants = (ultim_dia_mes - avui_metrics).days

col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Ingressos", f"{ingr:,.2f} €")
col2.metric("🔴 Despeses", f"{abs(desp):,.2f} €")
if taxa_estalvi is not None:
    delta_avis = "⚠ Gastes més del que ingressos" if taxa_estalvi < 0 else None
    col3.metric("💎 Taxa Estalvi", f"{taxa_estalvi:.1f}%",
                delta=delta_avis, delta_color="inverse" if taxa_estalvi < 0 else "normal")
else:
    col3.metric("💎 Taxa Estalvi", "—")
if opcio_data == "Aquest Mes":
    col4.metric("📅 Dies Restants", f"{dies_restants} dies")
else:
    dies_periode = (fi - inici).days + 1
    col4.metric("📅 Durada", f"{dies_periode} dies")

vista_grafic = st.segmented_control(
    "Visualització:",
    ["Evolució Saldo", "Despeses per Categoria", "Detall Ingressos"],
    default="Evolució Saldo",
    label_visibility="collapsed",
)

if not df_filtrat.empty:
    if vista_grafic == "Evolució Saldo":
        ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
        ev['saldo_acumulat'] = ev['quantitat'].cumsum()
        fig = px.bar(ev, x='data', y='quantitat', color='quantitat', color_continuous_scale=px.colors.diverging.RdYlGn)
        st.plotly_chart(aplicar_tema(fig, "Flux Diari"), width="stretch")

    elif vista_grafic == "Despeses per Categoria":
        df_desp = df_filtrat[df_filtrat['quantitat'] < 0].copy()
        if not df_desp.empty:
            df_desp['valor'] = df_desp['quantitat'].abs()
            fig = px.pie(df_desp, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(aplicar_tema(fig, "On van els diners?"), width="stretch")
        else:
            st.info("📊 Cap despesa en aquest període. Afegeix moviments o canvia el filtre de dates.")

    elif vista_grafic == "Detall Ingressos":
        df_ing = df_filtrat[df_filtrat['quantitat'] > 0]
        if not df_ing.empty:
            fig = px.bar(df_ing, x='categoria', y='quantitat', color='concepte')
            st.plotly_chart(aplicar_tema(fig, "Fonts d'Ingrés"), width="stretch")
        else:
            st.info("💰 Cap ingrés en aquest període. Afegeix moviments o canvia el filtre de dates.")

# --- ESTAT PRESSUPOSTOS (dashboard, "Aquest Mes" only) ---
if opcio_data == "Aquest Mes" and estats:
    estats_actius = {k: v for k, v in estats.items() if v["estat"] != "sense_pressupost"}
    if estats_actius:
        st.markdown("### 📊 Estat dels pressupostos")

        def _render_progress_pp(pct: float, estat: str) -> None:
            color_var = {
                "verd": "var(--success)",
                "groc": "var(--warning)",
                "vermell": "var(--danger)",
            }[estat]
            bar_width = min(pct * 100, 100)
            st.markdown(
                f'<div style="background:var(--bg-subtle);border-radius:8px;height:12px;overflow:hidden;">'
                f'<div style="background:{color_var};height:100%;width:{bar_width:.1f}%;transition:width 0.3s ease;"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        _EMOJI_PP = {"verd": "🟢", "groc": "🟡", "vermell": "🔴"}
        for _cat, _e in estats_actius.items():
            _import_mensual = pressupostos.get(_cat, 0.0)
            _despesa_cat = _import_mensual - _e["restant"]
            _c1, _c2, _c3 = st.columns([4, 5, 1])
            with _c1:
                st.markdown(f"**{_cat}**")
                st.caption(f"{_despesa_cat:,.0f} / {_import_mensual:,.0f} €")
            with _c2:
                _render_progress_pp(_e["pct_consumit"], _e["estat"])
                st.caption(f"{_e['pct_consumit']*100:.0f}% · queden {_e['restant']:,.0f} €")
            with _c3:
                st.markdown(
                    f'<div style="text-align:center;font-size:1.3rem;margin-top:4px">'
                    f'{_EMOJI_PP[_e["estat"]]}</div>',
                    unsafe_allow_html=True,
                )

# --- PREVISIÓ DE SALDO ---
if not df.empty:
    st.markdown("### 🔮 Previsió de saldo")

    _horitzo_ui = st.segmented_control(
        "Horitzó",
        [30, 60, 90],
        default=horitzo_defecte if horitzo_defecte in [30, 60, 90] else 60,
        key="seg_horitzo",
        label_visibility="collapsed",
    )
    if _horitzo_ui is None:
        _horitzo_ui = horitzo_defecte if horitzo_defecte in [30, 60, 90] else 60

    df_proj = df_proj_full[df_proj_full["data"] <= avui + timedelta(days=_horitzo_ui)].copy()

    # Mètrica 1: saldo a 30 dies
    _data_30 = avui + timedelta(days=30)
    _row_30 = df_proj[df_proj["data"] == _data_30]
    _saldo_30 = float(_row_30.iloc[0]["saldo_previst"]) if not _row_30.empty else saldo_actual
    _delta_30 = _saldo_30 - saldo_actual

    # Mètrica 2: saldo mínim
    _data_min_proj, _val_min_proj = saldo_minim_previst(df_proj)

    # Mètrica 3: pròxim moviment gran (|import| >= 200)
    _proxim_gran = None
    for _r in recurrents_llista:
        if abs(_r["import"]) >= 200:
            _occ = proximes_ocurrencies(_r, avui + timedelta(days=1), avui + timedelta(days=_horitzo_ui))
            if _occ:
                _cand = {"data": _occ[0], "nom": _r["nom"], "import": _r["import"]}
                if _proxim_gran is None or _cand["data"] < _proxim_gran["data"]:
                    _proxim_gran = _cand

    _mc1, _mc2, _mc3 = st.columns(3)
    _mc1.metric(
        "Saldo previst (30 dies)",
        f"{_saldo_30:,.2f} €",
        delta=f"{_delta_30:+,.2f} €",
        delta_color="normal" if _delta_30 >= 0 else "inverse",
    )
    _mc2.metric(
        "Saldo mínim previst",
        f"{_val_min_proj:,.2f} €",
        delta=_data_min_proj.strftime("%d/%m/%Y"),
        delta_color="off",
    )
    if _proxim_gran:
        _mc3.metric(
            "Pròxim moviment gran",
            f"{_proxim_gran['import']:+,.0f} €",
            delta=f"{_proxim_gran['nom']} · {_proxim_gran['data'].strftime('%d/%m')}",
            delta_color="off",
        )
    else:
        _mc3.metric("Pròxim moviment gran", "—")

    # Moviments grans per al scatter del gràfic
    _mg_chart = []
    for _r in recurrents_llista:
        if abs(_r["import"]) >= 200:
            for _d in proximes_ocurrencies(_r, avui, avui + timedelta(days=_horitzo_ui)):
                _rrow = df_proj[df_proj["data"] == _d]
                if not _rrow.empty:
                    _mg_chart.append({
                        "data": _d,
                        "nom": _r["nom"],
                        "import": _r["import"],
                        "saldo": float(_rrow.iloc[0]["saldo_previst"]),
                    })

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=df_proj["data"],
        y=df_proj["saldo_previst"],
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.15)",
        line=dict(color="#6366f1", width=2),
        name="Saldo previst",
        hovertemplate="%{x|%d/%m/%Y}<br>Saldo: %{y:,.2f} €<extra></extra>",
    ))
    fig_proj.add_hline(
        y=llindar_alerta,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"Llindar {llindar_alerta:.0f} €",
        annotation_position="bottom right",
    )
    if _mg_chart:
        fig_proj.add_trace(go.Scatter(
            x=[m["data"] for m in _mg_chart],
            y=[m["saldo"] for m in _mg_chart],
            mode="markers",
            marker=dict(
                size=10,
                color=["#10b981" if m["import"] > 0 else "#ef4444" for m in _mg_chart],
                line=dict(width=1, color="white"),
            ),
            text=[f"{m['nom']} ({m['import']:+.0f}€)" for m in _mg_chart],
            hovertemplate="%{text}<br>%{x|%d/%m/%Y}<br>Saldo: %{y:,.2f}€<extra></extra>",
            name="Moviment gran",
        ))
    fig_proj.update_layout(
        yaxis=dict(tickformat=",.0f", ticksuffix=" €"),
        showlegend=False,
        hovermode="x unified",
    )
    st.plotly_chart(aplicar_tema(fig_proj, f"Projecció de saldo — {_horitzo_ui} dies"), width="stretch")

    # Alertes per a l'horitzó seleccionat
    _alertes_proj = detectar_alertes_saldo(df_proj, llindar=llindar_alerta)
    if _alertes_proj:
        st.markdown("⚠️ **Alertes de liquiditat detectades:**")
        for _al in _alertes_proj:
            st.warning(_al["missatge"])

    if not recurrents_llista:
        st.caption(
            "Sense moviments recurrents configurats, la projecció és constant. "
            "Configura'n a la pestanya ⚙️ Configurar Recurrents."
        )

# =================================================
# 2. PESTANYES
# =================================================
t1, t2, t5, t_ins, t3, t4 = st.tabs(["➕ Afegir Moviment", "✏️ Editar Dades", "🧾 Autònom", "🔍 Insights", "🧠 Assessoria IA", "⚙️ Configurar Recurrents"])

# --- TAB 1: INPUT ---
with t1:
    col_txt, col_foto = st.columns(2)
    with col_txt:
        st.text_area("Escriu aquí (Ex: Ahir 45€ Mercadona)", key="input_text_key", height=100)
        st.button("Enviar Text", on_click=processar_text_callback)

    with col_foto:
        imatges = st.file_uploader(
            "Pujar Tiquets", type=['jpg', 'jpeg', 'png'],
            accept_multiple_files=True
        )

        prompt_foto = f"""AVUI ÉS: {date.today().isoformat()}.

Tasca: Llegir un tiquet de compra (foto). Extreure cada producte com un moviment separat.
O, si el tiquet és global (sense desglossament), un sol moviment amb el total.

Retorna NOMÉS un array JSON. Sense text addicional, sense markdown wrappers.

Schema per moviment:
{{
  "data": "YYYY-MM-DD",
  "concepte": "string ≤40 chars",
  "establiment": "string (pot ser buit)",
  "quantitat": número positiu (mai negatiu),
  "categoria": una de [Llar, Subscripcions, Alimentació, Restauració, Transport,
                       Salut, Oci, Roba, Deute, Altres],
  "tipus": "Despesa",
  "es_periodic": false
}}

Regles:
- Establiment: extreure'l de la capçalera del tiquet.
- Data: la del tiquet, no avui. Si no es veu, posar avui.
- Tipus: sempre "Despesa".
- es_periodic: sempre false.
- Si la foto és il·legible, retorna [].
"""

        if imatges:
            st.caption(f"{len(imatges)} imatge(s) seleccionada(s)")
            cols_prev = st.columns(min(len(imatges), 4))
            for i, img_file in enumerate(imatges[:4]):
                with cols_prev[i]:
                    st.image(img_file, width="stretch")
            if len(imatges) > 4:
                st.caption(f"... i {len(imatges) - 4} més sense previsualitzar")

        if st.button("Processar Tiquets", type="primary", disabled=not imatges):
            noves_total = []
            msg_resum = ""
            errors = []

            progress = st.progress(0, text="Processant tiquets...")
            total = len(imatges)

            for idx, im in enumerate(imatges):
                progress.progress(idx / total, text=f"Processant {idx + 1}/{total}: {im.name}")

                if im.size > MAX_IMG_BYTES:
                    errors.append(f"**{im.name}**: massa gran ({im.size/1024/1024:.1f} MB, màx {MAX_IMG_BYTES//1024//1024} MB).")
                    continue

                try:
                    img_p = Image.open(im)
                    res = amb_reintents(client.models.generate_content, model=GEMINI_MODEL, contents=[prompt_foto, img_p])
                    dades = parsejar_json_ia(res.text)

                    grup = "IMG_" + str(uuid.uuid4())[:8]
                    for item in dades:
                        t_prov = item.get('tipus', 'Despesa')
                        if str(t_prov).strip().lower() not in PARAULES_INGRES:
                            t_prov = "Despesa"
                        quant_final = corregir_signe(item.get('quantitat', 0), t_prov)
                        noves_total.append({
                            "data": item.get('data') or date.today(),
                            "concepte": item.get('concepte') or "Tiquet",
                            "establiment": item.get('establiment') or "",
                            "quantitat": quant_final,
                            "categoria": item.get('categoria') or "Altres",
                            "tipus": t_prov,
                            "aplica_iva": False,
                            "es_periodic": False,
                            "id_grup": grup,
                        })
                        msg_resum += f"- {item.get('concepte')}: {quant_final}€\n"

                except json.JSONDecodeError:
                    errors.append(f"**{im.name}**: la IA no ha retornat un JSON vàlid. Prova amb una foto més clara.")
                except Exception as e:
                    errors.append(f"**{im.name}**: {str(e)[:150]}")

            progress.progress(1.0, text="Fet!")

            if noves_total:
                df_final = pd.concat([df, pd.DataFrame(noves_total)], ignore_index=True)
                guardar_dades(df_final)
                st.session_state["ultim_moviment"] = msg_resum

            if errors:
                st.error("Errors en alguns tiquets:\n\n" + "\n\n".join(errors))

            if noves_total:
                st.rerun()

# --- TAB INSIGHTS ---
with t_ins:
    st.subheader("🔍 Insights del mes")

    _var = anomalies.get("variacions", [])
    _ind = anomalies.get("individuals", [])
    _nov = anomalies.get("noves", [])
    _total_an = len(_var) + len(_ind) + len(_nov)

    if _total_an == 0:
        st.success("✅ Cap anomalia detectada aquest mes. Les despeses segueixen el patró habitual.")
    else:
        # Resum IA (cached 1h)
        _prompt_an = prompt_resum_anomalies(anomalies)
        _resum_ia = _generar_resum_ia_cached(client, GEMINI_MODEL, _prompt_an)
        if _resum_ia and not _resum_ia.startswith("⚠️"):
            st.markdown(
                '<div class="custom-card accent" style="margin-bottom:16px;">'
                '<div class="card-title">Resum IA</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_resum_ia)
            st.markdown("</div>", unsafe_allow_html=True)
        elif _resum_ia.startswith("⚠️"):
            st.warning(_resum_ia)

        # Variacions per categoria
        if _var:
            st.markdown("### 📈 Variació per categoria")
            for v in _var:
                _color = "var(--danger)" if v["tipus"] == "augment" else "var(--success)"
                _icon = "🔺" if v["tipus"] == "augment" else "🔻"
                _signe = "+" if v["variacio_pct"] > 0 else ""
                st.markdown(
                    f'<div class="custom-card" style="border-left: 4px solid {_color};margin-bottom:8px;">'
                    f'<strong>{_icon} {v["categoria"]}</strong> — '
                    f'<span style="color:{_color};font-weight:700;">{_signe}{v["variacio_pct"]:.0f}%</span>'
                    f'<br><span style="color:var(--text-secondary);font-size:0.9rem;">'
                    f'Actual: {v["actual_normalitzat"]:.0f}€ · Mitjana historial: {v["mitjana_historic"]:.0f}€</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Despeses individuals atípiques
        if _ind:
            st.markdown("### 💸 Despeses individuals atípiques")
            for i in _ind:
                _data_str = i["data"].strftime("%d/%m") if hasattr(i["data"], "strftime") else str(i["data"])
                st.markdown(
                    f'<div class="custom-card" style="border-left: 4px solid var(--warning);margin-bottom:8px;">'
                    f'<strong>⚠️ {i["concepte"]}</strong>'
                    + (f' · {i["establiment"]}' if i.get("establiment") else "")
                    + f'<br>'
                    f'<span style="color:var(--danger);font-weight:700;">{i["quantitat"]:.2f}€</span>'
                    f' — <span style="color:var(--text-secondary);font-size:0.9rem;">'
                    f'{i["factor"]:.1f}x la mediana ({i["mediana_categoria"]:.0f}€) de {i["categoria"]} · {_data_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Categories noves
        if _nov:
            st.markdown("### 🆕 Categories noves")
            for n in _nov:
                st.markdown(
                    f'<div class="custom-card" style="border-left: 4px solid var(--accent);margin-bottom:8px;">'
                    f'<strong>🆕 {n["categoria"]}</strong>'
                    f'<br><span style="color:var(--text-secondary);font-size:0.9rem;">'
                    f'{n["total"]:.2f}€ · {n["moviments"]} moviment(s) · No apareixia els 3 mesos anteriors</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.caption(
            f"Anàlisi sobre {len(df)} moviments totals. "
            "Llindar variació: "
            f"{config_app.get('llindar_anomalia_pct', 30.0):.0f}% · "
            f"Factor individual: {config_app.get('factor_mediana_atipica', 2.0):.1f}x"
        )

# --- TAB 3: ASSESSORIA ESTRATÈGICA ---
with t3:
    st.subheader("🧠 L'Assessor de la Família")
    st.info("Context familiar: Jose Manuel a punt de ser autònom (800–1.000€/mes), Alba nòmina ~1.300€/mes, lloguer rebut 550€/mes.")
    if st.button("Generar Anàlisi del Mes"):
        with st.spinner("Consultant l'estratègia amb Gemini..."):
            resum_cat = df_filtrat.groupby('categoria')['quantitat'].sum().to_string() if not df_filtrat.empty else "Sense dades"
            prompt_advisor = f"""Actua com un assessor financer expert per a una família catalana
(Jose Manuel i Alba) en transició cap a autònom.

CONTEXT:
- Jose Manuel: a punt de ser autònom (web/SEO/edició).
  Ingressos actuals 800–1.000€/mes amb previsió creixent.
  Tarifa plana 80€/mes el primer any (real ~88,64€ amb MEI 0,9%).
  Provisió necessària: ~20% IRPF + IVA si factura amb IVA.
- Alba: nòmina ~1.300€/mes (estable).
- Ingrés extra: lloguer 550€/mes (recurrent).
- Localització: Calders, Bages, Catalunya.

DADES DEL PERÍODE:
- Ingressos totals: {ingr:.2f}€
- Despeses totals: {desp:.2f}€
- Saldo: {ingr + desp:.2f}€
- Desglossament per categoria:
{resum_cat}

TASCA: Generar exactament 3 consells:
1) Un de provisió fiscal (autònom).
2) Un de fons d'emergència o estalvi (objectiu 3–6 mesos despeses fixes).
3) Un d'optimització de despesa concreta detectada al desglossament.

FORMAT:
- Markdown amb capçaleres ##.
- To proper, en català, sense paternalisme.
- Cada consell amb: 1 frase de diagnòstic + 1 frase d'acció concreta.
- Inclou xifres concretes, no generalitats.
- Màxim 200 paraules totals.

NO incloguis: introduccions, salutacions, disclaimers, "espero que t'ajudi".
"""
            try:
                res_adv = amb_reintents(client.models.generate_content, model=GEMINI_MODEL, contents=prompt_advisor)
                st.markdown(res_adv.text)
            except Exception as e:
                st.error(f"Error connectant amb l'assessor: {str(e)[:200]}")

# --- TAB 4: CONFIGURAR RECURRENTS ---
with t4:
    st.write("Configura els pagaments fixos. Ara pots triar la freqüència.")
    df_config_editat = st.data_editor(
        df_recurrents_config,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "concepte": st.column_config.TextColumn("Concepte", required=True),
            "quantitat": st.column_config.NumberColumn("€", required=True, format="%.2f €"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Llar", "Subscripcions", "Nòmina", "Deute", "Lloguer_Ingrés", "Ajut_Públic"], required=True),
            "tipus": st.column_config.SelectboxColumn("Tipus", options=["Despesa", "Ingrés"], required=True),
            "dia": st.column_config.NumberColumn("Dia", min_value=1, max_value=31, required=True),
            "frequencia": st.column_config.SelectboxColumn("Freqüència", options=["Mensual", "Trimestral", "Semestral", "Anual"], required=True, default="Mensual")
        },
        key="editor_recurrents"
    )
    if st.button("💾 Guardar Configuració"):
        guardar_recurrents(df_config_editat)
        st.success("Configuració actualitzada!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 💰 Pressupostos mensuals per categoria")
    _pp_df = pd.DataFrame([
        {"categoria": cat, "import_mensual": pressupostos.get(cat, 0.0)}
        for cat in CATEGORIES_DESPESA
    ])
    _pp_editat = st.data_editor(
        _pp_df,
        column_config={
            "categoria": st.column_config.TextColumn("Categoria", disabled=True),
            "import_mensual": st.column_config.NumberColumn(
                "Import mensual (€)",
                min_value=0.0,
                step=10.0,
                format="%.2f €",
            ),
        },
        hide_index=True,
        key="editor_pressupostos",
    )
    st.caption("Posa 0 a una categoria si no vols definir pressupost. L'app només alertarà de les categories amb import > 0.")
    if st.button("💾 Desar pressupostos", type="primary", key="btn_desar_pp"):
        nous_pp = dict(zip(_pp_editat["categoria"], _pp_editat["import_mensual"]))
        guardar_pressupostos(conn, nous_pp)
        st.cache_data.clear()
        st.success("Pressupostos actualitzats.")
        st.rerun()

    st.markdown("---")
    with st.expander("⚙️ Configuració general de l'app"):
        _nou_llindar = st.number_input(
            "Llindar d'alerta de saldo (€)",
            min_value=0.0,
            value=float(llindar_alerta),
            step=50.0,
            format="%.0f",
        )
        _nou_horitzo = st.selectbox(
            "Horitzó de projecció per defecte (dies)",
            options=[30, 60, 90],
            index=[30, 60, 90].index(horitzo_defecte) if horitzo_defecte in [30, 60, 90] else 1,
        )
        _nou_llindar_an = st.number_input(
            "Llindar anomalia per categoria (%)",
            min_value=5.0,
            max_value=200.0,
            value=float(config_app.get("llindar_anomalia_pct", 30.0)),
            step=5.0,
            format="%.0f",
            help="Variació mínima respecte la mitjana dels 3 mesos anteriors per generar alerta.",
        )
        _nou_factor_med = st.number_input(
            "Factor mediana despesa individual",
            min_value=1.1,
            max_value=10.0,
            value=float(config_app.get("factor_mediana_atipica", 2.0)),
            step=0.5,
            format="%.1f",
            help="Multiplicador sobre la mediana de la categoria per considerar una despesa atípica.",
        )
        if st.button("💾 Desar configuració", key="btn_desar_config_app"):
            guardar_config_app(conn, {
                "llindar_alerta_saldo": str(_nou_llindar),
                "horitzo_projeccio_dies": str(_nou_horitzo),
                "llindar_anomalia_pct": str(_nou_llindar_an),
                "factor_mediana_atipica": str(_nou_factor_med),
            })
            st.success("Configuració desada.")
            st.rerun()

# --- TAB 5: AUTÒNOM ---
with t5:
    _cfg = carregar_config(conn)
    _preview = es_mode_preview(_cfg)

    _factures_mes = _cfg.get("factures_aprox_mes", 4) or 4
    _retencio = _cfg.get("retencio_irpf_pct", 0.15) or 0.15
    _iva_def = _cfg.get("iva_per_defecte", True)
    _prorrogada = _cfg.get("tarifa_plana_prorrogada", False)

    # ── HEADER CARD ────────────────────────────────────────────────────
    if _preview:
        _alta_prev_date = _cfg.get("data_alta_prevista")
        _alta_prev = _alta_prev_date.isoformat() if _alta_prev_date else "—"
        _manual_url = "https://github.com/druidub/comptabilitat-familiar/blob/main/docs/MANUAL_AUTONOM.md"
        st.markdown(
            f'<div class="custom-card accent" style="margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;">'
            f'<div><span style="font-size:1.1rem;font-weight:700;">🔮 Mode Preview</span>'
            f'<span style="color:var(--text-secondary);margin-left:12px;">Alta prevista el {_alta_prev}</span></div>'
            f'<a href="{_manual_url}" target="_blank" style="font-size:0.8rem;color:var(--text-secondary);text-decoration:none;white-space:nowrap;">📖 Manual</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── SIMULADOR ──────────────────────────────────────────────────
        _ingres_mes = st.slider(
            "Ingressos mensuals previstos (€)", min_value=500, max_value=3000,
            step=100, value=1000,
        )
        _tram = tram_actual(_ingres_mes)
        _provisio = calcular_provisio_freelance(
            _ingres_mes / _factures_mes,
            aplica_iva=_iva_def,
            retencio_irpf_pct=_retencio,
            cuota_ss_mensual=TARIFA_PLANA_AMB_MEI,
            factures_aprox_mes=_factures_mes,
        )

        # Data salt quota
        try:
            from datetime import date as _date_cls
            _d_alta_prev = _date_cls.fromisoformat(_alta_prev)
            _any_salt = _d_alta_prev.year + (_d_alta_prev.month + 11) // 12
            _mes_salt = (_d_alta_prev.month + 11) % 12 + 1
            _salt_label = f"salt el {_date_cls(_any_salt, _mes_salt, 1).strftime('%b %Y')}"
        except Exception:
            _salt_label = "salt al mes 13"

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("📊 Tram estimat", f"Tram {_tram.numero}",
                   delta=f"{_tram.limit_inferior:,.0f}–{_tram.limit_superior if _tram.limit_superior != float('inf') else '∞':,.0f} €/mes",
                   delta_color="off")
        mc2.metric("💚 Quota tarifa plana", f"{TARIFA_PLANA_AMB_MEI:.2f} €/mes",
                   delta="12 mesos", delta_color="off")
        mc3.metric("📈 Quota després", f"{_tram.quota_minima:.0f} €/mes",
                   delta=f"⚠ {_salt_label}", delta_color="inverse")
        mc4.metric("💰 Net per factura", f"{_provisio.net_disponible:,.2f} €",
                   delta=f"base {_ingres_mes / _factures_mes:,.0f} €", delta_color="off")

        # ── DETALL PROVISIÓ ────────────────────────────────────────────
        st.markdown('<div class="custom-card" style="margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Provisió per factura mitjana</div>', unsafe_allow_html=True)
        _dc1, _dc2, _dc3, _dc4 = st.columns(4)
        _dc1.metric("IVA repercutit", f"{_provisio.iva_repercutit:,.2f} €")
        _dc2.metric("IRPF a apartar", f"{_provisio.irpf_provisio:,.2f} €")
        _dc3.metric("SS proporcional", f"{_provisio.cuota_ss_provisio:,.2f} €")
        _dc4.metric("Net disponible", f"{_provisio.net_disponible:,.2f} €")
        st.caption("⚠ Xifres orientatives. Valida amb gestor per a decisions reals.")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # ── MODE OPERATIU ──────────────────────────────────────────────
        _data_alta = _cfg.get("data_alta_real") or date.today()
        _alta_real_str = _data_alta.isoformat() if hasattr(_data_alta, "isoformat") else str(_data_alta)

        _estat_tp = tarifa_plana_estat(_data_alta, prorroga_activa=_prorrogada)
        _trim_actual = trimestre_de(date.today())
        _any_actual = date.today().year

        # Tram basat en últims 3 mesos de Freelance
        _df_freelance = df[df['categoria'] == 'Freelance'].copy() if not df.empty else pd.DataFrame()
        if not _df_freelance.empty and len(_df_freelance) >= 3:
            _ingressos_3m = _df_freelance.nlargest(3, 'data')['quantitat'].abs().mean() if not _df_freelance.empty else 0
            _tram_op = tram_actual(float(_ingressos_3m))
            _tram_label = f"Tram {_tram_op.numero}"
            _tram_delta = "basat en historial"
        else:
            _tram_op = tram_actual(800.0)
            _tram_label = "Tram 1–2"
            _tram_delta = "sense historial suficient"

        _quota_op = TARIFA_PLANA_AMB_MEI if _estat_tp["activa"] else _tram_op.quota_minima
        _vtrim, _vdata, _vdies = proxim_venciment()

        # Buffers del trimestre
        _movs_freelance = []
        if not df.empty and 'categoria' in df.columns:
            for _, _r in df[df['categoria'] == 'Freelance'].iterrows():
                _movs_freelance.append({
                    "data": _r['data'],
                    "quantitat": abs(float(_r['quantitat'])),
                    "aplica_iva": bool(_r.get('aplica_iva', _iva_def)),
                    "retencio_pct": _retencio,
                })
        _buffers = calcular_buffers_trimestre(_movs_freelance, _trim_actual, _any_actual,
                                              cuota_ss_mensual=_quota_op)

        _manual_url = "https://github.com/druidub/comptabilitat-familiar/blob/main/docs/MANUAL_AUTONOM.md"
        st.markdown(
            f'<div class="custom-card accent" style="margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;">'
            f'<div><span style="font-size:1.1rem;font-weight:700;">🟢 Mode Operatiu</span>'
            f'<span style="color:var(--text-secondary);margin-left:12px;">Alta el {_alta_real_str}</span></div>'
            f'<a href="{_manual_url}" target="_blank" style="font-size:0.8rem;color:var(--text-secondary);text-decoration:none;white-space:nowrap;">📖 Manual</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

        oc1, oc2, oc3, oc4 = st.columns(4)
        if _estat_tp["activa"]:
            oc1.metric("💚 Tarifa plana", f"{_estat_tp['mesos_restants']}/12 mesos",
                       delta=f"fi: {_estat_tp['data_fi'].strftime('%b %Y')}", delta_color="off")
        else:
            oc1.metric("💚 Tarifa plana", "Acabada",
                       delta=f"quota: {_tram_op.quota_minima:.0f} €/mes", delta_color="inverse")
        oc2.metric("📊 Tram actual", _tram_label, delta=_tram_delta, delta_color="off")
        oc3.metric("🏦 Apartat Q" + str(_trim_actual),
                   f"{_buffers.iva_acumulat + _buffers.irpf_acumulat + _buffers.ss_acumulat:,.2f} €",
                   delta=f"{_buffers.nombre_factures} factures", delta_color="off")
        oc4.metric("📅 Pròxim venciment", _vdata.strftime("%d/%m/%Y"),
                   delta=f"{_vdies} dies · Q{_vtrim}", delta_color="off")

        # ── BUFFERS AMB PROGRESS BARS ──────────────────────────────────
        st.markdown("---")
        if _buffers.nombre_factures == 0:
            st.info("📭 Encara no hi ha factures Freelance aquest trimestre.")
        else:
            st.markdown("**Buffers acumulats — Q" + str(_trim_actual) + f" {_any_actual}**")
            _obj_iva = _quota_op * 3 * 0.21 / 0.314 if _quota_op > 0 else _buffers.total_ingressos * 0.21
            _obj_iva = _buffers.total_ingressos * 0.21
            _obj_irpf = _buffers.total_ingressos * 0.20
            _obj_ss = _quota_op * 3

            def _progress_color(actual, objectiu):
                if objectiu <= 0:
                    return 1.0, "🟢"
                pct = actual / objectiu
                if pct >= 1.0:
                    return 1.0, "🟢"
                elif pct >= 0.70:
                    return pct, "🟡"
                else:
                    return pct, "🔴"

            _pct_iva, _ic_iva = _progress_color(_buffers.iva_acumulat, _obj_iva)
            _pct_irpf, _ic_irpf = _progress_color(_buffers.irpf_acumulat, _obj_irpf)
            _pct_ss, _ic_ss = _progress_color(_buffers.ss_acumulat, _obj_ss)

            st.markdown(f"{_ic_iva} **IVA acumulat:** {_buffers.iva_acumulat:,.2f} € / objectiu {_obj_iva:,.2f} €")
            st.progress(min(_pct_iva, 1.0))
            st.markdown(f"{_ic_irpf} **IRPF acumulat:** {_buffers.irpf_acumulat:,.2f} € / objectiu {_obj_irpf:,.2f} €")
            st.progress(min(_pct_irpf, 1.0))
            st.markdown(f"{_ic_ss} **SS acumulada:** {_buffers.ss_acumulat:,.2f} € / objectiu {_obj_ss:,.2f} €")
            st.progress(min(_pct_ss, 1.0))
            st.caption("⚠ Xifres orientatives. Valida amb gestor.")

    # ── TIQUET RURAL ───────────────────────────────────────────────────
    _tr_estat = _cfg.get("tiquet_rural_estat", "no_aplica")
    if _tr_estat and _tr_estat != "no_aplica":
        st.markdown("---")
        _tr_quantia = _cfg.get("tiquet_rural_quantia", 0.0) or 0.0
        _tr_data_res_date = _cfg.get("tiquet_rural_data_resolucio")
        _tr_data_res = _tr_data_res_date.isoformat() if _tr_data_res_date else "—"

        if _tr_estat in ("concedit", "pagat"):
            _tr_bg = "var(--success-soft)"
            _tr_border = "var(--success)"
            _tr_icon = "✅"
            _tr_avís = (
                "⚠️ Aquest ajut tributa com a guany patrimonial a IRPF, "
                "no com a rendiment d'activitat. No s'inclou al càlcul del tram d'autònom. "
                "Consulta amb gestor per al model adequat de declaració."
            )
        elif _tr_estat == "denegat":
            _tr_bg = "var(--bg-subtle)"
            _tr_border = "var(--border)"
            _tr_icon = "❌"
            _tr_avís = "Pots tornar a presentar-te a la propera convocatòria."
        else:
            _tr_bg = "var(--bg-subtle)"
            _tr_border = "var(--border)"
            _tr_icon = "🕐"
            _tr_avís = f"Resolució prevista: {_tr_data_res}"

        st.markdown(
            f'<div class="custom-card" style="background:{_tr_bg};border-color:{_tr_border};margin-top:8px;">'
            f'<div class="card-title">Tiquet Rural</div>'
            f'<p style="margin:0 0 8px;font-weight:600;">{_tr_icon} Estat: {_tr_estat.replace("_"," ").capitalize()}'
            + (f' · {_tr_quantia:,.0f} €' if _tr_quantia > 0 else '') +
            f'</p><p style="margin:0;font-size:0.9rem;color:var(--text-secondary);">{_tr_avís}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── CONFIGURACIÓ EDITABLE ──────────────────────────────────────────
    with st.expander("⚙️ Configuració d'autònom"):
        with st.form("form_config_autonom"):
            _f_alta_prev = st.date_input(
                "Data d'alta prevista",
                value=_cfg.get("data_alta_prevista") or date(2026, 9, 1),
            )
            _f_donat = st.checkbox(
                "Ja estic donat d'alta", value=not _preview
            )
            _f_alta_real = st.date_input(
                "Data d'alta real",
                value=_cfg.get("data_alta_real") or date.today(),
                disabled=not _f_donat,
            )
            _f_prorrogada = st.checkbox("Tarifa plana prorrogada (2n any)", value=_prorrogada)
            _f_iva = st.checkbox("IVA per defecte als ingressos", value=_iva_def)
            _f_factures = st.number_input("Factures aproximades/mes", min_value=1, max_value=10,
                                          value=_factures_mes)
            _f_retencio = st.selectbox(
                "Retenció IRPF habitual",
                options=["0%", "7%", "15%"],
                index=["0%", "7%", "15%"].index(f"{int(_retencio*100)}%") if f"{int(_retencio*100)}%" in ["0%","7%","15%"] else 2,
            )
            _f_tr_estat = st.selectbox(
                "Tiquet Rural — estat",
                options=["no_aplica", "sollicitat", "concedit", "pagat", "denegat"],
                index=["no_aplica","sollicitat","concedit","pagat","denegat"].index(_tr_estat)
                      if _tr_estat in ["no_aplica","sollicitat","concedit","pagat","denegat"] else 0,
            )
            _f_tr_quantia = st.number_input("Tiquet Rural — quantia (€)", min_value=0.0,
                                            value=_cfg.get("tiquet_rural_quantia", 0.0) or 0.0,
                                            step=500.0)
            _tr_data_val = _cfg.get("tiquet_rural_data_resolucio") or date.today()
            _f_tr_data = st.date_input("Tiquet Rural — data resolució prevista", value=_tr_data_val)

            if st.form_submit_button("💾 Desar configuració", type="primary"):
                _nova_config = {
                    "data_alta_prevista": _f_alta_prev.isoformat(),
                    "data_alta_real": _f_alta_real.isoformat() if _f_donat else "",
                    "tarifa_plana_prorrogada": "TRUE" if _f_prorrogada else "FALSE",
                    "iva_per_defecte": "TRUE" if _f_iva else "FALSE",
                    "factures_aprox_mes": str(int(_f_factures)),
                    "retencio_irpf_pct": str(int(_f_retencio.replace("%","")) / 100),
                    "tiquet_rural_estat": _f_tr_estat,
                    "tiquet_rural_quantia": str(int(_f_tr_quantia)),
                    "tiquet_rural_data_resolucio": _f_tr_data.isoformat(),
                }
                guardar_config(conn, _nova_config)
                st.success("✅ Configuració desada.")
                st.rerun()

# --- TAB 2: EDITAR DADES ---
with t2:
    if not df.empty:
        df_per_editar = df_filtrat.sort_values(by='data', ascending=False)
        df_editat = st.data_editor(df_per_editar, num_rows="dynamic", width="stretch", key="main_editor")
        if st.button("💾 Guardar Canvis Taula"):
            mask_fora = (df['data'] < inici) | (df['data'] > fi)
            df_final = pd.concat([df.loc[mask_fora], df_editat], ignore_index=True)
            guardar_dades(df_final)
            st.success("Dades guardades!")
            st.rerun()
    else:
        st.info("📭 Cap moviment per editar. Canvia el filtre o afegeix dades primer.")