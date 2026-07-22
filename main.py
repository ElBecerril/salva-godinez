"""
Salva Godinez — Navaja suiza para oficinistas
by El_Becerril

Toolkit multi-modulo para rescate de archivos, mantenimiento
de impresoras, diagnostico del sistema y mas.
"""

__version__ = "2.6.1"

import sys
import os
import webbrowser

# Agregar el directorio del script al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.panel import Panel
from rich.prompt import Prompt
from rich.markup import escape
from rich import box

# Searchers (modulo de rescate de archivos Office)
from searchers.recycle_bin import search_recycle_bin
from searchers.disk_search import search_by_name, search_recent_excel
from searchers.temp_files import search_temp_files
from searchers.recent_files import search_recent_files
from searchers.shadow_copies import search_shadow_copies
from searchers.full_search import (
    search_everywhere,
    ETAPA_PAPELERA,
    ETAPA_TEMPORALES,
    ETAPA_RECIENTES,
    ETAPA_DISCO,
    ETAPA_SHADOW,
)
from reporting.console_report import show_results, offer_restore

# Tools — Fase 1
from tools.spooler import reset_spooler
from tools.system_info import show_system_info
from tools.usb_disinfect import usb_disinfect_menu
from tools.pdf_tools import pdf_menu
from tools.wifi_passwords import show_wifi_passwords
from tools.password_generator import password_generator_menu

# Tools — Fase 2
from tools.excel_cell_cleaner import cell_cleaner_menu
from tools.excel_consolidator import consolidator_menu
from tools.excel_comparator import comparator_menu
from tools.file_unlocker import file_unlocker_menu
from tools.ghost_printers import ghost_printers_menu
from tools.ping_checker import ping_checker_menu
from tools.usb_health import usb_health_menu
from tools.usb_backup import usb_backup_menu
from tools.disk_cleaner import disk_cleaner_menu
from tools.prestaciones_sim import prestaciones_menu

# Tools — Fase 3
from tools.usb_eject import usb_eject_menu
from tools.net_drive import net_drive_menu
from tools.image_converter import image_converter_menu
from tools.printer_share import printer_share_menu
from tools.salary_calculator import salary_calculator_menu
from tools.retention_calculator import retention_calculator_menu
from tools.updater import check_for_updates
from utils import console, asegurar_consola_texto
from config import CANALES_APOYO


BANNER = r"""[bold cyan]
              ( (
               ) )
            .-------.
            |       |]
            \       /
             `-----'

  ____        _              ____          _ _
 / ___|  __ _| |_   ____ _  / ___| ___   __| (_)_ __   ___ ____
 \___ \ / _` | \ \ / / _` || |  _ / _ \ / _` | | '_ \ / _ \_  /
  ___) | (_| | |\ V / (_| || |_| | (_) | (_| | | | | |  __// /
 |____/ \__,_|_| \_/ \__,_| \____|\___/ \__,_|_|_| |_|\___/___|

  [bold white]La navaja suiza para sobrevivir la oficina[/bold white]
  [dim]by El_Becerril - v{version}[/dim]
[/bold cyan]"""


# ─── Menu principal ───────────────────────────────────────────

def show_main_menu() -> str:
    console.print(BANNER.format(version=__version__))
    console.print(
        Panel(
            "[bold]1[/bold] - Recuperar y arreglar archivos (Word/Excel)\n"
            "[bold]2[/bold] - Arreglar impresoras\n"
            "[bold]3[/bold] - USB, WiFi y Red\n"
            "[bold]4[/bold] - Limpieza y mantenimiento\n"
            "[bold]5[/bold] - Calculadoras y herramientas\n"
            "[bold]6[/bold] - Volver a la version con ventanas\n"
            "[bold]0[/bold] - Salir",
            title="[bold yellow]Menu Principal[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("\n[bold cyan]Selecciona una opcion[/bold cyan]", default="0")


# ─── Sub-menu 1: Recuperar y arreglar archivos (Word/Excel) ──────────────────────

def show_office_submenu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Recuperar archivos perdidos\n"
            "[bold]2[/bold] - Quitar espacios que rompen formulas\n"
            "[bold]3[/bold] - Unir varios Excel en uno\n"
            "[bold]4[/bold] - Comparar dos archivos de Excel\n"
            "[bold]5[/bold] - Desbloquear archivo en uso\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Recuperar y arreglar archivos (Word/Excel)[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")


def office_menu() -> None:
    while True:
        choice = show_office_submenu()

        if choice == "1":
            office_rescue_menu()
        elif choice == "2":
            cell_cleaner_menu()
        elif choice == "3":
            consolidator_menu()
        elif choice == "4":
            comparator_menu()
        elif choice == "5":
            file_unlocker_menu()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("2", "3", "4", "5"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Sub-menu 2: Arreglar impresoras ──────────────────────

def show_printers_submenu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Destrabar impresora atascada\n"
            "[bold]2[/bold] - Quitar impresoras duplicadas\n"
            "[bold]3[/bold] - Probar si la impresora responde\n"
            "[bold]4[/bold] - Compartir impresora en red\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Arreglar impresoras[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")


def printers_menu() -> None:
    while True:
        choice = show_printers_submenu()

        if choice == "1":
            reset_spooler()
        elif choice == "2":
            ghost_printers_menu()
        elif choice == "3":
            ping_checker_menu()
        elif choice == "4":
            printer_share_menu()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("1", "2", "3", "4"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Sub-menu 3: USB, WiFi y Red ───────────────────────

def show_usb_net_submenu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Quitar virus de la USB\n"
            "[bold]2[/bold] - Revisar estado de la USB\n"
            "[bold]3[/bold] - Respaldar archivos a USB\n"
            "[bold]4[/bold] - Ver contrasenas WiFi guardadas\n"
            "[bold]5[/bold] - Expulsar USB con seguridad\n"
            "[bold]6[/bold] - Conectar carpetas de red\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]USB, WiFi y Red[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")


def usb_net_menu() -> None:
    while True:
        choice = show_usb_net_submenu()

        if choice == "1":
            usb_disinfect_menu()
        elif choice == "2":
            usb_health_menu()
        elif choice == "3":
            usb_backup_menu()
        elif choice == "4":
            show_wifi_passwords()
        elif choice == "5":
            usb_eject_menu()
        elif choice == "6":
            net_drive_menu()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("1", "2", "3", "4", "5"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Sub-menu 4: Limpieza y mantenimiento ───────────────────────

def show_system_submenu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Ver datos del equipo (nombre e IP)\n"
            "[bold]2[/bold] - Liberar espacio en disco\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Limpieza y mantenimiento[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")


def system_menu() -> None:
    while True:
        choice = show_system_submenu()

        if choice == "1":
            show_system_info()
        elif choice == "2":
            disk_cleaner_menu()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("1", "2"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Sub-menu 5: Utilidades ──────────────────────────────────

def show_utilities_submenu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Editar PDF (unir, dividir, proteger)\n"
            "[bold]2[/bold] - Generar contrasenas seguras\n"
            "[bold]3[/bold] - Calcular finiquito y prestaciones\n"
            "[bold]4[/bold] - Convertir imagenes (JPG, PNG, etc.)\n"
            "[bold]5[/bold] - Calcular sueldo neto\n"
            "[bold]6[/bold] - Retenciones de honorarios\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Calculadoras y herramientas[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")


def utilities_menu() -> None:
    while True:
        choice = show_utilities_submenu()

        if choice == "1":
            pdf_menu()
        elif choice == "2":
            password_generator_menu()
        elif choice == "3":
            prestaciones_menu()
        elif choice == "4":
            image_converter_menu()
        elif choice == "5":
            salary_calculator_menu()
        elif choice == "6":
            retention_calculator_menu()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        if choice in ("2", "4", "5"):
            Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# ─── Sub-menu: Buscar archivos de Office perdidos ──────────────────

def show_office_rescue_menu() -> str:
    console.print(
        Panel(
            "[bold]1[/bold] - Buscar mi archivo por nombre  [green](recomendado)[/green]\n"
            "[bold]2[/bold] - Ver todos los Office recientes (ultimos 30 dias)\n"
            "\n"
            "[dim]Busqueda avanzada (revisar un solo lugar):[/dim]\n"
            "[bold]3[/bold] - Solo en la Papelera de reciclaje\n"
            "[bold]4[/bold] - Solo en temporales / autorecuperacion\n"
            "[bold]5[/bold] - Solo en archivos recientes de Windows\n"
            "[bold]0[/bold] - Volver",
            title="[bold yellow]Buscar archivos de Office perdidos[/bold yellow]",
            box=box.ROUNDED,
        )
    )
    return Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="1")


def ask_name() -> str:
    """Pide el nombre a buscar. Reintenta si esta vacio; '0' cancela."""
    while True:
        name = Prompt.ask(
            "[bold]Nombre (o parte del nombre) del archivo[/bold] "
            "[dim](o 0 para volver)[/dim]"
        ).strip()
        if name == "0":
            return ""
        if name:
            return name
        console.print(
            "[yellow]Escribe al menos una parte del nombre, o 0 para volver.[/yellow]"
        )


def option_recent_office() -> None:
    console.print("[bold yellow]Buscando archivos Office de los ultimos 30 dias...[/bold yellow]")
    with console.status("[bold green]Escaneando discos...") as status:
        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {escape(display)}")
        results = search_recent_excel(progress_callback=progress)

    show_results(results, title="Archivos Office recientes (ultimos 30 dias)")
    offer_restore(results)


def option_recycle_bin() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Revisando papelera de reciclaje..."):
        results = search_recycle_bin(name)
    show_results(results, title="Archivos Office en la Papelera")
    offer_restore(results)


def option_temp_files() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Buscando archivos temporales y de autorecuperacion..."):
        results = search_temp_files(name)
    show_results(results, title="Archivos Temporales / Autorecuperacion")
    offer_restore(results)


def option_recent_windows() -> None:
    name = Prompt.ask(
        "[bold]Filtrar por nombre (dejar vacio para ver todos)[/bold]", default=""
    )
    with console.status("[bold green]Revisando archivos recientes de Windows..."):
        results = search_recent_files(name)
    show_results(results, title="Archivos Recientes de Windows")
    offer_restore(results)


def option_full_search() -> None:
    name = ask_name()
    if not name:
        return

    # La secuencia (que se busca, en que orden, deduplicacion final) vive en
    # searchers/full_search.py y es compartida con la GUI. Aca solo se traduce
    # cada etapa al texto que esta pantalla siempre mostro. Ojo: este mapa NO
    # sabe que etapa va despues de cual — ese orden lo decide full_search.py y
    # solo el.
    ETIQUETAS = {
        ETAPA_PAPELERA: "Papelera de reciclaje",
        ETAPA_TEMPORALES: "Archivos temporales / autorecuperacion",
        ETAPA_RECIENTES: "Archivos recientes de Windows",
        ETAPA_DISCO: "discos",
        ETAPA_SHADOW: "copias de seguridad",
    }
    # Etapas que ademas anuncian su inicio en grande porque tardan mucho y el
    # usuario podria creer que la app se colgo.
    AVISOS_LARGOS = {
        ETAPA_DISCO: "Escaneando todos los discos...",
        ETAPA_SHADOW: (
            "Buscando en las copias de seguridad automaticas de Windows, "
            "esto puede tardar varios minutos..."
        ),
    }

    with console.status("[bold green]Buscando...") as status:

        def progress(path):
            display = path if len(path) < 60 else "..." + path[-57:]
            status.update(f"[bold green]Escaneando:[/bold green] {escape(display)}")

        def on_stage(etapa: str, count, resultados=None) -> None:
            etiqueta = ETIQUETAS.get(etapa, etapa)
            if count is None:
                if etapa in AVISOS_LARGOS:
                    console.print(f"[bold yellow]{AVISOS_LARGOS[etapa]}[/bold yellow]")
                status.update(f"[bold green]Buscando en {etiqueta}...")
            elif count:
                console.print(f"  [green]+{count}[/green] encontrado(s) en {etiqueta}")

        all_results = search_everywhere(
            name, progress_callback=progress, stage_callback=on_stage
        )

    console.print()
    show_results(all_results, title=f"Busqueda completa para '{escape(name)}'")
    offer_restore(all_results)


def office_rescue_menu() -> None:
    """Sub-menu de rescate de archivos Office."""
    while True:
        choice = show_office_rescue_menu()

        if choice == "1":
            option_full_search()
        elif choice == "2":
            option_recent_office()
        elif choice == "3":
            option_recycle_bin()
        elif choice == "4":
            option_temp_files()
        elif choice == "5":
            option_recent_windows()
        elif choice == "0":
            break
        else:
            console.print("[red]Opcion no valida.[/red]")

        Prompt.ask("\n[dim]Presiona Enter para continuar[/dim]", default="")


# Mapea la opcion del menu (1, 2, ...) a (nombre, url), derivado de la fuente
# unica en config.CANALES_APOYO para no repetir las URLs (las usa tambien la
# despedida de la GUI en gui/despedida.py).
CHANNELS = {
    str(i): (nombre, url)
    for i, (nombre, _handle, url) in enumerate(CANALES_APOYO, start=1)
}


def show_farewell() -> None:
    console.print()
    lineas_redes = "\n".join(
        f"[bold]{i}[/bold] - {nombre}  ({handle})"
        for i, (nombre, handle, _url) in enumerate(CANALES_APOYO, start=1)
    )
    console.print(
        Panel(
            "[bold yellow]Te sirvio Salva Godinez?[/bold yellow]\n\n"
            "Esta herramienta es [bold]100% gratis[/bold]. Si quieres apoyar\n"
            "su desarrollo, ver mis videos me ayuda muchisimo.\n\n"
            f"{lineas_redes}\n"
            "[bold]0[/bold] - Cerrar",
            title="[bold cyan]Gracias por usar Salva Godinez![/bold cyan]",
            box=box.ROUNDED,
        )
    )
    choice = Prompt.ask("[bold cyan]Opcion[/bold cyan]", default="0")
    if choice in CHANNELS:
        name, url = CHANNELS[choice]
        console.print(f"[bold green]Abriendo {name}...[/bold green]")
        webbrowser.open(url)
    console.print("[bold cyan]Hasta luego![/bold cyan]")


# ─── Main ─────────────────────────────────────────────────────

def _show_source_notice() -> None:
    """Aviso unico al arrancar sobre el unico origen legitimo de descarga, para
    que el usuario no caiga con un clon/impostor que distribuya un .exe
    malicioso con el mismo nombre."""
    console.print(
        Panel(
            "[bold]Descarga segura.[/bold] SalvaGodinez solo es oficial si lo "
            "bajaste de:\n"
            "[bold cyan]github.com/ElBecerril/salva-godinez[/bold cyan]\n"
            "[dim]Si lo conseguiste en otra pagina, grupo o link, borralo: puede ser "
            "una copia falsa con virus.[/dim]",
            title="[bold green]Origen oficial[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def abrir_gui() -> str:
    """Abre la version con ventanas. Devuelve "salir", "consola" o "fallo".

    El .exe se compila como app de VENTANA (console=False): al arrancar NO hay
    consola negra que esconder. El truco viejo (compilar como consola y
    esconderla con ShowWindow) ya NO funciona en Windows 11 — la consola la
    hospeda Windows Terminal, que ignora el hide, y la ventana negra quedaba
    detras de la GUI. Ahora no se crea ninguna.

    Si tkinter falta o la ventana truena, se devuelve "fallo" y main.py cae a
    modo texto, que crea su propia consola on-demand. El import va adentro a
    proposito: es el respaldo si la GUI no abre en esa maquina.
    """
    try:
        from gui.app import run as run_gui
        return run_gui(__version__)
    except Exception:
        # Sin consola no hay donde imprimir; se registra en el log para
        # diagnostico y se cae a modo texto (el fallback crea la consola).
        _registrar_error_gui()
        return "fallo"


def _registrar_error_gui() -> None:
    """Guarda en salva_error.log el motivo de que la GUI no abriera."""
    import traceback
    try:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "salva_error.log"), "a", encoding="utf-8") as f:
            f.write("\n--- No se pudo abrir la version con ventanas ---\n")
            traceback.print_exc(file=f)
    except OSError:
        pass


def arranque_comun() -> None:
    """Lo que debe pasar SIEMPRE al abrir la app, sea con ventanas o con texto.

    OJO: esto vivia dentro de main(), que es el camino de la CONSOLA. Cuando la
    interfaz grafica paso a ser la que abre por default, main() dejo de correr
    en el caso normal y se perdieron dos cosas sin que nadie lo notara: el
    aviso de actualizaciones y la advertencia de origen oficial (que existe
    para que nadie use un clon con virus). Por eso ahora vive aparte y se llama
    ANTES de decidir que interfaz abrir.

    Corre con la consola todavia visible, asi que el "hay version nueva,
    la descargo?" se puede contestar aunque despues se abra la ventana.
    """
    check_for_updates(__version__)
    _show_source_notice()


def main() -> None:
    try:
        while True:
            choice = show_main_menu()

            if choice == "1":
                office_menu()
            elif choice == "2":
                printers_menu()
            elif choice == "3":
                usb_net_menu()
            elif choice == "4":
                system_menu()
            elif choice == "5":
                utilities_menu()
            elif choice == "6":
                # Si el usuario cierra la ventana para SALIR, no reaparecer el
                # menu de texto (la GUI ya mostro su despedida). "consola"/
                # "fallo" si regresan al menu.
                if abrir_gui() == "salir":
                    break
            elif choice == "0":
                show_farewell()
                break
            else:
                console.print("[red]Opcion no valida.[/red]")
    except KeyboardInterrupt:
        console.print()
        show_farewell()


if __name__ == "__main__":
    try:
        # Por default abre la interfaz grafica: la gente que hace doble clic a
        # un programa espera una ventana, no un menu de texto. Se comprobo en
        # uso real — al publicar la GUI como opcion del menu, los usuarios
        # nuevos ni la encontraron.
        #
        # El modo texto NO desaparece: se llega con --consola, con el boton
        # "Volver al modo texto" de la ventana, y automaticamente si la
        # interfaz grafica no se puede abrir en esa maquina.
        #
        # El arranque (revisar version nueva + aviso de origen oficial) corre
        # en la interfaz ACTIVA, no antes de elegirla: en consola lo hace
        # arranque_comun (texto); con ventanas lo hace la propia GUI como
        # dialogos (gui/actualizacion). Asi la consola negra se esconde de una
        # en vez de quedar visible mientras se contesta "hay version nueva?" —
        # que era justo lo que se veia poco confiable al arrancar.
        if "--consola" in sys.argv:
            asegurar_consola_texto()  # el .exe es app de ventana; crear consola
            arranque_comun()
            main()
        else:
            resultado = abrir_gui()  # app de ventana: abre limpia, sin consola
            if resultado == "fallo":
                # La ventana no pudo abrir: nunca mostro esos dialogos. Se cae a
                # consola (que hay que crear) y el arranque de texto se hace aqui.
                asegurar_consola_texto()
                arranque_comun()
                main()
            elif resultado == "consola":
                # El usuario pidio modo texto DESPUES de que la GUI ya mostro
                # origen/updates; no se repite el arranque, pero si hace falta la
                # consola.
                asegurar_consola_texto()
                main()
            # "salir": termina.
    except Exception:
        import traceback
        # Guardar traceback completo en archivo para diagnostico.
        # OJO: en el .exe de PyInstaller, __file__ apunta a la carpeta temporal
        # donde se descomprime la app, y Windows la BORRA al cerrar — el log se
        # perdia justo cuando hacia falta. Congelado hay que usar sys.executable,
        # que si es el .exe donde el usuario lo puede encontrar.
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base_dir, "salva_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except OSError:
            log_path = None
        # El .exe es app de ventana: para mostrar el error hace falta una consola.
        asegurar_consola_texto()
        console.print("\n[bold red]Ocurrio un error inesperado.[/bold red]")
        if log_path:
            console.print(f"[dim]Detalles guardados en: {log_path}[/dim]")
        input("\nPresiona Enter para cerrar...")
