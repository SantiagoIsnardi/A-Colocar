"""
Fondos visuales compartidos para las páginas de Streamlit.
- inject_background(): degradado CSS estilo césped, para las páginas internas.
- inject_home_background(): foto real de fondo, solo para Home.
Cada página llama a una de las dos, una vez, al principio del script.
"""

import base64
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def inject_background() -> None:
    """Degradado CSS estilo césped, sin imagen. Para las páginas internas."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(ellipse at top, rgba(57, 217, 138, 0.08), transparent 60%),
                repeating-linear-gradient(
                    135deg,
                    #0A140F,
                    #0A140F 40px,
                    #0C1712 40px,
                    #0C1712 80px
                );
            background-attachment: fixed;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_home_background() -> None:
    """
    Foto real de fondo (fronted/assets/background.jpg o .png) con tinte verdoso sutil,
    ajustada para cubrir toda la pantalla sin dejar franjas grises.
    """
    image_path = None
    for ext in ("jpg", "jpeg", "png"):
        candidate = ASSETS_DIR / f"background.{ext}"
        if candidate.exists():
            image_path = candidate
            break

    if image_path is None:
        inject_background()
        return

    mime = "png" if image_path.suffix == ".png" else "jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: #060c09 !important;
        }}

        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-image: 
                linear-gradient(rgba(6, 18, 12, 0.82), rgba(6, 18, 12, 0.82)),
                url("data:image/{mime};base64,{encoded}");
            /* 'cover' asegura que no haya franjas vacías. 
               'center center' prioriza el centro de la imagen al recortar los bordes excedentes */
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            filter: grayscale(80%) contrast(110%);
            pointer-events: none;
            z-index: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )