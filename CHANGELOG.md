# Changelog

Todos los cambios notables del proyecto se documentan aqui.

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
