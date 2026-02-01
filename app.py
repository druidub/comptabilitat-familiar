import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image
import uuid

# --- 1. CONFIGURACIÓ DE PÀGINA I ESTIL ---
st.set_page_config(page_title="Economia Jose Manuel i Alba", page_icon="🏠", layout="wide")

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

# --- 2. CONNEXIONS I CONFIGURACIÓ ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
# Utilitzem el model Flash 2.0 per a millor lectura de tickets
model = genai.GenerativeModel('gemini-2.0-flash-exp') 
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. FUNCIONS DE DADES ---
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

# --- 4. LÒGICA AUTOMÀTICA DE RECURRENTS ---
def comprovar_recurrents_pendents(df_actual, df_config):
    if df_config.empty: return []
    avui = date.today()
    mes_actual, any_actual = avui.month, avui.year
    moviments_a_afegir = []
    
    for rec in df_config.to_dict('records'):
        try:
            dia_fix = int(rec['dia'])
            data_tocaria = date(any_actual, mes_actual, min(dia_fix, 28))
            if avui >= data_tocaria:
                duplicat = df_actual[(df_actual['data'].apply(lambda x: x.month) == mes_actual) & 
                                     (df_actual['concepte'] == rec['concepte'])]
                saltat = df_actual[(df_actual['data'].apply(lambda x: x.month) == mes_actual) & 
                                   (df_actual['concepte'] == f"SALTAT: {rec['concepte']}")]
                if duplicat.empty and saltat.empty:
                    moviments_a_afegir.append({
                        "data": data_tocaria, "concepte": rec['concepte'], "establiment": "Recurrent Automàtic",
                        "quantitat": rec['quantitat'], "categoria": rec['categoria'], "tipus": rec['tipus'],
                        "es_periodic": True, "Acció": "Afegir"
                    })
        except: continue
    return moviments_a_afegir

# Carreguem dades
df = carregar_dades()
df_rec_config = carregar_recurrents()

# --- 5. SIDEBAR (FILTRES I GESTIÓ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6073/6073873.png", width=50)
    st.header("Menú Familiar")
    
    # Gestió de Recurrents (Alertes)
    pendents = comprovar_recurrents_pendents(df, df_rec_config)
    if pendents:
        st.warning(f"🔔 {len(pendents)} Pagaments pendents")
        with st.expander("Processar ara", expanded=True):
            df_p = pd.DataFrame(pendents)
            editat_p = st.data_editor(df_p, column_config={"Acció": st.column_config.SelectboxColumn("Acció", options=["Afegir", "Saltar (Ignorar)", "Pendent"]), "concepte": st.column_config.TextColumn("Què", disabled=True), "quantitat": st.column_config.NumberColumn("€", disabled=True)}, hide_index=True)
            if st.button("🚀 Executar"):
                noves = []
                for _, row in editat_p.iterrows():
                    if row['Acció'] == "Afegir":
                        item = row.drop('Acció').to_dict()
                        item['id_grup'] = "AUTO_" + uuid.uuid4().hex[:6]
                        noves.append(item)
                    elif row['Acció'] == "Saltar (Ignorar)":
                        noves.append({"data": row['data'], "concepte": f"SALTAT: {row['concepte']}", "establiment": "Sistema", "quantitat": 0.0, "categoria": row['categoria'], "tipus": row['tipus'], "es_periodic": False, "id_grup": "SKIP_" + uuid.uuid4().hex[:6]})
                if noves:
                    guardar_dades(pd.concat([df, pd.DataFrame(noves)], ignore_index=True))
                    st.rerun()

    st.divider()
    st.subheader("📅 Filtre de dades")
    opcio_data = st.selectbox("Període", ["Aquest Mes", "Mes Anterior", "Tot l'any", "Personalitzat"])
    avui = date.today()
    if opcio_data == "Aquest Mes": inici, fi = avui.replace(day=1), avui
    elif opcio_data == "Mes Anterior":
        primer = avui.replace(day=1)
        fi = primer - timedelta(days=1)
        inici = fi.replace(day=1)
    elif opcio_data == "Tot l'any": inici, fi = avui.replace(month=1, day=1), avui
    else:
        inici = st.date_input("Inici", avui - timedelta(days=30))
        fi = st.date_input("Fi", avui)

    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()

# Filtrar dades
mask = (df['data'] >= inici) & (df['data'] <= fi)
df_filtrat = df.loc[mask]

# --- 6. INTERFÍCIE PRINCIPAL ---
st.markdown(f"""
    <div class="family-header">
        <h1>Gestió Econòmica Familiar</h1>
        <p>Projecte de <b>Jose Manuel i Alba</b> | Període: {inici.strftime('%d/%m')} - {fi.strftime('%d/%m/%Y')}</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Balanç", "➕ Nou Moviment", "🤖 Assessor IA", "⚙️ Config"])

# --- TAB 1: DASHBOARD ---
with tab1:
    if not df_filtrat.empty:
        ing = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
        des = abs(df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum())
        bal = ing - des
    else: ing, des, bal = 0.0, 0.0, 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingressos", f"{ing:,.2f} €")
    c2.metric("Despeses", f"{des:,.2f} €", delta_color="inverse")
    c3.metric("Estalvi", f"{bal:,.2f} €")

    st.divider()
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        if not df_filtrat.empty:
            df_ev = df_filtrat.groupby('data')['quantitat'].sum().cumsum().reset_index()
            fig = px.line(df_ev, x='data', y='quantitat', title="Evolució Saldo")
            st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        if not df_filtrat.empty and des > 0:
            df_p = df_filtrat[df_filtrat['quantitat'] < 0].copy()
            df_p['quantitat'] = df_p['quantitat'].abs()
            st.plotly_chart(px.pie(df_p, values='quantitat', names='categoria', hole=0.5), use_container_width=True)

    st.subheader("✏️ Editar Moviments")
    df_ed = st.data_editor(df_filtrat.sort_values(by='data', ascending=False), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Guardar Canvis"):
        mask_fora = (df['data'] < inici) | (df['data'] > fi)
        guardar_dades(pd.concat([df.loc[mask_fora], df_ed], ignore_index=True))
        st.success("Guardat!")
        st.rerun()

# --- TAB 2: NOU MOVIMENT (TEXT I FOTO) ---
with tab2:
    prompt_ia = f"AVUI ÉS: {date.today()}. Retorna LLISTA de JSONs: 'data' (YYYY-MM-DD), 'concepte', 'establiment', 'quantitat' (Negatiu=Despesa), 'categoria', 'tipus', 'es_periodic' (bool)."
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📝 Per Text")
        txt_input = st.text_area("Què has gastat?", placeholder="Ahir 25€ al Mercadona...")
        if st.button("Enviar Text"):
            with st.spinner("La IA està llegint..."):
                res = model.generate_content([prompt_ia, txt_input])
                dades = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                if isinstance(dades, dict): dades = [dades]
                noves = pd.DataFrame(dades)
                noves['id_grup'] = uuid.uuid4().hex[:6]
                guardar_dades(pd.concat([carregar_dades(), noves], ignore_index=True))
                st.success("Afegit!")
                st.rerun()

    with col_b:
        st.subheader("📸 Per Ticket")
        file_im = st.file_uploader("Puja foto", type=['jpg','png','jpeg'])
        if st.button("Processar Foto") and file_im:
            with st.spinner("Analitzant ticket..."):
                img = Image.open(file_im)
                res = model.generate_content([prompt_ia, "Extrau dades d'aquest ticket:", img])
                dades = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                if isinstance(dades, dict): dades = [dades]
                noves = pd.DataFrame(dades)
                noves['id_grup'] = uuid.uuid4().hex[:6]
                guardar_dades(pd.concat([carregar_dades(), noves], ignore_index=True))
                st.success("Ticket processat!")
                st.rerun()

# --- TAB 3: ASSESSOR IA ---
with tab3:
    st.subheader("🕵️ L'Assessor de Jose i Alba")
    if st.button("Generar Informe Estratègic"):
        with st.spinner("Analitzant números..."):
            context = f"Balanç: {bal}€. Deute: 165€. Atur Jose. Reclamació BBVA: 1800€."
            r = model.generate_content(f"Ets assessor familiar de Jose i Alba. Analitza: {context}. Sigues breu i positiu.")
            st.markdown(f'<div class="advisor-box">{r.text}</div>', unsafe_allow_html=True)

# --- TAB 4: CONFIGURACIÓ RECURRENTS ---
with tab4:
    st.subheader("⚙️ Pagaments Fixos (Recurrents)")
    df_rec_ed = st.data_editor(df_rec_config, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Actualitzar Recurrents"):
        conn.update(worksheet="Recurrents", data=df_rec_ed)
        st.success("Configuració guardada!")
        st.rerun()