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

# ─── Fase 2: Constantes adicionales ─────────────────────────

# Respaldo rapido a USB: carpetas de origen
BACKUP_SOURCES = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]

# Liberador de espacio: rutas de archivos temporales
TEMP_CLEAN_PATHS = [
    os.environ.get("TEMP", ""),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Temp"),
    os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "Windows", "INetCache",
    ),
]

# Cache de Windows Update
WINDOWS_UPDATE_CACHE = os.path.join(
    os.environ.get("SYSTEMROOT", r"C:\Windows"),
    "SoftwareDistribution", "Download",
)

# Descargas antiguas
DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
OLD_DOWNLOAD_DAYS = 30

# Simulador de prestaciones — constantes laborales Mexico
AGUINALDO_MIN_DAYS = 15
UMA_DAILY = 108.57

# Tabla de dias de vacaciones segun antiguedad (LFT 2023+)
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
