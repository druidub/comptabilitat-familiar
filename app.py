import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import uuid

# --- 1. CONFIGURACIÓ DE PÀGINA I ESTIL ---
st.set_page_config(page_title="Economia Jose Manuel i Alba", page_icon="🏠", layout="wide")

# Estils CSS per al look "Premium"
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric {
        background-color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
    }
    .advisor-box {
        background-color: #1e1b4b;
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        border-left: 6px solid #6366f1;
        margin-bottom: 2rem;
    }
    .family-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
    }
    .stExpander {
        border: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        background: white !important;
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 🔒 SISTEMA DE SEGURETAT ---
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
# Utilitzem el model gemini-2.0-flash per a una anàlisi ràpida i moderna
model = genai.GenerativeModel('gemini-2.0-flash-exp') 
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dades():
    df = conn.read(ttl=0)
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
    if df.empty:
        df = pd.DataFrame(columns=columnes_base)
    for col in columnes_base:
        if col not in df.columns: df[col] = ""
    
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['quantitat'] = pd.to_numeric(df['quantitat'], errors='coerce')
    df = df.dropna(subset=['data', 'quantitat'])
    df['data'] = df['data'].dt.date
    return df

def carregar_recurrents():
    try:
        df_rec = conn.read(worksheet="Recurrents", ttl=0)
        return df_rec if not df_rec.empty else pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia"])
    except:
        return pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia"])

def guardar_dades(df_nou):
    conn.update(data=df_nou)

# --- 3. LÒGICA DE RECURRENTS PENDENTS ---
def comprovar_recurrents_pendents(df_actual, df_config):
    if df_config.empty: return []
    avui = date.today()
    mes_actual = avui.month
    any_actual = avui.year
    moviments_a_afegir = []
    
    for rec in df_config.to_dict('records'):
        try:
            dia_fix = int(rec['dia'])
            dia_real = min(dia_fix, 28) if mes_actual == 2 else min(dia_fix, 30)
            data_tocaria = date(any_actual, mes_actual, dia_real)
            
            if avui >= data_tocaria:
                concepte_rec = str(rec['concepte'])
                duplicat = df_actual[
                    (df_actual['data'].apply(lambda x: x.month) == mes_actual) & 
                    (df_actual['concepte'] == concepte_rec)
                ]
                saltat = df_actual[
                    (df_actual['data'].apply(lambda x: x.month) == mes_actual) & 
                    (df_actual['concepte'] == f"SALTAT: {concepte_rec}")
                ]
                
                if duplicat.empty and saltat.empty:
                    moviments_a_afegir.append({
                        "data": data_tocaria, 
                        "concepte": concepte_rec, 
                        "establiment": "Automàtic",
                        "quantitat": rec['quantitat'], 
                        "categoria": rec['categoria'], 
                        "tipus": rec['tipus'],
                        "es_periodic": True, 
                        "Acció": "Afegir"
                    })
        except: continue
    return moviments_a_afegir

# Càrrega de dades
df = carregar_dades()
df_rec_config = carregar_recurrents()

# --- 4. SIDEBAR (FILTRES I ALERTES) ---
with st.sidebar:
    st.markdown("### 🏠 Menú de la Llar")
    st.caption(f"Avui: {date.today().strftime('%d/%m/%Y')}")
    
    # ALERTES RECURRENTS
    pendents = comprovar_recurrents_pendents(df, df_rec_config)
    if pendents:
        st.warning(f"🔔 {len(pendents)} Pendents")
        with st.expander("Gestionar"):
            df_p = pd.DataFrame(pendents)
            editat_p = st.data_editor(df_p, column_config={"Acció": st.column_config.SelectboxColumn("Acció", options=["Afegir", "Saltar", "Pendent"]), "data": None, "establiment": None, "categoria": None, "tipus": None, "es_periodic": None}, hide_index=True)
            if st.button("🚀 Processar"):
                noves_files = []
                for _, row in editat_p.iterrows():
                    if row['Acció'] == "Afegir":
                        item = row.drop('Acció').to_dict()
                        item['id_grup'] = f"AUTO-{uuid.uuid4().hex[:6]}"
                        noves_files.append(item)
                if noves_files:
                    df_final = pd.concat([df, pd.DataFrame(noves_files)], ignore_index=True)
                    guardar_dades(df_final)
                    st.success("Actualitzat!")
                    st.rerun()

    st.divider()
    
    # SELECTOR DE PERÍODE (RECUPERAT)
    st.subheader("📅 Filtre de Període")
    opcio_data = st.selectbox("Selecciona:", ["Aquest Mes", "Mes Anterior", "Últims 30 dies", "Tot l'any", "Personalitzat"])
    avui = date.today()
    if opcio_data == "Aquest Mes":
        inici, fi = avui.replace(day=1), avui
    elif opcio_data == "Mes Anterior":
        fi = avui.replace(day=1) - timedelta(days=1)
        inici = fi.replace(day=1)
    elif opcio_data == "Tot l'any":
        inici, fi = avui.replace(month=1, day=1), avui
    elif opcio_data == "Personalitzat":
        inici = st.date_input("Inici", avui - timedelta(days=30))
        fi = st.date_input("Fi", avui)
    else: 
        inici, fi = avui - timedelta(days=30), avui

    st.divider()
    if st.button("🔒 Tancar"):
        st.session_state["password_correct"] = False
        st.rerun()

# Filtrar dades
mask = (df['data'] >= inici) & (df['data'] <= fi)
df_filtrat = df.loc[mask]

# --- 5. INTERFÍCIE PRINCIPAL ---

st.markdown(f"""
    <div class="family-header">
        <h1>Gestió Econòmica Familiar</h1>
        <p>Projecte de <b>Jose Manuel i Alba</b> | Període: {inici.strftime('%d/%m')} al {fi.strftime('%d/%m/%Y')}</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Balanç", "➕ Registre", "🤖 Assessor IA", "⚙️ Config"])

with tab1:
    if not df_filtrat.empty:
        ing = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
        des = abs(df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum())
        bal = ing - des
        ratio = (des / ing * 100) if ing > 0 else 0
    else:
        ing, des, bal, ratio = 0.0, 0.0, 0.0, 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingressos", f"{ing:,.2f} €")
    c2.metric("Despeses", f"{des:,.2f} €", delta_color="inverse")
    c3.metric("Balanç", f"{bal:,.2f} €")
    c4.metric("Salut Deute", f"{ratio:.1f} %")

    st.divider()
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.markdown("**Evolució Saldo**")
        if not df_filtrat.empty:
            df_ev = df_filtrat.groupby('data')['quantitat'].sum().cumsum().reset_index()
            fig = px.line(df_ev, x='data', y='quantitat', template="plotly_white")
            fig.update_traces(line_color='#4f46e5', line_width=4)
            st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.markdown("**Despeses**")
        if not df_filtrat.empty and des > 0:
            df_p = df_filtrat[df_filtrat['quantitat'] < 0].copy()
            df_p['quantitat'] = df_p['quantitat'].abs()
            st.plotly_chart(px.pie(df_p, values='quantitat', names='categoria', hole=0.5), use_container_width=True)

    # TAULA D'EDICIÓ
    st.divider()
    st.subheader("✏️ Edició de Moviments")
    df_ed = st.data_editor(df_filtrat.sort_values(by='data', ascending=False), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Guardar Canvis"):
        mask_fora = (df['data'] < inici) | (df['data'] > fi)
        df_final = pd.concat([df.loc[mask_fora], df_ed], ignore_index=True)
        guardar_dades(df_final)
        st.success("Guardat!")
        st.rerun()

with tab2:
    st.subheader("Nou Moviment")
    m_text = st.text_area("Explica el moviment per text o xat:", height=100)
    if st.button("Processar Moviment"): 
        st.info("La IA està analitzant...")

with tab3:
    st.subheader("🕵️ Assessor Jose & Alba")
    if st.button("Generar Informe"):
        with st.spinner("Analitzant números..."):
            resum = f"Balanç: {bal}€. Ingressos: {ing}€. Despeses: {des}€."
            prompt = f"Ets l'assessor familiar de Jose (atur) i Alba. Deute 165€. Reclamació 1800€ BBVA. Analitza: {resum}. Respon en 3 punts, positiu."
            try:
                r = model.generate_content(prompt)
                st.markdown(f'<div class="advisor-box"><h3>🤖 Consell IA</h3>{r.text}</div>', unsafe_allow_html=True)
            except:
                st.error("Error connectant amb la IA.")
    
    st.divider()
    st.info(f"**Provisió Renda:** Reservar uns **{ing * 0.15:,.2f} €** d'aquest mes.")

with tab4:
    st.subheader("Configuració")
    df_rec_ed = st.data_editor(df_rec_config, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Actualitzar"):
        conn.update(worksheet="Recurrents", data=df_rec_ed)
        st.success("Actualitzat!")