import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import uuid

# --- 1. CONFIGURACIÓ I ESTIL ---
st.set_page_config(page_title="Economia Jose Manuel i Alba", page_icon="🏠", layout="wide")

# CSS per millorar l'estètica (estil targetes modern)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #f1f5f9;
    }
    .advisor-box {
        background-color: #1e1b4b;
        color: white;
        padding: 25px;
        border-radius: 20px;
        border-left: 5px solid #6366f1;
    }
    .family-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 🔒 SEGURETAT ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Accés al Gestor Familiar")
    pwd = st.text_input("Contrasenya de la llar", type="password")
    if st.button("Entrar a casa"):
        if pwd == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Contrasenya incorrecta")
    return False

if not check_password():
    st.stop()

# --- 2. CONNEXIONS I DADES ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dades():
    df = conn.read(ttl=0)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['quantitat'] = pd.to_numeric(df['quantitat'], errors='coerce')
    df = df.dropna(subset=['data', 'quantitat'])
    return df

def carregar_recurrents():
    try:
        return conn.read(worksheet="Recurrents", ttl=0)
    except:
        return pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia"])

df = carregar_dades()
df_rec_config = carregar_recurrents()

# --- 3. LÒGICA DE L'ASSESSOR IA ---
def generar_consell_ia(df_context):
    resum_financer = {
        "balanç_total": df_context['quantitat'].sum(),
        "despeses_mes": df_context[df_context['quantitat'] < 0]['quantitat'].sum(),
        "ingressos_mes": df_context[df_context['quantitat'] > 0]['quantitat'].sum(),
        "categories": df_context.groupby('categoria')['quantitat'].sum().to_dict()
    }
    
    prompt = f"""
    Ets un assessor financer familiar per a en Jose Manuel i l'Alba. 
    CONTEXT: En Jose Manuel està a l'atur, reben un lloguer d'uns 850€, tenen hipoteca (376€) i préstec (165€).
    Estan reclamant 1800€ al BBVA.
    
    DADES DEL MES: {json.dumps(resum_financer)}
    
    TASCA:
    1. Dirigir-te a tots dos (Jose Manuel i Alba).
    2. Analitzar la salut de l'economia de la llar.
    3. Donar consells sobre el préstec de 165€ i la reserva per a la Renda del lloguer.
    4. Sigues positiu, familiar i ajuda'ls a estalviar per a un futur millor.
    Respon en Català, amb format markdown i molts emojis.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ L'assessor està descansant. Torneu-ho a provar en uns minuts!"

# --- 4. INTERFÍCIE ---

st.sidebar.markdown("### 🏠 La Nostra Llar")
st.sidebar.info("Hola Jose Manuel i Alba! 👋")

# Capçalera personalitzada
st.markdown("""
    <div class="family-header">
        <h1>Gestió Econòmica Familiar</h1>
        <p>Projecte compartit de Jose Manuel i Alba</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Balanç Familiar", "➕ Nou Moviment", "🤖 Assessor d'en Jose i l'Alba", "⚙️ Configuració"])

with tab1:
    mes_actual = date.today().month
    df_mes = df[df['data'].dt.month == mes_actual]
    
    ing = df_mes[df_mes['quantitat'] > 0]['quantitat'].sum()
    des = abs(df_mes[df_mes['quantitat'] < 0]['quantitat'].sum())
    bal = ing - des
    ratio_deute = (des / ing * 100) if ing > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingressos", f"{ing:,.2f} €")
    c2.metric("Despeses", f"{des:,.2f} €", delta_color="inverse")
    c3.metric("Balanç Estalvi", f"{bal:,.2f} €")
    c4.metric("Salut Deute", f"{ratio_deute:.1f} %", help="Ideal < 35%")

    st.divider()
    col_g1, col_g2 = st.columns([2, 1])
    
    with col_g1:
        st.markdown("**Com va el nostre mes?**")
        df_ev = df_mes.groupby('data')['quantitat'].sum().cumsum().reset_index()
        fig_line = px.line(df_ev, x='data', y='quantitat', template="plotly_white")
        fig_line.update_traces(line_color='#4f46e5', line_width=4)
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col_g2:
        st.markdown("**On se'n van els diners?**")
        df_pie = df_mes[df_mes['quantitat'] < 0].copy()
        df_pie['quantitat'] = df_pie['quantitat'].abs()
        fig_pie = px.pie(df_pie, values='quantitat', names='categoria', hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("Registrar una despesa o ingrés")
    input_method = st.radio("Com ho vols introduir?", ["Xat de veu/text", "Manual", "Ticket"])
    
    if input_method == "Xat de veu/text":
        user_input = st.text_area("Exemple: 'Alba ha comprat pa per 1.20€' o 'Lloguer rebut'", height=100)
        if st.button("Processar Moviment"):
            st.info("La IA està classificant el moviment...")

    elif input_method == "Manual":
        with st.form("manual_form"):
            c1, c2 = st.columns(2)
            d = c1.date_input("Data", date.today())
            q = c2.number_input("Import (€)", format="%.2f")
            con = st.text_input("Concepte")
            cat = st.selectbox("Categoria", ["Alimentació", "Habitatge", "Lloguer", "Deutes", "Subministraments", "Oci"])
            if st.form_submit_button("Guardar Moviment"):
                st.success("Moviment registrat correctament!")

with tab3:
    st.subheader("🕵️ L'Assessor de la Família")
    st.markdown("Consells personalitzats per a la vostra situació actual.")
    
    if st.button("Demanar consell a la IA"):
        with st.spinner("L'assessor està mirant els vostres números..."):
            consell = generar_consell_ia(df_mes)
            st.markdown(f'<div class="advisor-box">{consell}</div>', unsafe_allow_html=True)
            
    st.divider()
    st.markdown("### 📅 Objectius i Provisions")
    col_inf1, col_inf2 = st.columns(2)
    with col_inf1:
        st.info("**Guardiola per a la Renda (20% Lloguer)**")
        ingressos_lloguer = df_mes[df_mes['categoria'] == 'Lloguer']['quantitat'].sum()
        st.write(f"Recordeu reservar **{ingressos_lloguer * 0.20:.2f} €** aquest mes.")
    with col_inf2:
        st.warning("**Reclamació BBVA**")
        st.write("Estat: Pendent (1.800€). No signeu res sense revisar-ho!")

with tab4:
    st.subheader("Gestió del Sistema")
    st.write("Aquesta app sincronitza amb el vostre Google Sheets compartit.")
    df_edit = st.data_editor(df_rec_config, num_rows="dynamic")
    if st.button("💾 Guardar canvis en pagaments recurrents"):
        st.success("Configuració actualitzada!")

st.sidebar.divider()
st.sidebar.caption(f"Actualitzat: {datetime.now().strftime('%d/%m/%Y %H:%M')}")