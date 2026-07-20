"""Entrada de la interfaz grafica (PILOTO).

Deliberadamente separado de main.py: la app de consola es la que se distribuye
hoy y no debe verse afectada por este piloto. Cuando se decida si la GUI
reemplaza a la consola o convive con ella, esto se integra o se descarta.

Uso:  python salvagodinez_gui.py
"""

from gui.app import run
from main import __version__

if __name__ == "__main__":
    run(__version__)
