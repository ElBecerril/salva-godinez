# Buscador de Archivos Excel Perdidos

Herramienta para buscar y recuperar archivos Excel que desaparecieron de tu disco duro. Escanea multiples ubicaciones donde Windows y Excel guardan copias, temporales y referencias.

## Descarga

Ve a [Releases](../../releases) y descarga `BuscadorExcel.exe`. Doble clic y listo, no necesitas instalar nada.

## Estrategias de busqueda

| # | Estrategia | Que busca |
|---|-----------|-----------|
| 1 | **Buscar por nombre** | Ejecuta todas las estrategias filtrando por el nombre que ingreses |
| 2 | **Excel recientes (30 dias)** | Todos los archivos Excel modificados en el ultimo mes en todos los discos |
| 3 | **Papelera de reciclaje** | Archivos Excel que fueron eliminados |
| 4 | **Temporales / autorecuperacion** | Archivos que Excel guarda automaticamente en carpetas de respaldo |
| 5 | **Archivos recientes de Windows** | Historial de archivos Excel abiertos recientemente (detecta si aun existen) |
| 6 | **Busqueda completa** | Ejecuta todas las estrategias anteriores combinadas |

## Uso

### Ejecutable (recomendado)

Doble clic en `BuscadorExcel.exe`. Selecciona una opcion del menu:

```
  ____                           _
 | __ ) _   _ ___  ___ __ _ ___| | ___  _ __
 |  _ \| | | / __|/ __/ _` / __| |/ _ \| '__|
 | |_) | |_| \__ \ (_| (_| \__ \ | (_) | |
 |____/ \__,_|___/\___\__,_|___/_|\___/|_|

  Buscador de Archivos Excel Perdidos
  by El_Becerril

  1 - Buscar por nombre de archivo
  2 - Buscar todos los Excel recientes (30 dias)
  3 - Revisar papelera de reciclaje
  4 - Revisar archivos temporales / autorecup.
  5 - Revisar archivos recientes de Windows
  6 - Busqueda completa (todas las opciones)
  0 - Salir
```

Cuando encuentre resultados, te muestra una tabla con nombre, ruta, tamano, fecha y origen. Despues te ofrece copiar el archivo a la ubicacion que elijas.

### PowerShell (alternativa ligera)

Si prefieres no usar el .exe, puedes ejecutar el script de PowerShell directamente:

```powershell
powershell -ExecutionPolicy Bypass -File BuscadorExcel.ps1
```

### Python (desarrollo)

```bash
pip install rich
python BuscadorExcel.py
```

## Donde busca

- **Papelera de reciclaje** - Via PowerShell COM object
- **Todos los discos** (C:\, D:\, etc.) - Escaneo recursivo filtrando por extensiones Excel
- **Autorecuperacion de Excel:**
  - `%APPDATA%\Microsoft\Excel\`
  - `%LOCALAPPDATA%\Microsoft\Office\UnsavedFiles\`
  - `%TEMP%\` (archivos temporales `~$*.xlsx`)
- **Archivos recientes de Windows** - Lee shortcuts `.lnk` en `%APPDATA%\Microsoft\Windows\Recent\`
- **Shadow Copies (VSS)** - Versiones anteriores del sistema (requiere ejecutar como administrador)

## Extensiones soportadas

`.xlsx` `.xls` `.xlsm` `.xlsb` `.csv`

## Requisitos

- Windows 10 / 11
- Para shadow copies: ejecutar como administrador

## Notas

- La busqueda en disco completo puede tardar varios minutos dependiendo del tamano del disco
- Los archivos encontrados en "Recientes" que ya no existen se marcan como "NO encontrado" - esto indica que el archivo estuvo ahi pero fue movido o eliminado
- Para la papelera: el archivo se muestra con su ruta original, desde ahi puedes restaurarlo manualmente o usar la opcion de copiar

## Autor

**El_Becerril**
