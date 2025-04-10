import streamlit as st
import PyPDF2
import google.generativeai as genai
import pandas as pd
import re
from pathlib import Path
from cryptography.fernet import Fernet
import json

# Configuración de la página
st.set_page_config(
    page_title="Tutor Virtual - Formación",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Configuración Gemini ---
genai.configure(api_key="AIzaSyBZjKJOdxThOmcotZRX0on6uoJnGviyK7g")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Estilos CSS ---
st.markdown("""
<style>
    .header-gradient {
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .tutor-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 5px solid #3498db;
    }
    .pdf-warning {
        color: #e74c3c;
        font-weight: bold;
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
        
        if isinstance(datos_dict, dict):
            return pd.DataFrame({
                'CURP': list(datos_dict.keys()),
                'email': list(datos_dict.values())
            })
            
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
    return pd.DataFrame(columns=['CURP', 'email'])

df_curps = cargar_datos_curp()

# --- Validación de CURP ---
def validar_curp(curp):
    return bool(re.match(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]{2}$", curp))

# --- Leer PDF con verificación ---
def cargar_pdf(ruta_pdf):
    try:
        with open(ruta_pdf, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += f"--- Página {len(pdf_reader.pages)} ---\n{page_text}\n\n"
            return text
    except Exception as e:
        st.error(f"Error al cargar PDF: {str(e)}")
        return None

# --- Inicialización ---
if "pdf_text" not in st.session_state:
    pdf_content = cargar_pdf("APDAEMMA.pdf")
    if pdf_content is None:
        st.error("No se pudo cargar el documento PDF. Contacta al administrador.")
        st.stop()
    
    st.session_state.pdf_text = pdf_content
    st.session_state.messages = [{
        "role": "assistant",
        "content": "¡¡Hola! Soy un asistente virtual para el curso de Acoso escolar: prevención, detección y actuación."
                   "Puedes preguntarme cualquier duda sobre el curso."
                   "Mis respuestas se basarán estrictamente en todos los aspectos relacionados con esta formación."
    }]

# --- Interfaz Principal ---
st.markdown("""
<div class="header-gradient">
    <h1 style="margin:0;">Asistente virtual - Curso Acoso escolar: prevención, detección y actuación</h1>
    <p style="margin:0;"> </p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

# --- Columna de Chat ---
with col1:
    st.subheader("💬 Consulta la información")
    
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.markdown(f'<div class="tutor-message">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.chat_message(msg["role"]).write(msg["content"])
    
    if prompt := st.chat_input("Escribe tu pregunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Contexto estricto para Gemini
        contexto = f"""
        Eres un asistente académico especializado en responder preguntas sobre un documento específico.
        Documento actual: APDAEMMA.pdf
        Reglas estrictas:
        1. Responde EXCLUSIVAMENTE con información que puedas encontrar literalmente en el texto proporcionado
        2. Si la pregunta no puede responderse con el documento, di: "No cuento con esa respuesta. Por favor consulta a tu tutor."
        3. No inventes información bajo ninguna circunstancia
        4. No Cites la página
        
        CONTENIDO DEL DOCUMENTO:
        {st.session_state.pdf_text[:30000]}

        PREGUNTA DEL USUARIO:
        {prompt}
        """
        
        with st.spinner("Respondiendo..."):
            try:
                response = model.generate_content(
                    contexto,
                    generation_config={"temperature": 0.2}  # Reduce creatividad
                )
                respuesta = response.text
                
                # Verificación adicional
                if "no encuentro" in respuesta.lower() or "no aparece" in respuesta.lower():
                    respuesta = "No cuento con esa información. Por favor consulta con tu tutor."
                
            except Exception as e:
                respuesta = "Ocurrió un error al procesar tu consulta. Intenta nuevamente."
        
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        st.rerun()

# --- Columna de Búsqueda ---
with col2:
    st.subheader("📋Ingresa tu CURP para conocer con qué correo estás inscrito")
    
    curp = st.text_input(
        "Ingresa CURP:", 
        max_chars=18,
        placeholder="Ejemplo: PEMJ920313HDFLRN01",
        key="curp_input"
    ).upper()
    
    if st.button("Buscar", type="primary"):
        if not curp:
            st.warning("Ingresa un CURP válido")
        elif not validar_curp(curp):
            st.error("Formato de CURP incorrecto")
        else:
            resultado = df_curps[df_curps['CURP'].str.upper() == curp]
            if not resultado.empty:
                email = resultado.iloc[0]['email']
                st.success(f"Correo encontrado: {email}")
            else:
                st.error("No se encontró el CURP")

# --- Sidebar ---
with st.sidebar:
    st.title("ℹ️ Instrucciones")
    st.markdown("""
    1. Pregunta lo relacionado con la convocatoria Acoso escolar: Prevención, Detección y Actuación
    2. Si no encuentras/visualizas tu curso, revisa el correo con el que te inscribiste ingresando tu CURP en el panel derecho
    3. Cierre este panel, si deseas ver con mayor claridad la información
    """)
    
    if st.button("Reiniciar Chat"):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "¿En qué puedo ayudarte con el documento hoy?"
        }]
        st.rerun()
