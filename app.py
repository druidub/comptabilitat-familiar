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
st.set_page_config(page_title="Comptabilitat Familiar v1.3", page_icon="icona.svg", layout="wide")

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
# Canvia a 'gemini-1.5-flash' o el que estiguis usant si '3-flash-preview' et dona problemes puntuals
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3-flash-preview') 

# --- FUNCIONS ---
def carregar_dades():
    df = conn.read(ttl=0)
    # Afegim columna nova per gestionar recurrents (opcional, però útil per saber origen)
    columnes_base = ["data", "concepte", "establiment", "quantitat", "categoria", "tipus", "es_periodic", "id_grup"]
    
    if df.empty:
        return pd.DataFrame(columns=columnes_base)
    
    for col in columnes_base:
        if col not in df.columns:
            df[col] = ""

    # NETEJA DE DADES
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['quantitat'] = pd.to_numeric(df['quantitat'], errors='coerce')
    df = df.dropna(subset=['data', 'quantitat'])
    df['data'] = df['data'].dt.date
    
    df['establiment'] = df['establiment'].fillna("").astype(str)
    df['concepte'] = df['concepte'].fillna("").astype(str)
    df['categoria'] = df['categoria'].fillna("Altres").astype(str)
    df['tipus'] = df['tipus'].fillna("Despesa").astype(str)
    df['id_grup'] = df['id_grup'].fillna("").astype(str)
    
    # Normalitzem es_periodic
    df['es_periodic'] = df['es_periodic'].astype(str).map({'TRUE': True, 'True': True, 'true': True, '1': True, '1.0': True}).fillna(False)
    df['es_periodic'] = df['es_periodic'].astype(bool)

    return df

def guardar_dades(df_nou):
    conn.update(data=df_nou)

# --- GESTIÓ DE RECURRENTS ---
# Aquesta funció defineix els teus moviments fixos. 
# IDEALMENT: En el futur això podria estar en un altre full de càlcul, però per ara ho posem al codi per simplicitat.
def obtenir_configuracio_recurrents():
    # Format: Concepte, Quantitat, Categoria, Tipus, Dia del mes (1-31)
    # Afegeix/Modifica aquí els teus fixos:
    return [
        {"concepte": "Lloguer Pis", "quantitat": -800.00, "categoria": "Llar", "tipus": "Despesa", "dia": 5},
        {"concepte": "Netflix", "quantitat": -12.99, "categoria": "Subscripcions", "tipus": "Despesa", "dia": 15},
        {"concepte": "Spotify", "quantitat": -10.99, "categoria": "Subscripcions", "tipus": "Despesa", "dia": 25},
        {"concepte": "Nòmina", "quantitat": 1800.00, "categoria": "Nòmina", "tipus": "Ingrés", "dia": 1},
        {"concepte": "Gimnàs", "quantitat": -35.00, "categoria": "Salut", "tipus": "Despesa", "dia": 1}
    ]

def comprovar_recurrents_pendents(df_actual):
    avui = date.today()
    mes_actual = avui.month
    any_actual = avui.year
    
    recurrents_config = obtenir_configuracio_recurrents()
    moviments_a_afegir = []
    
    for rec in recurrents_config:
        # Calculem la data que li tocaria aquest mes
        try:
            data_tocaria = date(any_actual, mes_actual, rec['dia'])
        except ValueError:
            # Per si el mes no té dia 31, agafem l'últim
            data_tocaria = date(any_actual, mes_actual, 1) + timedelta(days=32)
            data_tocaria = data_tocaria.replace(day=1) - timedelta(days=1)

        # Si avui és igual o posterior al dia que toca...
        if avui >= data_tocaria:
            # Comprovem si JA existeix al full de càlcul per aquest mes i concepte
            # Filtrem per mes, any i concepte exacte
            duplicat = df_actual[
                (df_actual['data'].apply(lambda x: x.month) == mes_actual) &
                (df_actual['data'].apply(lambda x: x.year) == any_actual) &
                (df_actual['concepte'] == rec['concepte']) &
                (abs(df_actual['quantitat'] - rec['quantitat']) < 0.01) # Mateixa quantitat
            ]
            
            if duplicat.empty:
                # No existeix, l'hem de proposar
                moviments_a_afegir.append({
                    "data": data_tocaria, # Posem la data teòrica (dia 5), no avui
                    "concepte": rec['concepte'],
                    "establiment": "Recurrent",
                    "quantitat": rec['quantitat'],
                    "categoria": rec['categoria'],
                    "tipus": rec['tipus'],
                    "es_periodic": True,
                    "id_grup": "AUTO_" + str(uuid.uuid4())[:8]
                })
    
    return moviments_a_afegir

df = carregar_dades()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("icona.svg", width=50)
    st.header("Menú")
    
    # 1. Comprovació Automàtica de Recurrents
    pendents = comprovar_recurrents_pendents(df)
    if pendents:
        st.warning(f"🔔 {len(pendents)} Moviments Fixos pendents!")
        with st.expander("Veure i Aprovar"):
            st.write("Aquest mes falten:")
            for p in pendents:
                st.caption(f"{p['data']}: {p['concepte']} ({p['quantitat']}€)")
            
            if st.button("✅ Afegir-los tots ara"):
                df_nous = pd.DataFrame(pendents)
                df_final = pd.concat([df, df_nous], ignore_index=True)
                guardar_dades(df_final)
                st.success("Afegits correctament!")
                st.rerun()
    else:
        st.success("✅ Tot al dia (recurrents)")

    st.divider()
    
    if "ultim_moviment" in st.session_state:
        st.info("Últim afegit:")
        st.caption(st.session_state["ultim_moviment"])
        if st.button("Netejar avís"):
            del st.session_state["ultim_moviment"]
            st.rerun()
            
    st.divider()
    
    # FILTRES
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
Estructura: 'data' (YYYY-MM-DD), 'concepte' (Català), 'establiment', 'quantitat' (Negatiu=Despesa), 'categoria', 'tipus', 'es_periodic' (bool).
Si és tiquet llarg, separa items.
"""

# --- CALLBACK PER AL TEXT (AMB PROTECCIÓ D'ERROR) ---
def enviar_text_callback():
    text_a_processar = st.session_state.input_text_key
    
    if text_a_processar:
        try:
            res = model.generate_content([prompt_comu, text_a_processar])
            
            # PROTECCIÓ CONTRA RESPOSTES BUIDES/BLOQUEJADES
            if not res.parts:
                st.warning("⚠️ La IA no ha retornat text. Potser ha detectat contingut insegur o està saturada. Torna-ho a provar.")
                return

            txt = res.text.replace("```json", "").replace("```", "").strip()
            
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
            st.session_state.input_text_key = ""
            
        except ValueError:
             st.error("🤖 La IA ha bloquejat la resposta o ha fallat. Prova de reformular la frase.")
        except Exception as e:
            st.error(f"Error tècnic: {e}")

t1, t2, t3 = st.tabs(["📝 Text", "📸 Foto", "⚙️ Configurar Recurrents"])

with t1:
    st.text_area("Descriu moviments:", key="input_text_key", height=100, placeholder="Ex: Sopar ahir al Viena 45 euros")
    st.button("Enviar Text", on_click=enviar_text_callback)

with t2:
    im = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
    if st.button("Processar Foto") and im:
        with st.spinner("Processant..."):
            try:
                img_p = Image.open(im)
                res = model.generate_content([prompt_comu, "Extreu productes:", img_p])
                
                # PROTECCIÓ FOTO
                if not res.parts:
                    st.error("⚠️ No s'ha pogut llegir el tiquet (bloqueig de seguretat o error).")
                else:
                    txt = res.text.replace("```json", "").replace("```", "").strip()
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

with t3:
    st.info("ℹ️ Per afegir nous recurrents, has d'editar la funció `obtenir_configuracio_recurrents` al fitxer `app.py`. En futures versions ho farem des d'aquí!")
    st.code("""
    # Exemple del codi que pots editar:
    {"concepte": "Lloguer", "quantitat": -800.00, "dia": 5},
    {"concepte": "Netflix", "quantitat": -12.99, "dia": 15},
    """, language="python")
    st.write("Llistat actual configurat al codi:")
    st.table(pd.DataFrame(obtenir_configuracio_recurrents()))

# =================================================
# 2. DASHBOARD
# =================================================
st.divider()
if "ultim_moviment" in st.session_state:
    st.info(f"🚀 Últims moviments afegits:\n{st.session_state['ultim_moviment']}")

st.header("📊 Estat dels Comptes")

if not df_filtrat.empty:
    ingr = df_filtrat[df_filtrat['quantitat'] > 0]['quantitat'].sum()
    desp = df_filtrat[df_filtrat['quantitat'] < 0]['quantitat'].sum()
    saldo = df_filtrat['quantitat'].sum()
    # Despeses fixes reals (marcades al full)
    desp_fixes = df_filtrat[(df_filtrat['es_periodic'] == True) & (df_filtrat['quantitat'] < 0)]['quantitat'].sum()
else:
    ingr, desp, saldo, desp_fixes = 0.0, 0.0, 0.0, 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Ingressos", f"{ingr:.2f} €")
col2.metric("🔴 Despeses", f"{desp:.2f} €")
col3.metric("🔄 Despeses Fixes (Reals)", f"{desp_fixes:.2f} €")
col4.metric("📊 Saldo", f"{saldo:.2f} €")

if not df_filtrat.empty:
    tab_g, tab_d = st.tabs(["📉 Gràfics", "✏️ Edició"])
    with tab_g:
        c1, c2 = st.columns(2)
        with c1:
            df_g = df_filtrat.copy()
            df_g['valor_abs'] = df_g['quantitat'].abs()
            if not df_g.empty and df_g['valor_abs'].sum() > 0:
                fig = px.sunburst(df_g, path=['tipus', 'categoria', 'establiment'], values='valor_abs', 
                                color='tipus', color_discrete_map={'Despesa':'#EF553B', 'Ingrés':'#00CC96'})
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            ev = df_filtrat.groupby('data')['quantitat'].sum().reset_index()
            if not ev.empty:
                fig2 = px.bar(ev, x='data', y='quantitat', color='quantitat', color_continuous_scale=px.colors.diverging.RdYlGn)
                st.plotly_chart(fig2, use_container_width=True)
    with tab_d:
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