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

# ─── Simulador de prestaciones — constantes laborales Mexico ──
# IMPORTANTE: Actualizar UMA cada febrero cuando el INEGI publique el nuevo valor.
# Fuente: https://www.inegi.org.mx/temas/uma/
AGUINALDO_MIN_DAYS = 15
UMA_DAILY = 117.31  # Valor diario vigente 2026 (actualizar anualmente)

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

# ─── Retenciones de honorarios ────────────────────────────────
IVA_RATE = 0.16                 # Tasa IVA vigente
ISR_RETENTION_RATE = 0.10       # Retencion ISR sobre honorarios (Art. 106 LISR)
IVA_RETENTION_FRACTION = 2 / 3  # Fraccion del IVA retenida en honorarios

# ─── Fase 3: Constantes fiscales Mexico ──────────────────────

# Tabla ISR mensual Art. 96 LISR 2025
# (limite_inferior, limite_superior, cuota_fija, tasa_excedente)
ISR_MONTHLY_TABLE = [
    (0.01, 746.04, 0.00, 0.0192),
    (746.05, 6_332.05, 14.32, 0.0640),
    (6_332.06, 11_128.01, 371.83, 0.1088),
    (11_128.02, 12_935.82, 893.63, 0.16),
    (12_935.83, 15_487.71, 1_182.88, 0.1792),
    (15_487.72, 31_236.49, 1_640.18, 0.2136),
    (31_236.50, 49_233.00, 5_004.12, 0.2352),
    (49_233.01, 93_993.90, 9_236.89, 0.30),
    (93_993.91, 125_325.20, 22_665.17, 0.32),
    (125_325.21, 375_975.61, 32_691.18, 0.34),
    (375_975.62, float("inf"), 117_912.32, 0.35),
]

# Cuotas obrero IMSS (porcentajes sobre SBC salvo donde se indica)
IMSS_EMPLOYEE_RATES = {
    "enf_mat_excedente": 0.004,    # Enf. y Mat. excedente 3 UMA (prestaciones en especie)
    "enf_mat_dinero": 0.0025,      # Enf. y Mat. prestaciones en dinero
    "gastos_medicos": 0.00375,     # Gastos medicos pensionados
    "invalidez_vida": 0.00625,     # Invalidez y vida
    "cesantia_vejez": 0.01125,     # Cesantia en edad avanzada y vejez
}

# Tabla RESICO mensual personas fisicas
# (limite_inferior, limite_superior, cuota_fija, tasa_excedente)
RESICO_MONTHLY_TABLE = [
    (0.01, 25_000.00, 0.00, 0.01),
    (25_000.01, 50_000.00, 250.00, 0.011),
    (50_000.01, 83_333.33, 525.00, 0.015),
    (83_333.34, 208_333.33, 1_025.00, 0.02),
    (208_333.34, float("inf"), 3_525.00, 0.025),
]
