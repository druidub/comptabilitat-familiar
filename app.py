import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image
import uuid 

# --- 1. CONFIGURACIÓ DE PÀGINA I ESTILS PREMIUM ---
st.set_page_config(page_title="Família Finances v2.1", page_icon="🏦", layout="wide")

# CSS CUSTOM PER A LOOK "BANCA MODERNA"
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
# MODEL POTENT (3-Flash)
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# --- FUNCIONS DE DADES ---
def carregar_dades():
    df = conn.read(ttl=0)
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
    
    if df.empty:
        df = pd.DataFrame(columns=columnes_base)
    
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
    
    df['es_periodic'] = df['es_periodic'].astype(str).map({'TRUE': True, 'True': True, 'true': True, '1': True, '1.0': True}).fillna(False)
    df['es_periodic'] = df['es_periodic'].astype(bool)

    return df

def carregar_recurrents():
    try:
        df_rec = conn.read(worksheet="Recurrents", ttl=0)
        columnes_req = ["concepte", "quantitat", "categoria", "tipus", "dia", "frequencia"]
        if df_rec.empty:
             return pd.DataFrame(columns=columnes_req)
        
        if "frequencia" not in df_rec.columns:
            df_rec["frequencia"] = "Mensual"
            
        return df_rec
    except Exception:
        st.error("⚠️ Error llegint 'Recurrents'. Revisa que la pestanya existeixi.")
        return pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia", "frequencia"])

def guardar_dades(df_nou):
    conn.update(data=df_nou)

def guardar_recurrents(df_rec_nou):
    conn.update(worksheet="Recurrents", data=df_rec_nou)

# --- LÒGICA AUTOMÀTICA ---
def comprovar_recurrents_pendents(df_actual, df_config):
    if df_config.empty:
        return []

    avui = date.today()
    mes_actual = avui.month
    any_actual = avui.year
    
    moviments_a_afegir = []
    recurrents_list = df_config.to_dict('records')

    for rec in recurrents_list:
        try:
            freq = rec.get('frequencia', 'Mensual')
            toca_aquest_mes = False
            
            if freq == "Mensual":
                toca_aquest_mes = True
            elif freq == "Trimestral":
                if mes_actual in [1, 4, 7, 10]:
                    toca_aquest_mes = True
            elif freq == "Anual":
                if mes_actual == 1:
                    toca_aquest_mes = True
            
            if not toca_aquest_mes:
                continue

            dia_fix = int(rec['dia'])
            try:
                data_tocaria = date(any_actual, mes_actual, dia_fix)
            except ValueError:
                data_tocaria = date(any_actual, mes_actual, 1) + timedelta(days=32)
                data_tocaria = data_tocaria.replace(day=1) - timedelta(days=1)
            
            if avui >= data_tocaria:
                duplicat = df_actual[
                    (df_actual['data'].apply(lambda x: x.month) == mes_actual) &
                    (df_actual['data'].apply(lambda x: x.year) == any_actual) &
                    (df_actual['concepte'] == rec['concepte']) &
                    (abs(df_actual['quantitat'] - rec['quantitat']) < 0.01)
                ]
                saltat = df_actual[
                    (df_actual['data'].apply(lambda x: x.month) == mes_actual) &
                    (df_actual['data'].apply(lambda x: x.year) == any_actual) &
                    (df_actual['concepte'] == f"SALTAT: {rec['concepte']}")
                ]
                
                if duplicat.empty and saltat.empty:
                    moviments_a_afegir.append({
                        "data": data_tocaria,
                        "concepte": rec['concepte'],
                        "establiment": "Recurrent Automàtic",
                        "quantitat": rec['quantitat'],
                        "categoria": rec['categoria'],
                        "tipus": rec['tipus'],
                        "es_periodic": True,
                        "Acció": "Afegir"
                    })
        except Exception:
            continue
            
    return moviments_a_afegir

df = carregar_dades()
df_recurrents_config = carregar_recurrents()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🏦 Família Finances")
    st.caption("v2.1 - Jose & Alba Edition")
    st.divider()
    
    # 1. Avisos
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
                        del row['Acció']
                        row['id_grup'] = "AUTO_" + str(uuid.uuid4())[:8]
                        noves.append(row)
                    elif row['Acció'] == "Saltar (Ignorar)":
                        noves.append({
                            "data": row['data'], "concepte": f"SALTAT: {row['concepte']}", "establiment": "Sistema", "quantitat": 0.0, "categoria": row['categoria'], "tipus": row['tipus'], "es_periodic": False, "id_grup": "SKIP_" + str(uuid.uuid4())[:8]
                        })
                
                if noves:
                    df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
                    guardar_dades(df_final)
                    st.rerun()
    else:
        st.success("✅ Tot al dia")

    st.divider()
    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()

    # 2. FILTRE DE DATES (ARREGLAT!)
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
    else: # Personalitzat
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

ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
saldo = df_filtrat['quantitat'].sum()

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
        df_desp['valor'] = df_desp['quantitat'].abs()
        fig = px.pie(df_desp, values='valor', names='categoria', title="On van els diners?", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
        
    elif vista_grafic == "Detall Ingressos":
        df_ing = df_filtrat[df_filtrat['quantitat'] > 0]
        fig = px.bar(df_ing, x='categoria', y='quantitat', color='concepte', title="Fonts d'Ingrés")
        st.plotly_chart(fig, use_container_width=True)

# =================================================
# 2. PESTANYES
# =================================================
t1, t2, t3, t4 = st.tabs(["➕ Afegir Moviment", "🧠 Assessoria IA", "⚙️ Configurar Recurrents", "✏️ Editar Dades"])

# --- TAB 1: INPUT ---
with t1:
    prompt_comu = f"AVUI ÉS: {date.today()}. Analitza text/foto. Retorna LLISTA JSON: 'data' (YYYY-MM-DD), 'concepte', 'establiment', 'quantitat' (Negatiu=Despesa), 'categoria', 'tipus', 'es_periodic' (bool). Si usuari diu 'Ahir', calcula data."
    col_txt, col_foto = st.columns(2)
    with col_txt:
        st.text_area("Escriu aquí (Ex: Ahir 45€ Mercadona)", key="input_text_key", height=100)
        if st.button("Enviar Text"):
            txt_val = st.session_state.input_text_key
            if txt_val:
                try:
                    res = model.generate_content([prompt_comu, txt_val])
                    txt = res.text.replace("```json", "").replace("```", "").strip()
                    dades = json.loads(txt)
                    if isinstance(dades, dict): dades = [dades]
                    noves = []
                    for item in dades:
                        data_f = item.get('data') or date.today()
                        noves.append({
                            "data": data_f, "concepte": item.get('concepte', 'Varies'), "establiment": item.get('establiment', ''), "quantitat": item.get('quantitat', 0), "categoria": item.get('categoria', 'Altres'), "tipus": item.get('tipus', 'Despesa'), "es_periodic": item.get('es_periodic', False), "id_grup": "TXT_" + str(uuid.uuid4())[:8]
                        })
                    df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
                    guardar_dades(df_final)
                    st.session_state.input_text_key = ""
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    with col_foto:
        im = st.file_uploader("Pujar Tiquet", type=['jpg','png'])
        if st.button("Processar Foto") and im:
            with st.spinner("Llegint tiquet..."):
                try:
                    img_p = Image.open(im)
                    res = model.generate_content([prompt_comu, "Extreu productes:", img_p])
                    txt = res.text.replace("```json", "").replace("```", "").strip()
                    dades = json.loads(txt)
                    if isinstance(dades, dict): dades = [dades]
                    noves = []
                    grup = "IMG_" + str(uuid.uuid4())[:8]
                    for item in dades:
                        noves.append({
                            "data": item.get('data') or date.today(), "concepte": item.get('concepte'), "establiment": item.get('establiment'), "quantitat": item.get('quantitat'), "categoria": item.get('categoria'), "tipus": item.get('tipus'), "es_periodic": False, "id_grup": grup
                        })
                    df_final = pd.concat([df, pd.DataFrame(noves)], ignore_index=True)
                    guardar_dades(df_final)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: ASSESSORIA ESTRATÈGICA ---
with t2:
    st.subheader("🧠 L'Assessor de la Família")
    st.info("Aquest anàlisi té en compte: Jose (Atur), Ingrés Lloguer (850€), Deute (165€) i Reclamació BBVA.")
    if st.button("Generar Anàlisi del Mes"):
        with st.spinner("Consultant l'estratègia amb Gemini..."):
            resum_cat = df_filtrat.groupby('categoria')['quantitat'].sum().to_string()
            total_ing = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
            total_desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
            prompt_advisor = f"""
            Actua com un assessor financer expert per a una família (Jose Manuel i Alba).
            CONTEXT FAMILIAR:
            - Jose Manuel està a l'atur.
            - Ingrés extra lloguer 850€/mes.
            - Deute pendent 165€.
            - Esperant reclamació BBVA 1.800€.
            DADES MES: Ingressos {total_ing}€, Despeses {total_desp}€.
            Desglossament: {resum_cat}
            TASCA: 3 consells breus, estratègics i empàtics.
            """
            try:
                res_adv = model.generate_content(prompt_advisor)
                st.markdown(res_adv.text)
            except Exception as e:
                st.error(f"Error connectant amb l'assessor: {e}")

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
            "frequencia": st.column_config.SelectboxColumn("Freqüència", options=["Mensual", "Trimestral", "Anual"], required=True, default="Mensual")
        },
        key="editor_recurrents"
    )
    if st.button("💾 Guardar Configuració"):
        guardar_recurrents(df_config_editat)
        st.success("Configuració actualitzada!")
        st.rerun()

# --- TAB 4: EDITAR DADES ---
with t4:
    df_per_editar = df_filtrat.sort_values(by='data', ascending=False)
    df_editat = st.data_editor(df_per_editar, num_rows="dynamic", use_container_width=True, key="main_editor")
    if st.button("💾 Guardar Canvis Taula"):
        mask_fora = (df['data'] < inici) | (df['data'] > fi)
        df_final = pd.concat([df.loc[mask_fora], df_editat], ignore_index=True)
        guardar_dades(df_final)
        st.success("Dades guardades!")
        st.rerun()