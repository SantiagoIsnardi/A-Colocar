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
    Foto real de fondo (fronted/assets/background.jpg o .png), con un
    overlay oscuro encima para que el texto siga siendo legible. Si no
    encuentra el archivo, cae de vuelta al degradado CSS.
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
            background:
                linear-gradient(rgba(6, 12, 9, 0.72), rgba(6, 12, 9, 0.72)),
                url("data:image/{mime};base64,{encoded}");
            background-size: 100% auto;
            background-position: center top;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )