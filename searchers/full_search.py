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
- `stage_callback(etapa, cantidad, resultados=None)`: se llama DOS veces por
  etapa. Al EMPEZAR: `cantidad=None` y `resultados` no se manda (queda en su
  default `None`). Al TERMINAR: `cantidad` es el numero de resultados crudos
  de esa etapa (antes de deduplicar, para no romper el "+N encontrado(s)" que
  ya imprimia la consola) y `resultados` es la lista de esa etapa YA
  deduplicada de forma incremental contra todo lo visto en etapas anteriores
  (y contra si misma) — lista lista para pintarse en pantalla sin mostrar
  filas repetidas. `etapa` es una clave interna estable (ver abajo) para que
  cada interfaz elija su propio texto sin que este modulo sepa nada de UI.

  El aviso de inicio existe para que las interfaces NO tengan que saber que
  etapa viene despues de cual. Si solo se avisara al terminar, cada interfaz
  tendria que anunciar la etapa siguiente desde el callback de la anterior, y
  el ORDEN quedaria codificado tambien alla — que es justo la duplicacion que
  este modulo vino a eliminar. Aqui el orden se define una sola vez.

  La deduplicacion final (el `return`) ya no hace falta correrla aparte: se
  va acumulando incrementalmente etapa por etapa, en el mismo orden que
  produce `deduplicate()` sobre la lista completa concatenada (primera
  aparicion de cada ruta gana). El resultado es identico, solo que calculado
  en el camino en vez de al final.
"""

from searchers.disk_search import search_by_name
from searchers.recent_files import search_recent_files
from searchers.recycle_bin import search_recycle_bin
from searchers.shadow_copies import search_shadow_copies
from searchers.temp_files import search_temp_files

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
        stage_callback: opcional, recibe (etapa, None) al empezar cada etapa
            y (etapa, cantidad, resultados) al terminarla. `cantidad` es el
            total crudo de esa etapa (antes de deduplicar); `resultados` es
            la porcion NUEVA de esa etapa ya deduplicada contra todo lo
            visto antes (ver docstring del modulo).

    Returns:
        Lista de resultados de todas las etapas, deduplicados por ruta (el
        mismo conjunto, en el mismo orden, que antes producia
        `deduplicate()` aplicado al final).
    """
    todos: list[dict] = []
    vistos: set[str] = set()

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
        if stage_callback:
            stage_callback(etapa, None)

        if acepta_progreso:
            crudos = buscador(name, progress_callback=progress_callback)
        else:
            crudos = buscador(name)

        # Dedup incremental: solo lo que no se habia visto en una etapa
        # anterior (ni antes, dentro de esta misma) se agrega y se muestra.
        # Recorrer en orden y usar un set de rutas ya vistas produce
        # exactamente lo mismo que deduplicate() al final sobre la lista
        # concatenada completa (gana la primera aparicion de cada ruta).
        nuevos = []
        for r in crudos:
            # Preferir la ruta FISICA (unica por item) cuando exista: la
            # papelera de reciclaje pone "Desconocida" en "ruta" para todo
            # archivo borrado sin carpeta original registrada, y usar ese
            # valor como clave colapsaba todos esos items en uno solo,
            # descartando en silencio los demas (ver recycle_bin.py,
            # campo "ruta_fisica"). Con "ruta_fisica" como clave preferente
            # cada item borrado tiene su propia clave unica dentro de
            # $Recycle.Bin, y el dedup legitimo (mismo archivo real, misma
            # "ruta") se mantiene igual para el resto de las etapas, que no
            # traen "ruta_fisica".
            clave = r.get("ruta_fisica") or r.get("ruta", "")
            if clave not in vistos:
                vistos.add(clave)
                nuevos.append(r)
        todos.extend(nuevos)

        if stage_callback:
            stage_callback(etapa, len(crudos), nuevos)

    return todos
