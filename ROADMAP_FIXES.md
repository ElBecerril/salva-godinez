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

## Resumen por sesion

| Sesion | Tema | Items | Severidad |
|--------|------|-------|-----------|
| 1 | Seguridad y bugs | 4 | Critica |
| 2 | Codigo duplicado | 4 | Alta |
| 3 | Robustez | 5 | Media |
| 4 | Calidad de codigo | 5 | Baja |
| 5 | Docs y empaquetado | 5 | Baja |
