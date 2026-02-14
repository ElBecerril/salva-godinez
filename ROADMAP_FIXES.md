# Roadmap de Correcciones — Salva Godinez

Problemas detectados en revision de codigo, organizados por severidad.
Cada sesion aborda un grupo de issues relacionados.

---

## Sesion 1 — Critico: Seguridad y bugs funcionales ✓ COMPLETADA

- [x] **1.1** ~Corregir `password_generator.py`~ — FALSO POSITIVO: ya usaba `secrets.SystemRandom().shuffle()`
- [x] **1.2** Corregir parsing de .lnk en `recent_files.py` — agregada verificacion de LinkInfoFlags, fix de bounds check, decode latin-1 para acentos
- [x] **1.3** ~Agregar timeout a subprocess.run()~ — FALSO POSITIVO: todas las llamadas ya tenian timeout
- [x] **1.4** Cerrar workbooks de openpyxl con `.close()` en `excel_cell_cleaner.py`, `excel_consolidator.py`, `excel_comparator.py`

## Sesion 2 — Alto: Eliminar codigo duplicado ✓ COMPLETADA

- [x] **2.1** Crear `utils.py` con funciones canonicas: `read_lnk_target()`, `format_size()`, `get_drives()`
- [x] **2.2** Refactorizar `searchers/` para usar `utils.py` — eliminado `_format_size()` de 4 archivos y `_read_lnk_target()` + `_get_drives()` de 2
- [x] **2.3** Refactorizar `tools/usb_disinfect.py` — eliminado `get_removable_drives()` y `_read_lnk_target()` duplicados
- [x] **2.4** `BuscadorExcel.py` se mantiene standalone (intencional para dist .exe) — sincronizado fix de .lnk parsing

## Sesion 3 — Medio: Robustez y manejo de errores ✓ COMPLETADA

- [x] **3.1** Reemplazar `except Exception` por excepciones especificas en `file_unlocker.py` y `pdf_tools.py` (`ghost_printers.py` ya era correcto)
- [x] **3.2** Validar archivos al abrir en `excel_consolidator.py` — try/except por archivo individual (un archivo corrupto no aborta toda la consolidacion)
- [x] **3.3** Verificar exito de `net stop/start` en `spooler.py` — distingue "ya detenido" de errores reales, guia al usuario si falla
- [x] **3.4** Manejo de PDFs corruptos en `pdf_tools.py` — atrapa `PdfReadError`/`PdfStreamError` por archivo, skip corrupto y continua
- [x] **3.5** ~Mover a papelera~ — NO APLICA: disk_cleaner necesita liberar espacio (papelera no libera), usb_disinfect borra malware (no debe ser recuperable)

## Sesion 4 — Bajo: Calidad de codigo y mantenibilidad ✓ COMPLETADA

- [x] **4.1** Reemplazar `chr(92)` por `os.sep` en `disk_search.py` (2 ocurrencias)
- [x] **4.2** Robustecer parsing de `ping` con regex independientes de locale (ya no depende de "nimo"/"minimum")
- [x] **4.3** Actualizar UMA a valor 2025 ($113.14) en `config.py` + agregar comentario con fuente y recordatorio de actualizacion anual
- [x] **4.4** ~Limpiar archivos de test en usb_health.py~ — FALSO POSITIVO: ya tenia `finally` con `os.remove()`
- [x] **4.5** ~Agregar type hints~ — FALSO POSITIVO: todos los modulos ya tenian type hints consistentes

## Sesion 5 — Proyecto: Documentacion y empaquetado ✓ COMPLETADA

- [x] **5.1** Agregar `__version__` al proyecto — `__version__ = "2.0.0"` en `main.py`
- [x] **5.2** Crear `pyproject.toml` — metadata, dependencias, entry point `salva-godinez`, paquetes
- [x] **5.3** Marcar en el README que herramientas requieren admin — badge `admin` en 5 herramientas + leyenda
- [x] **5.4** Agregar seccion de troubleshooting al README — 6 problemas comunes con soluciones
- [x] **5.5** ~Evaluar si agregar CONTRIBUTING.md~ — NO APLICA: proyecto personal sin contribuidores externos

---

# Auditoría v2 — Sesiones ordenadas de mas rapido a mas tardado

## Sesion 6 — Arreglos instantaneos (~10 min) ✓ COMPLETADA

Cambios de 1-2 lineas cada uno. Cero riesgo de romper algo.

- [x] **6.1** Sincronizar version en `pyproject.toml` de `"2.0.0"` a `"2.1.0"` — 1 linea
- [x] **6.2** Eliminar archivo `nul` accidental de la raiz del proyecto (46 bytes)
- [x] **6.3** Eliminar import no usado `IntPrompt` en `reporting/console_report.py:9`
- [x] **6.4** Eliminar parametro no usado `drive` en `usb_disinfect.py:_is_suspicious_lnk()` (linea 20) y su unico call site (linea 58)
- [x] **6.5** Fijar versiones exactas en `requirements.txt` — `rich==14.3.2`, `pypdf==6.6.0`, `openpyxl==3.1.5`, `Pillow==12.1.0`
- [x] **6.6** Corregir `SalvaGodinez.spec` para incluir modulos Unicode de Rich — `collect_submodules('rich._unicode_data')`

## Sesion 7 — Mover constantes a config.py (~15 min) ✓ COMPLETADA

Cortar valor hardcoded de archivo X, pegar en `config.py`, agregar import en archivo X. Repetir.

- [x] **7.1** Mover `SKIP_DIRS` a `config.py` — reemplazar set inline en `disk_search.py` (2 ocurrencias)
- [x] **7.2** Mover magic number `86400` a `config.py` como `SECONDS_PER_DAY` — reemplazar en `disk_cleaner.py`, `disk_search.py`, `BuscadorExcel.py`
- [x] **7.3** Mover tasa IVA `0.16` de `retention_calculator.py` a `config.py` como `IVA_RATE`
- [x] **7.4** Mover tasa retencion ISR `0.10` y fraccion retencion IVA `2/3` a `config.py` como `ISR_RETENTION_RATE` e `IVA_RETENTION_FRACTION`
- [x] **7.5** Actualizar `UMA_DAILY` de $113.14 (2025) a $117.31 (2026) — fuente: INEGI boletín 1/26

## Sesion 8 — Escape de inyeccion PowerShell (~20 min) ✓ COMPLETADA

Crear 1 helper, aplicar mecanicamente en 5 archivos. El patron es identico en todos.

- [x] **8.1** Crear helper `ps_escape(value: str) -> str` en `utils.py` — escapa backtick, `"`, `$` para interpolacion segura en PowerShell
- [x] **8.2** Aplicar en `ghost_printers.py` — `Remove-Printer -Name`
- [x] **8.3** Aplicar en `printer_share.py` — `Set-Printer -Name/-ShareName` (2 ubicaciones)
- [x] **8.4** Aplicar en `usb_eject.py` — `Namespace(17).ParseName`
- [x] **8.5** Aplicar en `usb_health.py` — `Get-Volume -DriveLetter` + validacion de letra A-Z
- [x] **8.6** Aplicar en `file_unlocker.py` — reemplazar escape parcial `replace("'","''")` por `ps_escape()` con comillas dobles

## Sesion 9 — Extraer funciones duplicadas (~30 min) ✓ COMPLETADA

Crear modulos compartidos y reemplazar copias en 6+ archivos. Cambios mecanicos pero muchos archivos.

- [x] **9.1** Crear `tools/_fiscal_helpers.py` con: `ask_float()`, `fmt()`, `find_bracket()`, `DISCLAIMER`
- [x] **9.2** Refactorizar `salary_calculator.py` — eliminar 4 funciones locales, importar de `_fiscal_helpers`
- [x] **9.3** Refactorizar `retention_calculator.py` — eliminar 4 funciones locales, importar de `_fiscal_helpers`
- [x] **9.4** Refactorizar `prestaciones_sim.py` — eliminar `_ask_float`, `_fmt`, `DISCLAIMER`, importar de `_fiscal_helpers`
- [x] **9.5** Extraer `get_openpyxl()` a `utils.py` — refactorizar `excel_cell_cleaner.py`, `excel_comparator.py`, `excel_consolidator.py`
- [x] **9.6** Extraer `deduplicate()` de `main.py` a `utils.py`

## Sesion 10 — Limpieza legacy y mejoras UX (~35 min) ✓ COMPLETADA

Deprecar codigo viejo + mejoras de experiencia de usuario que requieren logica nueva.

- [x] **10.1** Deprecar `BuscadorExcel.py` — banner de advertencia en docstring dirigiendo a `main.py`/`SalvaGodinez.exe`
- [x] **10.2** Mover `BuscadorExcel.py` y `BuscadorExcel.ps1` a carpeta `legacy/`
- [x] **10.3** Reducir traceback expuesto en `main.py` — logea a `salva_error.log`, muestra solo mensaje amigable al usuario
- [x] **10.4** Enmascarar passwords en `wifi_passwords.py` — muestra `p*******3` por defecto, pregunta si revelar en texto plano
- [x] **10.5** En `net_drive.py` — usa `*` para que `net use` pida la contrasena interactivamente (no visible en lista de procesos)

## Sesion 11 — Integridad del updater y refactor Console (~45 min) ✓ COMPLETADA

Los cambios mas complejos: verificacion criptografica de descargas + refactor transversal de 26 archivos.

- [x] **11.1** Agregar hash SHA-256 como asset o en el body del GitHub Release al publicar nuevas versiones
- [x] **11.2** Verificar SHA-256 en `updater.py` despues de descargar el .exe — `_extract_sha256()` parsea hash del body del Release, verifica con `hashlib`, aborta y elimina si no coincide
- [x] **11.3** Crear fuente unica de verdad para version — `dynamic = ["version"]` en pyproject.toml leyendo de `main.__version__`
- [x] **11.4** Unificar instancias de `Console()` — singleton en `utils.py`, importado en 26 modulos (eliminadas 26 instancias independientes)

---

## Resumen por sesion

| Sesion | Tema | Items | Tiempo est. | Severidad original |
|--------|------|-------|-------------|-------------------|
| 1 | Seguridad y bugs | 4 | — | Critica ✓ |
| 2 | Codigo duplicado | 4 | — | Alta ✓ |
| 3 | Robustez | 5 | — | Media ✓ |
| 4 | Calidad de codigo | 5 | — | Baja ✓ |
| 5 | Docs y empaquetado | 5 | — | Baja ✓ |
| 6 | Arreglos instantaneos | 6 | ~10 min | Mixta (Alta/Baja) ✓ |
| 7 | Constantes a config.py | 5 | ~15 min | Media ✓ |
| 8 | Escape PowerShell | 6 | ~20 min | Critica ✓ |
| 9 | Extraer duplicados | 6 | ~30 min | Media ✓ |
| 10 | Legacy + UX | 5 | ~35 min | Alta/Media ✓ |
| 11 | Updater SHA-256 + Console | 4 | ~45 min | Alta/Baja ✓ |
