import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image

# --- CONFIGURACIÓ DE LA PÀGINA ---
st.set_page_config(page_title="Comptabilitat Familiar", page_icon="💰", layout="wide")

# --- 🔒 SISTEMA DE SEGURETAT (LOGIN) ---
def check_password():
    """Retorna True si l'usuari ha encertat la contrasenya."""

    def password_entered():
        """Comprova si la contrasenya és correcta."""
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardem la clau en memòria
        else:
            st.session_state["password_correct"] = False

    # Si ja hem validat, tot ok
    if st.session_state.get("password_correct", False):
        return True

    # Mostrem el formulari de login
    st.title("🔒 Accés Restringit")
    st.text_input(
        "Contrasenya", type="password", on_change=password_entered, key="password"
    )
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Contrasenya incorrecta")
        
    return False

# SI LA CONTRASENYA NO ÉS CORRECTA, ATUREM EL PROGRAMA AQUÍ
if not check_password():
    st.stop()

# ========================================================
# A PARTIR D'AQUÍ, NOMÉS S'EXECUTA SI JA ESTEM LOGUEJATS
# ========================================================

# 1. Recuperem les claus
API_KEY = st.secrets["GEMINI_API_KEY"]

# 2. Connectem amb Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- FUNCIONS DE DADES ---
def carregar_dades():
    df = conn.read(ttl=0)
    if df.empty or len(df.columns) < 2:
        return pd.DataFrame(columns=["data", "concepte", "establiment", "quantitat", "categoria", "tipus"])
    
    df['establiment'] = df['establiment'].fillna("")
    df['concepte'] = df['concepte'].fillna("")
    df['categoria'] = df['categoria'].fillna("Altres")
    df['tipus'] = df['tipus'].fillna("Despesa")
    df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.date
    df = df.dropna(subset=['quantitat'])
    return df

def guardar_dades(df_nou):
    conn.update(data=df_nou)

# Carreguem dades
df = carregar_dades()

# --- SIDEBAR AMB BOTÓ DE TANCAR SESSIÓ ---
with st.sidebar:
    st.header("🔍 Filtres")
    
    # Botó per tancar sessió
    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()
        
    st.divider()
    
    opcio_data = st.selectbox("Període", ["Aquest Mes", "Mes Anterior", "Últims 7 dies", "Tot l'any", "Personalitzat"])
    avui = date.today()
    
    if opcio_data == "Aquest Mes":
        inici = avui.replace(day=1)
        fi = avui
    elif opcio_data == "Mes Anterior":
        primer = avui.replace(day=1)
        fi = primer - timedelta(days=1)
        inici = fi.replace(day=1)
    elif opcio_data == "Últims 7 dies":
        inici = avui - timedelta(days=7)
        fi = avui
    elif opcio_data == "Tot l'any":
        inici = avui.replace(month=1, day=1)
        fi = avui
    else:
        inici = st.date_input("Data Inici", avui - timedelta(days=30))
        fi = st.date_input("Data Fi", avui)
    
    st.caption(f"📅 {inici} - {fi}")

# --- FILTRATGE ---
if not df.empty:
    mask = (df['data'] >= inici) & (df['data'] <= fi)
    df_filtrat = df.loc[mask]
else:
    df_filtrat = df

# --- PÀGINA PRINCIPAL ---
st.title("💰 Comptabilitat al Núvol ☁️")

col1, col2, col3 = st.columns(3)
ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
saldo = df_filtrat['quantitat'].sum()

col1.metric("🟢 Ingressos", f"{ingr:.2f} €")
col2.metric("🔴 Despeses", f"{desp:.2f} €")
col3.metric("📊 Saldo Període", f"{saldo:.2f} €")

st.divider()

if not df_filtrat.empty:
    tab1, tab2 = st.tabs(["📊 Gràfics", "📝 Dades"])
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            df_g = df_filtrat.copy()
            df_g['valor_abs'] = df_g['quantitat'].abs()
            if not df_g.empty:
                fig = px.sunburst(df_g, path=['tipus', 'categoria', 'concepte'], values='valor_abs', color='tipus', 
                                  color_discrete_map={'Despesa':'#EF553B', 'Ingrés':'#00CC96'})
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
            fig2 = px.bar(ev, x='data', y='quantitat', color='quantitat', color_continuous_scale=px.colors.diverging.RdYlGn)
            st.plotly_chart(fig2, use_container_width=True)
    with tab2:
        st.dataframe(
            df_filtrat.sort_values(by='data', ascending=False),
            column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "quantitat": st.column_config.NumberColumn("€", format="%.2f €")},
            use_container_width=True,
            hide_index=True
        )

st.divider()
st.subheader("➕ Afegir Moviment")

prompt_comu = f"""
Analitza la informació. Retorna una LLISTA de JSONs.
Estructura obligatòria:
- 'data': Format ISO 'YYYY-MM-DD'. Si no la trobes, "AVUI". Si diu ahir, calcula-la (Avui: {date.today()}).
- 'concepte': Text breu en CATALÀ.
- 'establiment': Nom de la botiga.
- 'quantitat': Numéric (Negatiu=Despesa, Positiu=Ingrés).
- 'categoria': (Alimentació, Llar, Oci, Cotxe, Nòmina, Restauració, Extra).
- 'tipus': "Ingrés" o "Despesa".
"""

def processar_i_pujar(resposta):
    txt = resposta.text.replace("```json", "").replace("```", "").strip()
    try:
        dades = json.loads(txt)
        if isinstance(dades, dict): dades = [dades]
        
        noves = []
        for item in dades:
            data_f = item.get('data')
            if not data_f or data_f == "AVUI": data_f = date.today()
            
            noves.append({
                "data": data_f,
                "concepte": item.get('concepte', 'Varies'),
                "establiment": item.get('establiment', ''),
                "quantitat": item.get('quantitat', 0),
                "categoria": item.get('categoria', 'Altres'),
                "tipus": item.get('tipus', 'Despesa')
            })
        
        df_act = carregar_dades()
        df_final = pd.concat([df_act, pd.DataFrame(noves)], ignore_index=True)
        guardar_dades(df_final)
        st.success("✅ Guardat al Núvol!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error: {e}")

t1, t2 = st.tabs(["📝 Text", "📸 Foto"])
with t1:
    with st.form("txt"):
        t = st.text_input("Ex: Dinar al Viena 12€")
        if st.form_submit_button("Enviar") and t:
            with st.spinner("Pujant..."):
                res = model.generate_content([prompt_comu, t])
                processar_i_pujar(res)
with t2:
    with st.form("img"):
        im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
        if st.form_submit_button("Pujar Foto") and im:
            with st.spinner("Pujant..."):
                img_p = Image.open(im)
                res = model.generate_content([prompt_comu, "Extreu dades:", img_p])
                processar_i_pujar(res)