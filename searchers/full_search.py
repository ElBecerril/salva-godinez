"""Orquestacion de la busqueda completa ("buscar en todos lados").

Corre siempre la misma secuencia, en el MISMO orden: papelera de reciclaje,
archivos temporales/autorecuperacion, recientes de Windows, disco completo
y copias de seguridad (shadow copies); al final deduplica por ruta.

Este modulo no tiene UI (nada de console.print, Prompt, rich ni tkinter):
tanto la consola (main.py) como la GUI (gui/panels/rescate.py) llaman a
`search_everywhere()` y presentan el resultado a su manera. El avance se
reporta por dos callbacks opcionales, ninguno de los dos imprime nada:

- `progress_callback(texto)`: mismo contrato que `search_by_name`, se usa
  para el avance fino del escaneo de disco (archivo por archivo).
- `stage_callback(etapa, cantidad)`: se llama DOS veces por etapa. Con
  `cantidad=None` cuando la etapa EMPIEZA, y con el numero de resultados
  crudos (antes de deduplicar) cuando TERMINA. `etapa` es una clave interna
  estable (ver abajo) para que cada interfaz elija su propio texto sin que
  este modulo sepa nada de UI.

  El aviso de inicio existe para que las interfaces NO tengan que saber que
  etapa viene despues de cual. Si solo se avisara al terminar, cada interfaz
  tendria que anunciar la etapa siguiente desde el callback de la anterior, y
  el ORDEN quedaria codificado tambien alla — que es justo la duplicacion que
  este modulo vino a eliminar. Aqui el orden se define una sola vez.
"""

from searchers.disk_search import search_by_name
from searchers.recent_files import search_recent_files
from searchers.recycle_bin import search_recycle_bin
from searchers.shadow_copies import search_shadow_copies
from searchers.temp_files import search_temp_files
from utils import deduplicate

# Claves estables de cada etapa, en el orden en que se ejecutan. Las
# interfaces (consola, GUI) las usan para mapear a su propio texto.
ETAPA_PAPELERA = "papelera"
ETAPA_TEMPORALES = "temporales"
ETAPA_RECIENTES = "recientes"
ETAPA_DISCO = "disco"
ETAPA_SHADOW = "shadow"


def search_everywhere(name: str, progress_callback=None, stage_callback=None) -> list[dict]:
    """Busca `name` en todos lados, en el mismo orden que usaban antes por
    separado main.py y gui/panels/rescate.py.

    Args:
        name: texto parcial del nombre del archivo a buscar.
        progress_callback: opcional, recibe la ruta actual durante el
            escaneo de disco completo (igual que search_by_name).
        stage_callback: opcional, recibe (etapa, None) al empezar cada etapa y
            (etapa, cantidad) al terminarla, con los resultados crudos de esa
            etapa (antes de deduplicar el total).

    Returns:
        Lista de resultados de todas las etapas, deduplicados por ruta.
    """
    todos: list[dict] = []

    def _avisar(etapa: str, cantidad=None) -> None:
        if stage_callback:
            stage_callback(etapa, cantidad)

    # La secuencia se define UNA sola vez, aqui. search_by_name es la unica que
    # acepta progress_callback (es la lenta, la que recorre el disco).
    secuencia = (
        (ETAPA_PAPELERA, search_recycle_bin, False),
        (ETAPA_TEMPORALES, search_temp_files, False),
        (ETAPA_RECIENTES, search_recent_files, False),
        (ETAPA_DISCO, search_by_name, True),
        (ETAPA_SHADOW, search_shadow_copies, False),
    )

    for etapa, buscador, acepta_progreso in secuencia:
        _avisar(etapa)
        if acepta_progreso:
            resultados = buscador(name, progress_callback=progress_callback)
        else:
            resultados = buscador(name)
        todos.extend(resultados)
        _avisar(etapa, len(resultados))

    return deduplicate(todos)
