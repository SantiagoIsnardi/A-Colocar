"""
Página de Rendimiento: muestra qué tan bien viene acertando el modelo,
usando las predicciones ya resueltas contra resultados reales
(Brier Score, accuracy, CLV cuando hay cuota de cierre disponible).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
from components import api_client
from components.theme import inject_background
from components.display import render_result

st.set_page_config(page_title="Rendimiento", layout="wide")
inject_background()

st.title("Rendimiento del Modelo")
st.caption(
    "Compara las predicciones ya resueltas (partidos finalizados) contra el "
    "resultado real. Se actualiza una vez al día, junto con el resto del sync."
)

resumen = api_client.get_calibration_summary()

if resumen:
    if resumen.get("sample_size", 0) == 0:
        st.info(resumen.get("note", "Todavía no hay predicciones resueltas."))
    else:
        render_result(resumen)

        st.divider()
        st.markdown(
            """
            **Cómo leer esto:**
            - **Precisión del modelo** — más cerca de 0 es mejor (0 = predicción perfecta, 0.25 = tan bueno como tirar una moneda, 1 = siempre se equivocó con confianza).
            - **Aciertos** — de las predicciones donde el modelo dijo "más probable que sí" (≥50%), qué porcentaje se cumplió.
            - **Valor vs. cierre de mercado** — solo para las que tenían una apuesta de valor asociada con cuota de cierre disponible; positivo significa que conseguiste mejor cuota que el cierre del mercado (buena señal de que la apuesta tenía valor real, más allá de si ganó o perdió esa vez puntual).
            """
        )