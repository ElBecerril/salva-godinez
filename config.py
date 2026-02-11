"""Configuracion central: extensiones, rutas de autorecuperacion y constantes."""

import os

# Extensiones de archivos Excel y hojas de calculo
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv"}

# Extensiones de archivos temporales de Excel
TEMP_PREFIXES = ("~$", "~")
TEMP_EXTENSIONS = {".tmp", ".xlk"}

# Rutas conocidas de autorecuperacion de Excel
RECOVERY_PATHS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Excel"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Office", "UnsavedFiles"),
    os.path.join(os.environ.get("TEMP", ""), ""),
]

# Ruta de archivos recientes de Windows
RECENT_PATH = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Recent"
)

# Dias para considerar un archivo como "reciente"
RECENT_DAYS = 30
