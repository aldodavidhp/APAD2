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
    page_title="Tutor Virtual - Formación DDAW",
    page_icon="🎓",
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
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .big-curp-input input {
        font-size: 1.2rem !important;
        padding: 12px 15px !important;
        height: 50px !important;
        width: 100% !important;
    }
    .email-result-container {
        background: linear-gradient(135deg, #2980b9 0%, #2c3e50 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1.5rem;
    }
    .tutor-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 5px solid #3498db;
    }
</style>
""", unsafe_allow_html=True)

# --- Cargar datos encriptados ---
@st.cache_data
def cargar_datos_curp():
    try:
        cipher = Fernet(st.secrets.db.encryption_key)
        datos_descifrados = cipher.decrypt(st.secrets.db.encrypted_data.encode())
        datos_dict = json.loads(datos_descifrados)
        
        # Conversión robusta a DataFrame
        if isinstance(datos_dict, dict):
            # Caso 1: Diccionario simple {CURP: email}
            if all(isinstance(v, str) for v in datos_dict.values()):
                return pd.DataFrame({
                    'CURP': list(datos_dict.keys()),
                    'email': list(datos_dict.values())
                })
            # Caso 2: Diccionario con estructura compleja
            else:
                return pd.DataFrame.from_dict(datos_dict, orient='index').reset_index()
        
        raise ValueError("Formato de datos no reconocido")
        
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=['CURP', 'email'])

df_curps = cargar_datos_curp()

# --- Validación de CURP Mexicano ---
def validar_curp_mexicano(curp):
    pattern = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2}$")
    return bool(pattern.match(curp))

# --- Leer PDF ---
def leer_pdf(ruta_pdf):
    try:
        with open(ruta_pdf, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e:
        st.error(f"Error al leer PDF: {str(e)}")
        return ""

# --- Carga inicial ---
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = leer_pdf("DDAW1.pdf")
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy tu tutor virtual de la formación DDAW. Puedes consultarme cualquier "
                      "duda sobre el material del curso. Si la información no está en los documentos, "
                      "te indicaré que consultes con tu tutor humano."
        }
    ]

# --- Interfaz Principal ---
st.markdown("""
<div class="header-gradient">
    <h1 style="margin:0;">Tutor Virtual - Formación DDAW</h1>
    <p style="margin:0;">Sistema de consulta académica y gestión de alumnos</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

# --- Columna de Chat ---
with col1:
    st.subheader("💬 Tutor Virtual")
    
    # Mostrar historial de chat
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.markdown(f'<div class="tutor-message">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.chat_message(msg["role"]).write(msg["content"])
    
    # Input de chat
    if prompt := st.chat_input("Escribe tu pregunta sobre la formación..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Contexto mejorado con instrucciones específicas
        contexto = f"""
        Eres un tutor virtual para la formación DDAW. 
        El documento proporcionado contiene el material del curso.
        
        INSTRUCCIONES:
        1. Responde ÚNICAMENTE con información que puedas encontrar en el documento
        2. Sé claro y conciso
        3. Si la pregunta no está relacionada con el curso, indica que solo puedes responder sobre la formación
        4. Si no encuentras la información, di que consultes al tutor humano
        
        DOCUMENTO:
        {st.session_state.pdf_text[:30000]}
        
        PREGUNTA:
        {prompt}
        """
        
        with st.spinner("Buscando en el material..."):
            try:
                response = model.generate_content(contexto)
                respuesta = response.text
            except Exception as e:
                respuesta = f"Error al procesar tu consulta: {str(e)}"
        
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        st.rerun()

# --- Columna de Búsqueda ---
with col2:
    st.subheader("📋 Buscador de Alumnos")
    
    st.markdown('<div class="big-curp-input">', unsafe_allow_html=True)
    curp = st.text_input(
        "Ingresa CURP del alumno:", 
        max_chars=18,
        placeholder="Ejemplo: PEMJ920313HDFLRN01",
        key="curp_input",
        label_visibility="collapsed"
    ).upper()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Buscar Correo", type="primary", use_container_width=True):
        if not curp:
            st.warning("Por favor ingresa un CURP")
        elif not validar_curp_mexicano(curp):
            st.error("Formato de CURP inválido")
        else:
            resultado = df_curps[df_curps['CURP'].str.upper() == curp]
            
            if not resultado.empty:
                email = resultado.iloc[0]['email']
                st.markdown(f"""
                <div class="email-result-container">
                    <div>Correo institucional:</div>
                    <div style="font-size:1.3rem; font-weight:bold; margin-top:0.5rem;">{email}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Alumno no encontrado")

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3976/3976626.png", width=100)
    st.title("Información")
    
    st.markdown("""
    ### Instrucciones:
    1. Haz preguntas sobre la formación
    2. Busca alumnos por CURP
    
    ### Características:
    - Respuestas basadas en el material oficial
    - Búsqueda segura de información
    """)
    
    if st.button("🔄 Reiniciar Conversación", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "¡Hola! Soy tu tutor virtual. ¿En qué puedo ayudarte hoy con la formación?"
            }
        ]
        st.rerun()
