import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from PIL import Image
import uuid # Per generar codis únics per als grups de tiquets

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

# --- FUNCIONS ---
def carregar_dades():
    df = conn.read(ttl=0)
    # Estructura base v1.2
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
    
    if df.empty:
        return pd.DataFrame(columns=columnes_base)
    
    # MIGRACIÓ AUTOMÀTICA: Si falten columnes noves, les creem
    for col in columnes_base:
        if col not in df.columns:
            df[col] = ""

    # Neteja de dades
    df['establiment'] = df['establiment'].fillna("")
    df['concepte'] = df['concepte'].fillna("")
    df['categoria'] = df['categoria'].fillna("Altres")
    df['tipus'] = df['tipus'].fillna("Despesa")
    df['es_periodic'] = df['es_periodic'].fillna(False).infer_objects(copy=False)
    df['id_grup'] = df['id_grup'].fillna("")
    
    df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.date
    df = df.dropna(subset=['quantitat'])
    return df

def guardar_dades(df_nou):
    conn.update(data=df_nou)

df = carregar_dades()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("icona.svg", width=50)
    st.header("Menú")
    
    # Feedback de l'últim moviment
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
# 1. ZONA D'AFEGIR (MILLORADA v1.2)
# =================================================
st.title("➕ Afegir Moviment")

# Prompt avançat amb context de data i periodicitat
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

def processar_i_pujar(resposta):
    txt = resposta.text.replace("```json", "").replace("```", "").strip()
    try:
        dades = json.loads(txt)
        if isinstance(dades, dict): dades = [dades]
        
        noves = []
        # Generem un ID únic per a aquest grup (tiquet)
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
                "id_grup": grup_id_unic # Tots els items d'aquesta pujada tindran el mateix ID
            })
            msg_resum += f"- {concepte}: {quantitat}€\n"
        
        df_act = carregar_dades()
        df_final = pd.concat([df_act, pd.DataFrame(noves)], ignore_index=True)
        guardar_dades(df_final)
        
        # Guardem estat per mostrar avís i netegem inputs
        st.session_state["ultim_moviment"] = msg_resum
        
        # BUIDAR INPUTS (TRUC MÀGIC)
        if "input_text_key" in st.session_state:
            st.session_state["input_text_key"] = ""
        
        st.rerun()
        
    except Exception as e:
        st.error(f"Error: {e}")

# Funció separada per gestionar l'enviament del text
def enviar_text_callback():
    # Agafem el text directament de l'estat
    text_a_processar = st.session_state.input_text_key
    
    if text_a_processar:
        # Mostrem un missatge temporal mentre processa (no podem usar st.spinner dins un callback fàcilment, però no passa res)
        # Cridem a la IA
        res = model.generate_content([prompt_comu, text_a_processar])
        
        # Processem la resposta (nota: he adaptat lleugerament processar_i_pujar perquè no faci rerun, el farem aquí)
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
            
            # Guardem l'èxit en sessió
            st.session_state["ultim_moviment"] = msg_resum
            
            # BUIDEM LA CAIXA DE TEXT (Ara sí que funcionarà perquè estem dins un callback)
            st.session_state.input_text_key = ""
            
        except Exception as e:
            st.error(f"Error: {e}")

t1, t2 = st.tabs(["📝 Text", "📸 Foto"])

with t1:
    # Aquesta caixa de text està connectada a "input_text_key"
    st.text_area(
        "Descriu moviments:", 
        key="input_text_key", 
        height=100, 
        placeholder="Ex: Sopar ahir al Viena 45 euros"
    )
    
    # EL CANVI CLAU: Usem 'on_click'
    st.button("Enviar Text", on_click=enviar_text_callback)

with t2:
    im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
    if st.button("Processar Foto") and im:
        with st.spinner("Desglossant tiquet..."):
            img_p = Image.open(im)
            res = model.generate_content([prompt_comu, "Extreu tots els productes i preus:", img_p])
            # Per la foto, podem reutilitzar la lògica antiga o adaptar-la, 
            # però com que el file_uploader es neteja diferent, ho deixem com estava per simplificar
            # (Aquí hauríem de copiar la lògica de processament de dalt, però sense el callback de text)
            # Per no duplicar codi, l'ideal seria tenir una funció "core_processar(json)" 
            # però per arreglar el teu error ràpid, deixem la foto com estava:
            
            # ... (Copia aquí la lògica de processament de la foto anterior, sense tocar session_state de text)
            txt = res.text.replace("```json", "").replace("```", "").strip()
            try:
                dades = json.loads(txt)
                if isinstance(dades, dict): dades = [dades]
                noves = []
                grup_id_unic = str(uuid.uuid4())[:8] 
                msg_resum = ""
                for item in dades:
                    # ... (mateixa lògica d'abans) ...
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