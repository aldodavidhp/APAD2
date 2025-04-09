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

# Configuración de Gemini
genai.configure(api_key="AIzaSyAtsIgmN8GWnuy-tUhPIt9odwouOvMuujc")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Estilos CSS personalizados ---
st.markdown("""
<style>
    /* Estilo principal */
    .main {
        max-width: 1200px;
    }
    
    /* Campo CURP más amplio */
    .curp-input-container {
        width: 100% !important;
    }
    .curp-input input {
        font-size: 18px !important;
        padding: 15px !important;
        width: 100% !important;
    }
    
    /* Resto de estilos... */
    .header-gradient {
        background: linear-gradient(135deg, #6e48aa 0%, #9d50bb 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .chat-container {
        height: calc(100vh - 250px);
        overflow-y: auto;
        padding: 20px;
        background-color: #ffffff;
        border-radius: 15px;
        margin-right: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    /* ... (mantén los otros estilos igual) ... */
</style>
""", unsafe_allow_html=True)

# --- Cargar datos encriptados ---
@st.cache_data
def cargar_datos_curp():
    try:
        cipher = Fernet(st.secrets.db.encryption_key)
        datos_descifrados = cipher.decrypt(st.secrets.db.encrypted_data.encode())
        return pd.DataFrame(json.loads(datos_descifrados))
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame(columns=['CURP', 'email'])

df_curps = cargar_datos_curp()

# --- Validación de CURP Mexicano ---
def validar_curp_mexicano(curp):
    pattern = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2}$")
    return bool(pattern.match(curp))

# --- Leer PDF desde ubicación fija ---
def leer_pdf(ruta_pdf):
    try:
        with open(ruta_pdf, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return ""

# Ruta fija del PDF
RUTA_PDF = "APDAEMMA.pdf"

# Cargar el PDF al iniciar la aplicación
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = leer_pdf(RUTA_PDF)

# --- Estructura principal de la aplicación ---
st.markdown("""
<div class="header-gradient">
    <h1 style="color:white; margin:0;">ChatDoc + CURP Finder</h1>
    <p style="color:white; margin:0;">Sistema integrado de consulta documental y búsqueda por CURP</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

# Columna principal (chat)
with col1:
    st.markdown("### 💬 Chat con Documento")
    
    # Contenedor del chat
    chat_container = st.container()
    
    # Inicializar historial de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostrar mensajes en el contenedor
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"<div class='user-message'>{message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='assistant-message'>{message['content']}</div>", unsafe_allow_html=True)

    # Input del chat (posición fija)
    if prompt := st.chat_input("Escribe tu pregunta sobre el documento..."):
        if not st.session_state.pdf_text:
            st.error("No se pudo cargar el documento PDF")
        else:
            # Agregar mensaje del usuario
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Crear contexto con el PDF
            contexto = f"""
            Basándote estrictamente en el siguiente documento, responde la pregunta del usuario.
            Si la información no se encuentra en el documento, indica claramente que no está disponible.

            CONTENIDO DEL DOCUMENTO:
            {st.session_state.pdf_text[:30000]}

            PREGUNTA DEL USUARIO:
            {prompt}
            """
            
            # Obtener respuesta de Gemini
            with st.spinner("Procesando tu pregunta..."):
                try:
                    response = model.generate_content(contexto)
                    respuesta = response.text
                except Exception as e:
                    respuesta = f"Error al generar respuesta: {str(e)}"
            
            # Agregar respuesta al historial
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
            st.rerun()

# Columna lateral (búsqueda por CURP)
with col2:
    st.markdown("""
    <div class="curp-section">
        <h3>🔍 Buscador de CURP</h3>
        <p>Ingresa un CURP válido para encontrar el correo asociado</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Contenedor especial para el input más grande
    st.markdown('<div class="curp-input-container">', unsafe_allow_html=True)
    curp_buscar = st.text_input(
        "Ingresa el CURP:",
        max_chars=18,
        placeholder="Ejemplo: PEMJ920313HDFLRN01",
        key="curp_input",
        label_visibility="collapsed"
    ).strip().upper()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Buscar Correo", key="buscar_email"):
        if not curp_buscar:
            st.error("🚫 Por favor ingresa un CURP")
        elif not validar_curp_mexicano(curp_buscar):
            st.error("❌ Formato de CURP inválido para México")
        else:
            resultado = df_curps[df_curps['CURP'].str.upper() == curp_buscar]
            
            if not resultado.empty:
                email = resultado.iloc[0]['email']
                st.markdown(f"""
                <div class="email-result">
                    <i class="fas fa-envelope"></i> Correo encontrado:<br>
                    <code style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px;">{email}</code>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("🔍 No se encontró ningún registro con ese CURP")

# --- Sidebar con información adicional ---
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <h3>🤖 Sistema Integrado</h3>
        <p>Chat con documentos y búsqueda por CURP</p>
    </div>
    """)
    
    st.markdown("""
    ### 📋 Instrucciones
    1. **Chat con Documento**:
       - Haz preguntas sobre el contenido del PDF
       - Las respuestas se generan automáticamente
    
    2. **Buscador CURP**:
       - Ingresa un CURP válido mexicano
       - Recupera el correo asociado
    """)
    
    if st.button("🧹 Limpiar Chat", key="limpiar_chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- Para preparar los datos encriptados ---
# Ejecutar solo una vez localmente para generar los datos encriptados
if st.secrets.get("db", {}).get("encryption_key") is None and st.secrets.get("db", {}).get("encrypted_data") is None:
    if st.checkbox("Mostrar opciones de desarrollo (solo para administradores)"):
        if st.button("Generar datos encriptados de ejemplo"):
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            cipher = Fernet(key)
            
            # Datos de ejemplo
            data = {
                'CURP': ['PEMJ920313HDFLRN01', 'ROGG850621MDFMNS02', 'VACJ880430HDFLZP02'],
                'email': ['juan.perez@ejemplo.com', 'maria.garcia@ejemplo.com', 'carlos.lopez@ejemplo.com']
            }
            
            encrypted = cipher.encrypt(json.dumps(data).encode())
            
            st.code(f"""
            # Agrega esto a secrets.toml
            [db]
            encryption_key = "{key.decode()}"
            encrypted_data = "{encrypted.decode()}"
            """)
