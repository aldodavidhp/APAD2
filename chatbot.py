import streamlit as st
import PyPDF2
import google.generativeai as genai
import pandas as pd
import re
from pathlib import Path
from cryptography.fernet import Fernet
import json

# Configuración de la página (modo ancho)
st.set_page_config(
    page_title="ChatDoc + CURP Finder",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Configuración Gemini ---
genai.configure(api_key="AIzaSyAtsIgmN8GWnuy-tUhPIt9odwouOvMuujc")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Estilos CSS mejorados ---
st.markdown("""
<style>
    .header-gradient {
        background: linear-gradient(135deg, #6e48aa 0%, #9d50bb 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .curp-input input {
        font-size: 1.1rem !important;
        padding: 0.8rem !important;
        width: 100% !important;
        border: 2px solid #6e48aa !important;
    }
    .email-result {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 10px;
        margin-top: 1.5rem;
    }
    /* ... (otros estilos se mantienen igual) ... */
</style>
""", unsafe_allow_html=True)

# --- Función mejorada para cargar datos encriptados ---
@st.cache_data
def cargar_datos_curp():
    try:
        cipher = Fernet(st.secrets.db.encryption_key)
        datos_descifrados = cipher.decrypt(st.secrets.db.encrypted_data.encode())
        datos_dict = json.loads(datos_descifrados)
        
        # Convertir a formato adecuado para DataFrame
        if isinstance(datos_dict, dict):
            # Si los datos son {CURP: email}
            if all(isinstance(v, str) for v in datos_dict.values()):
                data = [{"CURP": k, "email": v} for k, v in datos_dict.items()]
            # Si los datos ya están en formato lista
            elif isinstance(next(iter(datos_dict.values())), dict):
                data = [{"CURP": k, **v} for k, v in datos_dict.items()]
            return pd.DataFrame(data)
        
        raise ValueError("Formato de datos no reconocido")
        
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=['CURP', 'email'])

df_curps = cargar_datos_curp()

# --- Validación de CURP Mexicano (mejorada) ---
def validar_curp_mexicano(curp):
    if not isinstance(curp, str) or len(curp) != 18:
        return False
    pattern = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$")
    return bool(pattern.match(curp))

# --- Lectura de PDF con manejo de errores mejorado ---
def leer_pdf(ruta_pdf):
    try:
        with open(ruta_pdf, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return "\n".join(
                page.extract_text() or f"<Página {i+1} sin texto>" 
                for i, page in enumerate(pdf_reader.pages)
            )
    except Exception as e:
        st.error(f"Error al leer PDF: {str(e)}")
        return ""

# --- Carga inicial del PDF ---
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = leer_pdf("APDAEMMA.pdf")

# --- Interfaz Principal ---
st.markdown("""
<div class="header-gradient">
    <h1 style="margin:0;">ChatDoc + CURP Finder</h1>
    <p style="margin:0;">Sistema integrado de consulta documental</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

# --- Columna de Chat ---
with col1:
    st.subheader("💬 Chat con Documento")
    
    # Historial de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
    
    # Input de chat
    if prompt := st.chat_input("Escribe tu pregunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            response = model.generate_content(
                f"Documento:\n{st.session_state.pdf_text[:30000]}\n\nPregunta: {prompt}"
            )
            respuesta = response.text
        except Exception as e:
            respuesta = f"⚠️ Error: {str(e)}"
        
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        st.rerun()

# --- Columna de Búsqueda ---
with col2:
    st.subheader("🔍 Buscador de CURP")
    
    st.markdown("""
    <style>
        .big-curp-input {
            width: 100% !important;
        }
        .big-curp-input input {
            font-size: 1.2rem !important;
            padding: 12px !important;
            height: 50px !important;
        }
    </style>
    """, unsafe_allow_html=True)    
    curp = st.text_input(
        "Ingresa CURP:", 
        max_chars=18,
        placeholder="Ej: PEMJ920313HDFLRN01",
        key="curp_input",
        label_visibility="collapsed"
    ).upper()
    st.markdown('<div class="big-curp-input"></div>', unsafe_allow_html=True)
    
    if st.button("Buscar", type="primary"):
        if not curp:
            st.warning("Ingresa un CURP")
        elif not validar_curp_mexicano(curp):
            st.error("CURP inválido")
        else:
            resultado = df_curps[df_curps['CURP'].str.upper() == curp]
            if not resultado.empty:
                email = resultado.iloc[0]['email']
                st.markdown(f"""
                <div class="email-result">
                    Correo encontrado:<br>
                    <strong>{email}</strong>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("CURP no encontrado")

# --- Sidebar ---
with st.sidebar:
    st.title("Configuración")
    if st.button("🧹 Limpiar Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.info("""
    ### Instrucciones:
    1. Chatea con el documento PDF
    2. Busca correos con CURP válidos
    """)

# --- Sección de desarrollo (solo visible localmente) ---
if st.secrets.get("db", {}).get("encryption_key") is None:
    if st.toggle("Mostrar herramientas de desarrollo"):
        st.warning("Esta sección solo es visible localmente")
        if st.button("Generar datos de ejemplo"):
            key = Fernet.generate_key()
            cipher = Fernet(key)
            data = {
                "XXXJ920313HDFLRN01": "ejemplo1@correo.com",
                "YYYG850621MDFMNS02": "ejemplo2@correo.com"
            }
            encrypted = cipher.encrypt(json.dumps(data).encode())
            st.code(f"""
            # secrets.toml
            [db]
            encryption_key = "{key.decode()}"
            encrypted_data = "{encrypted.decode()}"
            """)
