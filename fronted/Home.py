"""
Página principal. Muestra un resumen del estado del backend y navegación
a las secciones principales.
"""

import httpx
import streamlit as st

from components.api_client import BASE_URL

st.set_page_config(
    page_title="A Colocar",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ A Colocar")
st.caption(f"🔧 Debug: conectando a {BASE_URL}")
st.caption("Análisis estadístico y detección de valor en mercados de fútbol")

# Verificar conexión con el backend
try:
    response = httpx.get("http://localhost:8000/health", timeout=5.0)
    health = response.json()
    if health.get("database") == "connected":
        st.success(f"✅ Backend conectado — {health.get('app')} ({health.get('environment')})")
    else:
        st.warning("⚠️ Backend responde pero la base de datos no está conectada")
except Exception:
    st.error("❌ No se pudo conectar al backend. Verificá que `uvicorn` esté corriendo en el puerto 8000.")

st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.page_link("pages/1_Buscar_Partido.py", label="🔍 Buscar Partido", use_container_width=True)
with col2:
    st.page_link("pages/2_Predicciones.py", label="📊 Predicciones", use_container_width=True)
with col3:
    st.page_link("pages/3_Apuestas_de_Valor.py", label="💰 Apuestas de Valor", use_container_width=True)
with col4:
    st.page_link("pages/4_Rankings.py", label="🏆 Rankings", use_container_width=True)

st.divider()
st.markdown(
    """
    ### Cómo usar esta herramienta

    1. **Buscar Partido** — encontrá el `match_id` del partido que te interesa.
    2. **Predicciones** — generá y consultá probabilidades por línea, para goles y otros mercados.
    3. **Value Bets** — compará esas probabilidades contra cuotas reales de mercado.
    4. **Rankings** — mirá las mejores oportunidades detectadas en toda tu base de datos.
    """
)