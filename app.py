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
        background-color: #ffffff;
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
    }
    .family-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 1.5rem;
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
    st.text_input("Contrasenya familiar", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contrasenya incorrecta")
    return False

if not check_password():
    st.stop()

# --- 2. CONNEXIONS I MODELS ---
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3-flash-preview') 
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
        # Columnes: concepte, quantitat, categoria, tipus, dia, frequencia (Mensual, Trimestral, Anual)
        if df_rec.empty:
            return pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia", "frequencia"])
        return df_rec
    except:
        return pd.DataFrame(columns=["concepte", "quantitat", "categoria", "tipus", "dia", "frequencia"])

def guardar_dades(df_nou):
    conn.update(data=df_nou)

# --- 4. LÒGICA DE RECURRENTS (Millorada: Mensual, Trimestral, Anual) ---
def comprovar_recurrents_pendents(df_actual, df_config):
    if df_config.empty: return []
    avui = date.today()
    moviments_a_afegir = []
    
    for rec in df_config.to_dict('records'):
        try:
            dia_fix = int(rec['dia'])
            freq = rec.get('frequencia', 'Mensual')
            data_tocaria = date(avui.year, avui.month, min(dia_fix, 28))
            
            # Lògica segons freqüència
            ha_de_sortir = False
            if freq == 'Mensual':
                ha_de_sortir = True
            elif freq == 'Trimestral' and avui.month in [1, 4, 7, 10]:
                ha_de_sortir = True
            elif freq == 'Anual' and avui.month == 1: # Exemple: cada gener
                ha_de_sortir = True

            if ha_de_sortir and avui >= data_tocaria:
                # Mirem si ja existeix aquest mes o si està saltat
                duplicat = df_actual[(df_actual['data'].apply(lambda x: x.month) == avui.month) & 
                                     (df_actual['data'].apply(lambda x: x.year) == avui.year) &
                                     (df_actual['concepte'] == rec['concepte'])]
                
                saltat = df_actual[(df_actual['data'].apply(lambda x: x.month) == avui.month) & 
                                   (df_actual['concepte'] == f"SALTAT: {rec['concepte']}")]
                
                if duplicat.empty and saltat.empty:
                    moviments_a_afegir.append({
                        "data": data_tocaria, "concepte": rec['concepte'], "establiment": "Recurrent Automàtic",
                        "quantitat": rec['quantitat'], "categoria": rec['categoria'], "tipus": rec['tipus'],
                        "es_periodic": True, "Acció": "Afegir"
                    })
        except: continue
    return moviments_a_afegir

# Carreguem dades globals
df = carregar_dades()
df_rec_config = carregar_recurrents()

# --- 5. SIDEBAR (FILTRES I ALERTES) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6073/6073873.png", width=60)
    st.header("Menú Familiar")
    
    # 🔔 ALERTES DE PAGAMENTS
    pendents = comprovar_recurrents_pendents(df, df_rec_config)
    if pendents:
        st.warning(f"🔔 {len(pendents)} Pagaments pendents")
        with st.expander("Gestionar Avisos", expanded=True):
            df_p = pd.DataFrame(pendents)
            editat_p = st.data_editor(df_p, column_config={
                "Acció": st.column_config.SelectboxColumn("Què vols fer?", options=["Afegir", "Saltar (Ignorar)", "Pendent"]),
                "concepte": st.column_config.TextColumn("Concepte", disabled=True),
                "quantitat": st.column_config.NumberColumn("€", disabled=True)
            }, hide_index=True, key="sidebar_rec_editor")
            
            if st.button("🚀 Processar"):
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
    st.subheader("📅 Període de dades")
    opcio_data = st.selectbox("Selecciona:", ["Aquest Mes", "Mes Anterior", "Últims 30 dies", "Tot l'any", "Personalitzat"])
    avui = date.today()
    if opcio_data == "Aquest Mes": inici, fi = avui.replace(day=1), avui
    elif opcio_data == "Mes Anterior":
        fi = avui.replace(day=1) - timedelta(days=1)
        inici = fi.replace(day=1)
    elif opcio_data == "Tot l'any": inici, fi = avui.replace(month=1, day=1), avui
    else:
        inici = st.date_input("De:", avui - timedelta(days=30))
        fi = st.date_input("A:", avui)

    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()

# Filtrar dades per a tota l'app
mask = (df['data'] >= inici) & (df['data'] <= fi)
df_filtrat = df.loc[mask]

# --- 6. INTERFÍCIE PRINCIPAL ---
st.markdown(f"""
    <div class="family-header">
        <h1 style='margin:0'>Gestió Econòmica Familiar</h1>
        <p style='margin:0'>Projecte de Jose Manuel i Alba | {inici.strftime('%d/%m/%y')} - {fi.strftime('%d/%m/%y')}</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Balanç i Gràfics", "➕ Registre (Text/Foto)", "🤖 Assessor IA", "⚙️ Gestió de Recurrents"])

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
    c3.metric("Estalvi Net", f"{bal:,.2f} €")

    st.divider()
    
    # GRAFICA PERSONALITZABLE
    tipus_grafic = st.radio("Personalitza el gràfic:", ["Evolució Saldo", "Detall per Ingressos", "Detall per Despeses"], horizontal=True)
    
    if not df_filtrat.empty:
        if tipus_grafic == "Evolució Saldo":
            df_ev = df_filtrat.groupby('data')['quantitat'].sum().cumsum().reset_index()
            fig = px.line(df_ev, x='data', y='quantitat', title="Evolució de l'estalvi en el període", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        elif tipus_grafic == "Detall per Despeses":
            df_desp = df_filtrat[df_filtrat['quantitat'] < 0].copy()
            df_desp['quantitat'] = df_desp['quantitat'].abs()
            fig = px.sunburst(df_desp, path=['categoria', 'establiment'], values='quantitat', title="On han anat els diners?")
            st.plotly_chart(fig, use_container_width=True)
        else: # Ingressos
            df_ing = df_filtrat[df_filtrat['quantitat'] > 0].copy()
            fig = px.bar(df_ing, x='categoria', y='quantitat', color='categoria', title="Origen dels Ingressos")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("✏️ Edició de Moviments")
    df_ed = st.data_editor(df_filtrat.sort_values(by='data', ascending=False), num_rows="dynamic", use_container_width=True, key="main_table")
    if st.button("💾 Guardar Canvis a la Taula"):
        mask_fora = (df['data'] < inici) | (df['data'] > fi)
        df_final = pd.concat([df.loc[mask_fora], df_ed], ignore_index=True)
        guardar_dades(df_final)
        st.success("Dades guardades!")
        st.rerun()

# --- TAB 2: REGISTRE (TEXT I FOTO) ---
with tab2:
    prompt_comu = f"AVUI ÉS: {date.today()}. Retorna LLISTA de JSONs: 'data' (YYYY-MM-DD), 'concepte', 'establiment', 'quantitat' (Negatiu si és despesa), 'categoria', 'tipus', 'es_periodic' (bool)."
    
    col_text, col_foto = st.columns(2)
    with col_text:
        st.subheader("📝 Per Text o Veu")
        txt = st.text_area("Què ha passat?", placeholder="Ahir vam gastar 30€ al Mercadona...")
        if st.button("Processar Text"):
            with st.spinner("La IA està classificant..."):
                res = model.generate_content([prompt_comu, txt])
                dades = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                if isinstance(dades, dict): dades = [dades]
                noves = pd.DataFrame(dades)
                noves['id_grup'] = uuid.uuid4().hex[:6]
                guardar_dades(pd.concat([carregar_dades(), noves], ignore_index=True))
                st.success("Moviment afegit!")
                st.rerun()

    with col_foto:
        st.subheader("📸 Per Foto de Ticket")
        fitxer = st.file_uploader("Puja el ticket", type=['jpg','png','jpeg'])
        if st.button("Llegir Ticket") and fitxer:
            with st.spinner("Analitzant imatge..."):
                img = Image.open(fitxer)
                res = model.generate_content([prompt_comu, "Extrau els productes i total d'aquesta imatge:", img])
                dades = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                if isinstance(dades, dict): dades = [dades]
                noves = pd.DataFrame(dades)
                noves['id_grup'] = uuid.uuid4().hex[:6]
                guardar_dades(pd.concat([carregar_dades(), noves], ignore_index=True))
                st.success("Ticket registrat!")
                st.rerun()

# --- TAB 3: ASSESSOR IA ---
with tab3:
    st.subheader("🕵️ L'Assessor de Jose i Alba")
    if st.button("Generar Informe Estratègic"):
        with st.spinner("Analitzant..."):
            context = f"Balanç: {bal}€. Deute: 165€. Reclamació BBVA: 1800€. Jose atur."
            try:
                res = model.generate_content(f"Ets assessor familiar de Jose i Alba. Analitza: {context}. Sigues motivador i dóna 3 consells clau en català.")
                st.markdown(f'<div class="advisor-box">{res.text}</div>', unsafe_allow_html=True)
            except:
                st.error("Error en la connexió amb la IA.")

# --- TAB 4: GESTIÓ DE RECURRENTS ---
with tab4:
    st.subheader("⚙️ Configuració de Pagaments Periòdics")
    st.info("Configura aquí els pagaments que el sistema t'avisarà cada mes, trimestre o any.")
    
    # Assegurem que la columna frequencia existeix
    if 'frequencia' not in df_rec_config.columns:
        df_rec_config['frequencia'] = 'Mensual'

    df_rec_ed = st.data_editor(df_rec_config, num_rows="dynamic", use_container_width=True, column_config={
        "frequencia": st.column_config.SelectboxColumn("Freqüència", options=["Mensual", "Trimestral", "Anual"], required=True),
        "dia": st.column_config.NumberColumn("Dia del mes", min_value=1, max_value=31)
    }, key="config_rec_editor")
    
    if st.button("💾 Guardar Configuració Recurrents"):
        conn.update(worksheet="Recurrents", data=df_rec_ed)
        st.success("Configuració actualitzada!")
        st.rerun()