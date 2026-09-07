"""
Truco: pasar un nombre de liga inválido a propósito. ScraperFC está
diseñado para, en ese caso, listar todos los nombres válidos disponibles
en el error — así vemos los nombres exactos de las ligas europeas.
"""

import ScraperFC as sfc

def main():
    sofascore = sfc.Sofascore()
    try:
        sofascore.get_valid_seasons("NOMBRE_INVALIDO_A_PROPOSITO")
    except Exception as ex:
        print(f"{type(ex).__name__}: {ex}")


if __name__ == "__main__":
    main()