import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image

# --- 1. CONFIGURACIÓ DE PÀGINA (AMB ICONA NOVA) ---
# Assegura't que el nom del fitxer coincideix amb el que has pujat a GitHub
st.set_page_config(page_title="Comptabilitat Familiar", page_icon="icona.svg", layout="wide")

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
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- FUNCIONS ---
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

df = carregar_dades()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("icona.svg", width=50) # Mostrem la icona també aquí
    st.header("Menú")
    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()
    st.divider()
    
    # Filtres
    st.subheader("📅 Filtre de Dades")
    opcio_data = st.selectbox("Període", ["Aquest Mes", "Mes Anterior", "Últims 7 dies", "Tot l'any", "Personalitzat"])
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
    elif opcio_data == "Personalitzat":
        inici = st.date_input("Data Inici", avui - timedelta(days=30))
        fi = st.date_input("Data Fi", avui)
    else: # Últims 7 dies
        inici = avui - timedelta(days=7)
        fi = avui

# --- LÒGICA DE FILTRATGE ---
if not df.empty:
    mask = (df['data'] >= inici) & (df['data'] <= fi)
    df_filtrat = df.loc[mask]
else:
    df_filtrat = df

# =================================================
# 1. ZONA D'AFEGIR (ARA A DALT DE TOT)
# =================================================
st.title("➕ Afegir Moviment")

prompt_comu = f"""
Analitza la informació. Retorna una LLISTA de JSONs.
Estructura:
- 'data': Format ISO 'YYYY-MM-DD'. Si no la trobes, "AVUI".
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
        st.success("✅ Guardat correctament!")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

t1, t2 = st.tabs(["📝 Text (Gran)", "📸 Foto"])
with t1:
    with st.form("txt"):
        # --- MILLORA 2: TEXT AREA MÉS GRAN ---
        t = st.text_area("Descriu les despeses (pots enganxar llistes llargues)", height=150, placeholder="Ex:\n- Dinar Viena 12€\n- Mercadona 45€\n- Benzina 30€")
        if st.form_submit_button("Enviar") and t:
            with st.spinner("Processant..."):
                res = model.generate_content([prompt_comu, t])
                processar_i_pujar(res)
with t2:
    with st.form("img"):
        im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
        if st.form_submit_button("Pujar Foto") and im:
            with st.spinner("Llegint ticket..."):
                img_p = Image.open(im)
                res = model.generate_content([prompt_comu, "Extreu dades:", img_p])
                processar_i_pujar(res)

st.divider()

# =================================================
# 2. DASHBOARD I GRÀFICS (ARA A BAIX)
# =================================================
st.header("📊 Estat dels Comptes")

col1, col2, col3 = st.columns(3)
ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
saldo = df_filtrat['quantitat'].sum()

col1.metric("🟢 Ingressos", f"{ingr:.2f} €")
col2.metric("🔴 Despeses", f"{desp:.2f} €")
col3.metric("📊 Saldo", f"{saldo:.2f} €")

if not df_filtrat.empty:
    tab_g, tab_d = st.tabs(["📉 Gràfics Visuals", "✏️ Edició de Dades"])
    
    with tab_g:
        c1, c2 = st.columns(2)
        with c1:
            # Gràfic Solar
            df_g = df_filtrat.copy()
            df_g['valor_abs'] = df_g['quantitat'].abs()
            fig = px.sunburst(df_g, path=['tipus', 'categoria', 'concepte'], values='valor_abs', 
                              color='tipus', color_discrete_map={'Despesa':'#EF553B', 'Ingrés':'#00CC96'})
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            # Evolució
            ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
            fig2 = px.bar(ev, x='data', y='quantitat', color='quantitat', 
                          color_continuous_scale=px.colors.diverging.RdYlGn)
            st.plotly_chart(fig2, use_container_width=True)

    with tab_d:
        st.info("Pots editar les cel·les directament. Recorda clicar 'Guardar Canvis' al final.")
        
        # --- MILLORA 3: EDICIÓ DIRECTA ---
        # Mostrem TOTS els moviments del període filtrat per editar
        # Ordenem per data descendent per tenir els nous a dalt
        df_per_editar = df_filtrat.sort_values(by='data', ascending=False)
        
        df_editat = st.data_editor(
            df_per_editar,
            num_rows="dynamic", # Permet afegir i esborrar files
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "quantitat": st.column_config.NumberColumn("€", format="%.2f €"),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentació", "Llar", "Oci", "Cotxe", "Nòmina", "Restauració", "Extra", "Salut", "Educació"]),
                "tipus": st.column_config.SelectboxColumn("Tipus", options=["Ingrés", "Despesa"])
            },
            key="editor_principal"
        )
        
        if st.button("💾 Guardar Canvis a la Taula"):
            with st.spinner("Actualitzant Google Sheets..."):
                # 1. Agafem les dades que NO estaven al filtre (per no perdre-les)
                mask_fora = (df['data'] < inici) | (df['data'] > fi)
                df_restant = df.loc[mask_fora]
                
                # 2. Ajuntem les dades velles amb les editades
                df_final = pd.concat([df_restant, df_editat], ignore_index=True)
                
                # 3. Guardem
                guardar_dades(df_final)
                st.success("Taula actualitzada correctament!")
                st.rerun()