import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image

# --- CONFIGURACIÓ ---
st.set_page_config(page_title="Comptabilitat Familiar", page_icon="💰", layout="wide")

# 1. Recuperem les claus SECRETES del núvol (més endavant t'explico on es posen)
API_KEY = st.secrets["GEMINI_API_KEY"]

# 2. Connectem amb Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- FUNCIONS DE DADES ---
def carregar_dades():
    # Llegim el full de càlcul directament (full 1 per defecte)
    df = conn.read(ttl=0) # ttl=0 vol dir que no guardi caché, que ho llegeixi fresc sempre
    
    # Si està buit o no té columnes, ho gestionem
    if df.empty or len(df.columns) < 2:
        return pd.DataFrame(columns=["data", "concepte", "establiment", "quantitat", "categoria", "tipus"])
    
    # Assegurem tipus de dades correcte
    # Convertim columnes buides a string per evitar errors
    df['establiment'] = df['establiment'].fillna("")
    df['concepte'] = df['concepte'].fillna("")
    df['categoria'] = df['categoria'].fillna("Altres")
    df['tipus'] = df['tipus'].fillna("Despesa")
    
    # La data
    df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.date
    
    # Eliminem files buides si n'hi ha
    df = df.dropna(subset=['quantitat'])
    
    return df

def guardar_dades(df_nou):
    # Actualitzem el full de càlcul
    conn.update(data=df_nou)

# Carreguem dades inicials
df = carregar_dades()

# --- SIDEBAR (Igual que abans) ---
with st.sidebar:
    st.header("🔍 Filtres")
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

# --- LÒGICA DE FILTRATGE ---
if not df.empty:
    mask = (df['data'] >= inici) & (df['data'] <= fi)
    df_filtrat = df.loc[mask]
else:
    df_filtrat = df

# --- PÀGINA PRINCIPAL ---
st.title("💰 Comptabilitat al Núvol ☁️")

# KPIs
col1, col2, col3 = st.columns(3)
ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
saldo = df_filtrat['quantitat'].sum()

col1.metric("🟢 Ingressos", f"{ingr:.2f} €")
col2.metric("🔴 Despeses", f"{desp:.2f} €")
col3.metric("📊 Saldo Període", f"{saldo:.2f} €")

st.divider()

# GRÀFICS
if not df_filtrat.empty:
    tab1, tab2 = st.tabs(["📊 Gràfics", "📝 Dades"])
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            # Gràfic Solar
            df_g = df_filtrat.copy()
            df_g['valor_abs'] = df_g['quantitat'].abs()
            # Només mostrem si hi ha dades
            if not df_g.empty:
                fig = px.sunburst(df_g, path=['tipus', 'categoria', 'concepte'], values='valor_abs', color='tipus', 
                                  color_discrete_map={'Despesa':'#EF553B', 'Ingrés':'#00CC96'})
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            # Evolució
            ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
            fig2 = px.bar(ev, x='data', y='quantitat', color='quantitat', color_continuous_scale=px.colors.diverging.RdYlGn)
            st.plotly_chart(fig2, use_container_width=True)
            
    with tab2:
        # No posem editor per seguretat i simplicitat al mòbil, només visualització neta
        st.dataframe(
            df_filtrat.sort_values(by='data', ascending=False),
            column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "quantitat": st.column_config.NumberColumn("€", format="%.2f €")},
            use_container_width=True,
            hide_index=True
        )

# --- ENTRADA DE DADES ---
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
        
        # Llegim, afegim i guardem
        df_actual = carregar_dades()
        df_final = pd.concat([df_actual, pd.DataFrame(noves)], ignore_index=True)
        guardar_dades(df_final)
        st.success("✅ Guardat al Núvol de Google!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error: {e}")

t1, t2 = st.tabs(["📝 Text", "📸 Foto"])
with t1:
    with st.form("txt"):
        t = st.text_input("Ex: Dinar al Viena 12€")
        if st.form_submit_button("Enviar") and t:
            with st.spinner("Pujant al núvol..."):
                res = model.generate_content([prompt_comu, t])
                processar_i_pujar(res)

with t2:
    with st.form("img"):
        im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
        if st.form_submit_button("Pujar Foto") and im:
            with st.spinner("Analitzant i pujant..."):
                img_p = Image.open(im)
                res = model.generate_content([prompt_comu, "Extreu dades:", img_p])
                processar_i_pujar(res)