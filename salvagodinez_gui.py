"""Entrada directa a la interfaz grafica (atajo de desarrollo).

La GUI es la interfaz por default desde v2.5.0; el .exe la abre via main.py.
Este archivo es solo un atajo para lanzarla sin pasar por el menu de consola.

Uso:  python salvagodinez_gui.py
"""

from gui.app import run
from main import __version__

if __name__ == "__main__":
    run(__version__)
