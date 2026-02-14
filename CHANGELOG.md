# Changelog

Todos los cambios notables del proyecto se documentan aqui.

## [2.2.2] - 2026-02-14

### Agregado
- Panel de despedida al salir con links a YouTube y Facebook para apoyar el proyecto

### Corregido
- Auto-updater: ahora elimina versiones anteriores del Escritorio antes de descargar la nueva
- CONTRIBUTORS: link al perfil de GitHub y descripcion actualizada

## [2.2.1] - 2026-02-14

### Corregido
- Tabla ISR mensual actualizada a 2026 (Anexo 8 RMF 2026, DOF 28/12/2025, factor 1.13213)
- Version en README sincronizada con `main.__version__`
- Submenu de impresoras: "Compartir en Red" ahora muestra pausa "Presiona Enter"
- Consolidador Excel: nombres de hoja truncados a 31 chars ya no crashean por duplicados (sufijo numerico)
- Mapeo de red: rutas UNC con espacios se parsean correctamente en `net use`

## [2.2.0] - 2026-02-13

### Seguridad
- Escape de inyeccion PowerShell (`ps_escape()`) en 5 modulos: ghost_printers, printer_share, usb_eject, usb_health, file_unlocker
- Verificacion SHA-256 del .exe descargado en auto-updater
- Passwords WiFi enmascarados por defecto (revelar solo si el usuario confirma)
- Credenciales de unidades de red nunca visibles en lista de procesos (`net use *`)

### Cambiado
- Constantes hardcoded centralizadas en `config.py`: SKIP_DIRS, SECONDS_PER_DAY, IVA_RATE, ISR_RETENTION_RATE, IVA_RETENTION_FRACTION
- UMA actualizado a $117.31 (2026)
- Console singleton en `utils.py` compartido por 26 modulos (antes cada uno creaba su propia instancia)
- Funciones fiscales duplicadas extraidas a `tools/_fiscal_helpers.py`
- `get_openpyxl()` y `deduplicate()` extraidas a `utils.py`
- Version dinamica en `pyproject.toml` (lee de `main.__version__`)
- Dependencias fijadas en `requirements.txt`: rich==14.3.2, pypdf==6.6.0, openpyxl==3.1.5, Pillow==12.1.0
- Traceback amigable: errores inesperados se loguean a `salva_error.log` en vez de mostrarse al usuario

### Deprecado
- `BuscadorExcel.py` y `BuscadorExcel.ps1` movidos a `legacy/` con banner de advertencia

### Eliminado
- Import no usado `IntPrompt` en console_report
- Parametro no usado `drive` en usb_disinfect
- Archivo `nul` accidental en raiz del proyecto
- ~1,200 lineas de codigo duplicado eliminadas

## [2.1.0] - 2026-02-13

### Agregado
- Auto-updater: al abrir SalvaGodinez verifica GitHub Releases y ofrece descargar nueva version al Escritorio
- Version visible en el banner del menu principal (by El_Becerril - v2.1.0)

### Corregido
- Crash por UnicodeDecodeError (cp1252) al buscar en papelera de reciclaje con archivos con caracteres especiales
- Mismo fix aplicado a shadow copies (searchers/shadow_copies.py)

## [1.2.0] - 2026-02-12

### Agregado
- Limpiador de Celdas Excel (espacios dobles, NBSP, caracteres invisibles)
- Consolidador de Libros Excel (unir archivos o unir hojas)
- Comparador de Excel (diferencias celda por celda con reporte)
- Desbloquear Archivo en Uso (detecta procesos via Restart Manager API)
- Limpiador de Impresoras Fantasma (detecta y elimina copias duplicadas)
- Verificador de Conexion (ping + prueba de puertos de impresora)
- Verificador de USB (info, velocidad, autenticidad, chkdsk)
- Respaldo Rapido a USB (copia Desktop/Documents con barra de progreso)
- Liberador de Espacio (temporales, cache Windows Update, descargas antiguas, papelera)
- Simulador de Prestaciones Mexico (aguinaldo, vacaciones, finiquito, liquidacion)
- Dependencia openpyxl para herramientas Excel
- Utilidades compartidas: format_size, get_drives, get_removable_drives

### Cambiado
- Menu principal reorganizado en 5 categorias con sub-menus
- 17 herramientas totales distribuidas en: Office, Impresoras, USB y Red, Sistema, Utilidades

## [1.1.0] - 2026-02-12

### Agregado
- Soporte para archivos Word (.docx, .doc, .docm, .dotx, .dotm, .rtf)
- Soporte para archivos PowerPoint (.pptx, .ppt, .pptm, .potx, .ppsx)
- Reset de Spooler (cola de impresion) con limpieza de archivos
- Info del Sistema (hostname, IP, MAC, Windows, usuario)
- Desinfectante de USB (autorun.inf, ejecutables, .lnk maliciosos, carpetas ocultas)
- Editor de PDF (unir y dividir archivos)
- Recuperador de contrasenas WiFi guardadas
- Generador de contrasenas seguras con copia al portapapeles
- Menu principal multi-modulo con banner Salva Godinez
- Dependencia pypdf para herramientas PDF

### Cambiado
- Searchers actualizados de EXCEL_EXTENSIONS a OFFICE_EXTENSIONS
- Menu de busqueda de archivos movido a sub-menu "Rescatista de Archivos Office"
- Rutas de autorecuperacion expandidas a Word y PowerPoint

## [1.0.0] - 2026-02-11

### Agregado
- Busqueda de archivos Excel por nombre en todos los discos
- Busqueda de archivos Excel recientes (ultimos 30 dias)
- Busqueda en papelera de reciclaje via PowerShell COM
- Busqueda en archivos temporales y autorecuperacion
- Busqueda en archivos recientes de Windows (.lnk)
- Busqueda en Shadow Copies VSS (requiere admin)
- Reporte interactivo con Rich y opcion de restaurar
- Version standalone (BuscadorExcel.py) sin dependencias
- Version PowerShell (BuscadorExcel.ps1)
