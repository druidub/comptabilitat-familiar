import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import time
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image
import uuid

APP_VERSION = "v2.8"
GEMINI_MODEL = "gemini-2.5-flash"
GSHEETS_TTL = 60
MAX_IMG_BYTES = 5 * 1024 * 1024

# --- 1. CONFIGURACIÓ DE PÀGINA I ESTILS PREMIUM ---
st.set_page_config(page_title=f"Família Finances {APP_VERSION}", page_icon="🏦", layout="wide")

# CSS CUSTOM
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #333;
    }
    div[data-testid="stMetricLabel"] {
        color: #666;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #1f1f1f;
        font-weight: 700;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #555;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f6;
        color: #000;
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
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

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
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
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
        res = amb_reintents(model.generate_content, [prompt_comu, text_val])
        dades = parsejar_json_ia(res.text)

        noves = []
        msg_resum = ""
        grup = "TXT_" + str(uuid.uuid4())[:8]

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

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🏦 Família Finances")
    st.caption(f"{APP_VERSION} - Jose & Alba Edition")
    st.divider()
    
    # 1. Avisos Recurrents
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
                        # SOLUCIÓ: Convertir la fila de Pandas a un diccionari net
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

    # 2. ÚLTIM MOVIMENT
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

    # 3. FILTRES
    st.subheader("📅 Filtres")
    opcio_data = st.selectbox("Període", ["Aquest Mes", "Mes Anterior", "Tot l'any", "Personalitzat"])
    avui = date.today()
    
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

# =================================================
# 1. DASHBOARD PREMIUM
# =================================================

ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum() if not df_filtrat.empty else 0.0
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum() if not df_filtrat.empty else 0.0
saldo = df_filtrat['quantitat'].sum() if not df_filtrat.empty else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("🟢 Ingressos", f"{ingr:.2f} €", delta="Mes en curs")
col2.metric("🔴 Despeses", f"{desp:.2f} €", delta_color="inverse")
col3.metric("💰 Saldo Disponible", f"{saldo:.2f} €")

st.markdown("<br>", unsafe_allow_html=True)
vista_grafic = st.radio("Visualització:", ["Evolució Saldo", "Despeses per Categoria", "Detall Ingressos"], horizontal=True)

if not df_filtrat.empty:
    if vista_grafic == "Evolució Saldo":
        ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
        ev['saldo_acumulat'] = ev['quantitat'].cumsum()
        fig = px.bar(ev, x='data', y='quantitat', color='quantitat', title="Flux Diari", color_continuous_scale=px.colors.diverging.RdYlGn)
        st.plotly_chart(fig, use_container_width=True)
        
    elif vista_grafic == "Despeses per Categoria":
        df_desp = df_filtrat[df_filtrat['quantitat'] < 0].copy()
        if not df_desp.empty:
            df_desp['valor'] = df_desp['quantitat'].abs()
            fig = px.pie(df_desp, values='valor', names='categoria', title="On van els diners?", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hi ha despeses per mostrar en aquest període.")
        
    elif vista_grafic == "Detall Ingressos":
        df_ing = df_filtrat[df_filtrat['quantitat'] > 0]
        if not df_ing.empty:
            fig = px.bar(df_ing, x='categoria', y='quantitat', color='concepte', title="Fonts d'Ingrés")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hi ha ingressos per mostrar en aquest període.")

# =================================================
# 2. PESTANYES
# =================================================
t1, t2, t3, t4 = st.tabs(["➕ Afegir Moviment", "🧠 Assessoria IA", "⚙️ Configurar Recurrents", "✏️ Editar Dades"])

# --- TAB 1: INPUT ---
with t1:
    col_txt, col_foto = st.columns(2)
    with col_txt:
        st.text_area("Escriu aquí (Ex: Ahir 45€ Mercadona)", key="input_text_key", height=100)
        st.button("Enviar Text", on_click=processar_text_callback)

    with col_foto:
        im = st.file_uploader("Pujar Tiquet", type=['jpg', 'jpeg', 'png'])
        prompt_foto = (
            f"AVUI ÉS: {date.today()}. Analitza foto. Retorna LLISTA JSON: "
            "'data', 'concepte', 'establiment', 'quantitat', 'categoria', "
            "'tipus' (Despesa/Ingrés), 'es_periodic' (bool)."
        )

        if st.button("Processar Foto") and im:
            if im.size > MAX_IMG_BYTES:
                st.error(f"La imatge és massa gran ({im.size/1024/1024:.1f} MB). Màx {MAX_IMG_BYTES//1024//1024} MB.")
            else:
                with st.spinner("Llegint tiquet..."):
                    try:
                        img_p = Image.open(im)
                        res = amb_reintents(model.generate_content, [prompt_foto, "Extreu productes:", img_p])
                        dades = parsejar_json_ia(res.text)

                        noves = []
                        msg_resum = ""
                        grup = "IMG_" + str(uuid.uuid4())[:8]
                        for item in dades:
                            t_prov = item.get('tipus', 'Despesa')
                            if str(t_prov).strip().lower() not in PARAULES_INGRES:
                                t_prov = "Despesa"

                            quant_final = corregir_signe(item.get('quantitat', 0), t_prov)

                            noves.append({
                                "data": item.get('data') or date.today(),
                                "concepte": item.get('concepte') or "Tiquet",
                                "establiment": item.get('establiment') or "",
                                "quantitat": quant_final,
                                "categoria": item.get('categoria') or "Altres",
                                "tipus": t_prov,
                                "es_periodic": False,
                                "id_grup": grup,
                            })
                            msg_resum += f"- {item.get('concepte')}: {quant_final}€\n"

                        df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
                        guardar_dades(df_final)

                        st.session_state["ultim_moviment"] = msg_resum
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("La IA no ha retornat un JSON vàlid. Prova amb una foto més clara.")
                    except Exception as e:
                        st.error(f"Error processant la foto: {str(e)[:200]}")

# --- TAB 2: ASSESSORIA ESTRATÈGICA ---
with t2:
    st.subheader("🧠 L'Assessor de la Família")
    st.info("Aquest anàlisi té en compte: Jose (Atur), Ingrés Lloguer (850€), Deute (165€) i Reclamació BBVA.")
    if st.button("Generar Anàlisi del Mes"):
        with st.spinner("Consultant l'estratègia amb Gemini..."):
            resum_cat = df_filtrat.groupby('categoria')['quantitat'].sum().to_string() if not df_filtrat.empty else "Sense dades"
            prompt_advisor = f"""
            Actua com un assessor financer expert per a una família (Jose Manuel i Alba).
            CONTEXT FAMILIAR:
            - Jose Manuel està a l'atur tot i que té ingressos recurrents per treballs d'edició web.
            - Ingrés extra lloguer 550€/mes.
            - Nómina de l'Alba de 1.300€ aprox.
            - Esperant reclamació BBVA 1.800€.
            DADES MES: Ingressos {ingr}€, Despeses {desp}€.
            Desglossament: {resum_cat}
            TASCA: 3 consells breus, estratègics i empàtics.
            """
            try:
                res_adv = amb_reintents(model.generate_content, prompt_advisor)
                st.markdown(res_adv.text)
            except Exception as e:
                st.error(f"Error connectant amb l'assessor: {str(e)[:200]}")

# --- TAB 3: CONFIGURAR RECURRENTS ---
with t3:
    st.write("Configura els pagaments fixos. Ara pots triar la freqüència.")
    df_config_editat = st.data_editor(
        df_recurrents_config,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "concepte": st.column_config.TextColumn("Concepte", required=True),
            "quantitat": st.column_config.NumberColumn("€", required=True, format="%.2f €"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Llar", "Subscripcions", "Nòmina", "Deute", "Lloguer_Ingrés"], required=True),
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

# --- TAB 4: EDITAR DADES ---
with t4:
    if not df.empty:
        df_per_editar = df_filtrat.sort_values(by='data', ascending=False)
        df_editat = st.data_editor(df_per_editar, num_rows="dynamic", use_container_width=True, key="main_editor")
        if st.button("💾 Guardar Canvis Taula"):
            mask_fora = (df['data'] < inici) | (df['data'] > fi)
            df_final = pd.concat([df.loc[mask_fora], df_editat], ignore_index=True)
            guardar_dades(df_final)
            st.success("Dades guardades!")
            st.rerun()
    else:
        st.info("No hi ha dades per editar.")