import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image
import uuid 

# --- 1. CONFIGURACIÓ DE PÀGINA ---
st.set_page_config(page_title="Comptabilitat Familiar v1.2", page_icon="icona.svg", layout="wide")

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

# --- FUNCIONS (VERSIÓ A PROVA DE BALES) ---
def carregar_dades():
    # Llegim sense caché
    df = conn.read(ttl=0)
    
    # Definim columnes obligatòries
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
    
    # Si està buit, retornem estructura buida
    if df.empty:
        return pd.DataFrame(columns=columnes_base)
    
    # Assegurem que totes les columnes existeixen
    for col in columnes_base:
        if col not in df.columns:
            df[col] = ""

    # NETEJA AGRESSIVA DE DADES (Per evitar errors a la taula)
    
    # 1. Dates: Convertim a datetime i si falla posa NaT (Not a Time)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    
    # 2. Quantitat: Convertim a numèric, si falla posa NaN
    df['quantitat'] = pd.to_numeric(df['quantitat'], errors='coerce')
    
    # 3. Eliminem files que no tinguin data o quantitat (són errors o files buides)
    df = df.dropna(subset=['data', 'quantitat'])
    
    # 4. Ara que estem segurs que són dates, convertim a objecte 'date' (sense hores)
    df['data'] = df['data'].dt.date
    
    # 5. Textos: Omplim buits amb strings buits
    df['establiment'] = df['establiment'].fillna("").astype(str)
    df['concepte'] = df['concepte'].fillna("").astype(str)
    df['categoria'] = df['categoria'].fillna("Altres").astype(str)
    df['tipus'] = df['tipus'].fillna("Despesa").astype(str)
    df['id_grup'] = df['id_grup'].fillna("").astype(str)
    
    # 6. Booleans (Periòdic): Assegurem que sigui True/False
    # Google Sheets a vegades torna "TRUE" com a text, això ho arregla
    df['es_periodic'] = df['es_periodic'].astype(str).map({'TRUE': True, 'True': True, 'true': True, '1': True, '1.0': True}).fillna(False)
    df['es_periodic'] = df['es_periodic'].astype(bool)

    return df

def guardar_dades(df_nou):
    conn.update(data=df_nou)

df = carregar_dades()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("icona.svg", width=50)
    st.header("Menú")
    
    if "ultim_moviment" in st.session_state:
        st.success("✅ Últim afegit:")
        st.caption(st.session_state["ultim_moviment"])
        if st.button("Netejar avís"):
            del st.session_state["ultim_moviment"]
            st.rerun()
    
    st.divider()
    if st.button("🔒 Tancar Sessió"):
        st.session_state["password_correct"] = False
        st.rerun()
        
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
    else: 
        inici = avui - timedelta(days=7)
        fi = avui

# --- LÒGICA DE FILTRATGE ---
if not df.empty:
    mask = (df['data'] >= inici) & (df['data'] <= fi)
    df_filtrat = df.loc[mask]
else:
    df_filtrat = df

# =================================================
# 1. ZONA D'AFEGIR
# =================================================
st.title("➕ Afegir Moviment")

prompt_comu = f"""
AVUI ÉS: {date.today()}.
Analitza la informació. Si l'usuari diu "ahir" o dates relatives, calcula la data exacta basant-te en que avui és {date.today()}.

Retorna una LLISTA de JSONs.
Estructura:
- 'data': Format ISO 'YYYY-MM-DD'.
- 'concepte': Text breu en CATALÀ.
- 'establiment': Nom de la botiga/empresa.
- 'quantitat': Numéric (Negatiu=Despesa, Positiu=Ingrés).
- 'categoria': (Alimentació, Llar, Oci, Cotxe, Nòmina, Restauració, Extra, Subscripcions, Educació, Salut).
- 'tipus': "Ingrés" o "Despesa".
- 'es_periodic': true o false. (Detecta si és: Lloguer, Netflix, Spotify, Nòmina, Hipoteca, Gimnàs, Assegurança).

Si és un tiquet de supermercat amb molts items, separa'ls.
"""

# --- CALLBACK PER AL TEXT ---
def enviar_text_callback():
    text_a_processar = st.session_state.input_text_key
    
    if text_a_processar:
        res = model.generate_content([prompt_comu, text_a_processar])
        
        txt = res.text.replace("```json", "").replace("```", "").strip()
        try:
            dades = json.loads(txt)
            if isinstance(dades, dict): dades = [dades]
            
            noves = []
            grup_id_unic = str(uuid.uuid4())[:8] 
            msg_resum = ""

            for item in dades:
                data_f = item.get('data')
                if not data_f or data_f == "AVUI": data_f = date.today()
                
                concepte = item.get('concepte', 'Varies')
                quantitat = item.get('quantitat', 0)
                
                noves.append({
                    "data": data_f,
                    "concepte": concepte,
                    "establiment": item.get('establiment', ''),
                    "quantitat": quantitat,
                    "categoria": item.get('categoria', 'Altres'),
                    "tipus": item.get('tipus', 'Despesa'),
                    "es_periodic": item.get('es_periodic', False),
                    "id_grup": grup_id_unic
                })
                msg_resum += f"- {concepte}: {quantitat}€\n"
            
            df_act = carregar_dades()
            df_final = pd.concat([df_act, pd.DataFrame(noves)], ignore_index=True)
            guardar_dades(df_final)
            
            st.session_state["ultim_moviment"] = msg_resum
            
            # Buidem la caixa
            st.session_state.input_text_key = ""
            
        except Exception as e:
            st.error(f"Error: {e}")

t1, t2 = st.tabs(["📝 Text", "📸 Foto"])

with t1:
    st.text_area(
        "Descriu moviments:", 
        key="input_text_key", 
        height=100, 
        placeholder="Ex: Sopar ahir al Viena 45 euros"
    )
    st.button("Enviar Text", on_click=enviar_text_callback)

with t2:
    im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
    if st.button("Processar Foto") and im:
        with st.spinner("Desglossant tiquet..."):
            img_p = Image.open(im)
            res = model.generate_content([prompt_comu, "Extreu tots els productes i preus:", img_p])
            
            txt = res.text.replace("```json", "").replace("```", "").strip()
            try:
                dades = json.loads(txt)
                if isinstance(dades, dict): dades = [dades]
                noves = []
                grup_id_unic = str(uuid.uuid4())[:8] 
                msg_resum = ""
                for item in dades:
                    data_f = item.get('data')
                    if not data_f or data_f == "AVUI": data_f = date.today()
                    noves.append({
                        "data": data_f,
                        "concepte": item.get('concepte', 'Varies'),
                        "establiment": item.get('establiment', ''),
                        "quantitat": item.get('quantitat', 0),
                        "categoria": item.get('categoria', 'Altres'),
                        "tipus": item.get('tipus', 'Despesa'),
                        "es_periodic": item.get('es_periodic', False),
                        "id_grup": grup_id_unic
                    })
                    msg_resum += f"- {item.get('concepte')}: {item.get('quantitat')}€\n"
                
                df_act = carregar_dades()
                df_final = pd.concat([df_act, pd.DataFrame(noves)], ignore_index=True)
                guardar_dades(df_final)
                st.session_state["ultim_moviment"] = msg_resum
                st.rerun()
            except Exception as e:
                st.error(f"Error foto: {e}")

# =================================================
# 2. DASHBOARD
# =================================================
st.divider()

if "ultim_moviment" in st.session_state:
    st.info(f"🚀 Últims moviments afegits:\n{st.session_state['ultim_moviment']}")

st.header("📊 Estat dels Comptes")

# Càlculs segurs
if not df_filtrat.empty:
    ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
    desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
    saldo = df_filtrat['quantitat'].sum()
    desp_fixes = df_filtrat[(df_filtrat['es_periodic'] == True) & (df_filtrat['quantitat'] < 0)]['quantitat'].sum()
else:
    ingr, desp, saldo, desp_fixes = 0.0, 0.0, 0.0, 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Ingressos", f"{ingr:.2f} €")
col2.metric("🔴 Despeses", f"{desp:.2f} €")
col3.metric("🔄 Despeses Fixes", f"{desp_fixes:.2f} €")
col4.metric("📊 Saldo", f"{saldo:.2f} €")

if not df_filtrat.empty:
    tab_g, tab_d = st.tabs(["📉 Gràfics", "✏️ Edició"])
    
    with tab_g:
        c1, c2 = st.columns(2)
        with c1:
            df_g = df_filtrat.copy()
            df_g['valor_abs'] = df_g['quantitat'].abs()
            path_chart = ['tipus', 'categoria', 'establiment'] if 'establiment' in df_g.columns else ['tipus', 'categoria']
            # Evitem error si no hi ha dades per mostrar
            if not df_g.empty and df_g['valor_abs'].sum() > 0:
                fig = px.sunburst(df_g, path=path_chart, values='valor_abs', 
                                color='tipus', color_discrete_map={'Despesa':'#EF553B', 'Ingrés':'#00CC96'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hi ha dades per mostrar gràfics.")
        with c2:
            ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
            if not ev.empty:
                fig2 = px.bar(ev, x='data', y='quantitat', color='quantitat', 
                              color_continuous_scale=px.colors.diverging.RdYlGn)
                st.plotly_chart(fig2, use_container_width=True)

    with tab_d:
        st.caption("Doble clic per editar. Els tiquets desglossats tenen el mateix 'Grup ID'.")
        
        df_per_editar = df_filtrat.sort_values(by='data', ascending=False)
        
        df_editat = st.data_editor(
            df_per_editar,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "quantitat": st.column_config.NumberColumn("€", format="%.2f €"),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=["Alimentació", "Llar", "Oci", "Cotxe", "Nòmina", "Restauració", "Extra", "Salut", "Educació", "Subscripcions"]),
                "tipus": st.column_config.SelectboxColumn("Tipus", options=["Ingrés", "Despesa"]),
                "es_periodic": st.column_config.CheckboxColumn("Periòdic?"),
                "id_grup": st.column_config.TextColumn("Grup ID", disabled=True)
            },
            key="editor_principal"
        )
        
        if st.button("💾 Guardar Canvis Taula"):
            with st.spinner("Guardant..."):
                mask_fora = (df['data'] < inici) | (df['data'] > fi)
                df_restant = df.loc[mask_fora]
                df_final = pd.concat([df_restant, df_editat], ignore_index=True)
                guardar_dades(df_final)
                st.success("Fet!")
                st.rerun()