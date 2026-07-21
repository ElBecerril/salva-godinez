"""Configuracion central: extensiones, rutas de autorecuperacion y constantes."""

import os

# Extensiones de archivos Excel y hojas de calculo
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv"}

# Extensiones de archivos Word
WORD_EXTENSIONS = {".docx", ".doc", ".docm", ".dotx", ".dotm", ".rtf"}

# Extensiones de archivos PowerPoint
POWERPOINT_EXTENSIONS = {".pptx", ".ppt", ".pptm", ".potx", ".ppsx"}

# Todas las extensiones de Office combinadas
OFFICE_EXTENSIONS = EXCEL_EXTENSIONS | WORD_EXTENSIONS | POWERPOINT_EXTENSIONS

# Extensiones de archivos temporales de Office
TEMP_PREFIXES = ("~$", "~")
TEMP_EXTENSIONS = {".tmp", ".xlk", ".wbk"}

# Rutas conocidas de autorecuperacion de Office
RECOVERY_PATHS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Excel"),
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Word"),
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "PowerPoint"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Office", "UnsavedFiles"),
    os.path.join(os.environ.get("TEMP", ""), ""),
]

# Ruta de archivos recientes de Windows
RECENT_PATH = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Recent"
)

# Dias para considerar un archivo como "reciente"
RECENT_DAYS = 30

# Segundos por dia (evitar magic number 86400)
SECONDS_PER_DAY = 86400

# Directorios del sistema a excluir en busquedas de disco
SKIP_DIRS = {"$Recycle.Bin", "System Volume Information", "Windows", "$WinREAgent", "Recovery"}

# ─── Fase 2: Constantes adicionales ─────────────────────────

# Respaldo rapido a USB: carpetas de origen
BACKUP_SOURCES = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]

# Liberador de espacio: rutas de archivos temporales
# Si falta alguna env var (LOCALAPPDATA/TEMP/SYSTEMROOT), os.path.join con
# base vacia produce una ruta RELATIVA peligrosa (disk_cleaner borra con
# estas rutas). Se filtran al final para excluir cualquier ruta no absoluta.
_TEMP_CLEAN_PATHS_RAW = [
    os.environ.get("TEMP", ""),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Temp"),
    os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "Windows", "INetCache",
    ),
]
TEMP_CLEAN_PATHS = [p for p in _TEMP_CLEAN_PATHS_RAW if os.path.isabs(p)]

# Cache de Windows Update
WINDOWS_UPDATE_CACHE = os.path.join(
    os.environ.get("SYSTEMROOT", r"C:\Windows"),
    "SoftwareDistribution", "Download",
)

# Descargas antiguas
DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
OLD_DOWNLOAD_DAYS = 30

# ─── Redes de El_Becerril ─────────────────────────────────────
# Fuente unica para el mensaje de apoyo al cerrar la app (lo usan la
# despedida de consola en main.py y la de ventanas en gui/despedida.py).
# (nombre, handle, url)
CANALES_APOYO = [
    ("YouTube", "@el_becerril", "https://www.youtube.com/@el_becerril"),
    ("Facebook", "El Becerril", "https://www.facebook.com/elbecerrilslim"),
]

# ─── Simulador de prestaciones — constantes laborales Mexico ──
# IMPORTANTE: Actualizar UMA cada febrero cuando el INEGI publique el nuevo valor.
# Fuente: https://www.inegi.org.mx/temas/uma/
AGUINALDO_MIN_DAYS = 15
UMA_DAILY = 117.31  # Valor diario vigente 2026 (actualizar anualmente)

# Salario minimo general diario vigente 2026 (zona general, resto del pais).
# Fuente: CONASAMI/DOF, resolucion publicada 09/12/2025, vigente desde el
# 01/01/2026 (incremento 13.0%: MIR 17.01 + 6.5% de fijacion).
# Art. 162/486 LFT usan este valor (NO la UMA) como tope para la prima de
# antiguedad.
SALARIO_MINIMO_DAILY = 315.04  # Vigente 2026 (zona general) - CONASAMI/DOF 09/12/2025

# Tabla de dias de vacaciones segun antiguedad, 1 a 20 anos (LFT 2023+, reforma
# de "vacaciones dignas")
VACATION_DAYS_TABLE = {
    1: 12,
    2: 14,
    3: 16,
    4: 18,
    5: 20,
    6: 22,
    7: 22,
    8: 22,
    9: 22,
    10: 22,
    11: 24,
    12: 24,
    13: 24,
    14: 24,
    15: 24,
    16: 26,
    17: 26,
    18: 26,
    19: 26,
    20: 26,
}

# Dias de vacaciones para antiguedad mayor a 20 anos (LFT Art. 76, reforma
# "vacaciones dignas" 2023): se suman 2 dias cada 5 anos adicionales,
# iniciando en 28 dias para el rango 21-25 (no 26, que corresponde a 16-20).
# (anio_inicio, anio_fin, dias)
VACATION_DAYS_RANGES_20PLUS = [
    (21, 25, 28),
    (26, 30, 30),
    (31, 35, 32),
    (36, 40, 34),
    (41, 45, 36),
    (46, 50, 38),
]

# ─── Retenciones de honorarios ────────────────────────────────
IVA_RATE = 0.16                 # Tasa IVA vigente
ISR_RETENTION_RATE = 0.10       # Retencion ISR sobre honorarios (Art. 106 LISR)
IVA_RETENTION_FRACTION = 2 / 3  # Fraccion del IVA retenida en honorarios

# ─── Fase 3: Constantes fiscales Mexico ──────────────────────

# Tabla ISR mensual Art. 96 LISR 2026 (Anexo 8 RMF 2026, DOF 28/12/2025)
# Factor de actualizacion 1.13213 (INPC nov-2025 / INPC nov-2022)
# (limite_inferior, limite_superior, cuota_fija, tasa_excedente)
ISR_MONTHLY_TABLE = [
    (0.01, 844.59, 0.00, 0.0192),
    (844.60, 7_168.51, 16.22, 0.0640),
    (7_168.52, 12_598.02, 420.95, 0.1088),
    (12_598.03, 14_644.64, 1_011.68, 0.16),
    (14_644.65, 17_533.64, 1_339.14, 0.1792),
    (17_533.65, 35_362.83, 1_856.84, 0.2136),
    (35_362.84, 55_736.68, 5_665.16, 0.2352),
    (55_736.69, 106_410.50, 10_457.09, 0.30),
    (106_410.51, 141_880.66, 25_659.23, 0.32),
    (141_880.67, 425_641.99, 37_009.69, 0.34),
    (425_642.00, float("inf"), 133_488.54, 0.35),
]

# Cuotas obrero IMSS (porcentajes sobre SBC salvo donde se indica)
IMSS_EMPLOYEE_RATES = {
    "enf_mat_excedente": 0.004,    # Enf. y Mat. excedente 3 UMA (prestaciones en especie)
    "enf_mat_dinero": 0.0025,      # Enf. y Mat. prestaciones en dinero
    "gastos_medicos": 0.00375,     # Gastos medicos pensionados
    "invalidez_vida": 0.00625,     # Invalidez y vida
    "cesantia_vejez": 0.01125,     # Cesantia en edad avanzada y vejez
}

# Tabla RESICO mensual personas fisicas (Art. 113-E LISR).
# IMPORTANTE: RESICO personas fisicas NO usa un modelo marginal (cuota fija +
# excedente); aplica una TASA FIJA sobre el INGRESO TOTAL del rango en el que
# cae el contribuyente. El campo "cuota_fija" se conserva por compatibilidad
# de forma con otras tablas de este archivo pero NO debe usarse en el calculo
# de RESICO (ver tools/retention_calculator.py, que aplica ingreso*tasa).
# (limite_inferior, limite_superior, cuota_fija_no_usada, tasa)
RESICO_MONTHLY_TABLE = [
    (0.01, 25_000.00, 0.00, 0.01),
    (25_000.01, 50_000.00, 0.00, 0.011),
    (50_000.01, 83_333.33, 0.00, 0.015),
    (83_333.34, 208_333.33, 0.00, 0.02),
    (208_333.34, float("inf"), 0.00, 0.025),
]

# ─── Vigencia de tablas fiscales ──────────────────────────────

# Anio para el cual se verificaron las tablas fiscales de este archivo
# (ISR_MONTHLY_TABLE, UMA_DAILY, RESICO_MONTHLY_TABLE, SALARIO_MINIMO_DAILY,
# etc.). Actualizar cada vez que se revisen contra las publicaciones
# oficiales del SAT/DOF/CONASAMI/INEGI.
TABLAS_VIGENTES_PARA_ANIO = 2026


def _warn_if_tables_outdated() -> None:
    """Aviso en tiempo de ejecucion (no bloqueante) si el anio del sistema ya
    no coincide con el anio para el que se verificaron las tablas fiscales."""
    import datetime

    current_year = datetime.date.today().year
    if current_year == TABLAS_VIGENTES_PARA_ANIO:
        return
    mensaje = (
        f"Aviso: las tablas fiscales (ISR, UMA, RESICO, salario minimo) de este "
        f"programa fueron verificadas para {TABLAS_VIGENTES_PARA_ANIO} y el "
        f"sistema marca el anio {current_year}. Revisa y actualiza config.py "
        "con los valores oficiales vigentes antes de confiar en los calculos."
    )
    try:
        from utils import console
        console.print(f"[bold yellow]{mensaje}[/bold yellow]")
    except Exception:
        import warnings
        warnings.warn(mensaje, stacklevel=2)


_warn_if_tables_outdated()
