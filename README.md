```
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

  La navaja suiza para sobrevivir la oficina
```

Herramientas para resolver los problemas mas comunes del godinez: archivos perdidos, impresoras trabadas, USBs infectadas, PDFs imposibles y mas.

**by El_Becerril** | v2.8.0

[![GitHub Release](https://img.shields.io/github/v/release/ElBecerril/salva-godinez)](https://github.com/ElBecerril/salva-godinez/releases/latest)

## Modulos

### Recuperar y arreglar archivos (Word/Excel)

- **Recuperar archivos perdidos** - Busqueda automatica de archivos temporales (.asd, .tmp, .xlb) de Word, Excel y PowerPoint tras cierres inesperados
- **Quitar espacios que rompen formulas** - Eliminacion de espacios dobles o invisibles que rompen las formulas de Excel
- **Unir varios Excel en uno** - Unir varias hojas o archivos de Excel en uno solo de forma automatica
- **Comparar dos archivos de Excel** - Comparar dos versiones de un archivo y marcar las diferencias celda por celda
- **Desbloquear archivo en uso** - Detectar que proceso tiene abierto un archivo y ofrecer cerrarlo

### Arreglar impresoras

- **Destrabar impresora atascada** `admin` - Boton de panico para limpiar documentos trabados y reiniciar el servicio de impresion
- **Quitar impresoras duplicadas** `admin` - Identificacion y eliminacion de impresoras duplicadas o inactivas (Copia 1, Copia 2, etc.)
- **Probar si la impresora responde** - Prueba de comunicacion (Ping) para saber si la impresora de red responde
- **Compartir impresora en red** `admin` - Compartir o dejar de compartir impresoras en la red local

### USB, WiFi y Red

- **Quitar virus de la USB** - Eliminacion de virus de "acceso directo" y recuperacion de carpetas ocultas por malware
- **Revisar estado de la USB** - Diagnostico de estado: filesystem corrupto, deteccion de USBs falsas, errores de lectura/escritura
- **Respaldar archivos a USB** - Copiar carpetas importantes (Escritorio, Documentos) a USB con barra de progreso
- **Ver contrasenas WiFi guardadas** `admin` - Mostrar las claves WiFi guardadas en el equipo
- **Expulsar USB con seguridad** - Expulsar unidades USB de forma segura (mismo mecanismo que el Explorador de Windows)
- **Conectar carpetas de red** - Ver, conectar y desconectar carpetas de red compartidas

### Limpieza y mantenimiento

- **Ver datos del equipo (nombre e IP)** - Muestra rapida del nombre del equipo y la direccion IP (datos que siempre pide el area de Sistemas)
- **Liberar espacio en disco** `admin` - Limpiar temporales, cache de Windows Update y descargas viejas para liberar disco

### Calculadoras y herramientas

- **Editar PDF (unir, dividir, proteger)** - Unir, dividir, rotar, eliminar, reordenar paginas, extraer texto, convertir imagenes, proteger/desproteger y limpiar metadatos
- **Generar contrasenas seguras** - Crear contrasenas seguras y copiarlas al portapapeles
- **Calcular finiquito y prestaciones** - Estimacion de aguinaldo, vacaciones, finiquito y liquidacion segun la LFT
- **Convertir imagenes (JPG, PNG, etc.)** - Convertir imagenes entre PNG, JPG, BMP, WEBP e ICO con barra de progreso
- **Calcular sueldo neto** - Desglose de deducciones IMSS e ISR para calcular el sueldo neto mensual
- **Retenciones de honorarios** - Calculo de retenciones para Honorarios y regimen RESICO

> `admin` = Requiere ejecutar como administrador. Sin permisos de admin la herramienta lo indica y funciona de forma limitada o se omite.

## Descarga

Baja el `.exe` de la [ultima release](https://github.com/ElBecerril/salva-godinez/releases/latest) y ejecutalo directamente, no requiere instalacion. Al abrir, SalvaGodinez verifica automaticamente si hay una version nueva disponible.

### "Windows protegio tu PC" — como abrirlo la primera vez

La primera vez que lo abras, Windows te puede mostrar una pantalla azul que dice
**"Windows protegio tu PC"** y parece que bloqueo el programa. **Es normal y no
significa que tenga virus.** Sale porque SalvaGodinez es una app nueva y todavia
no tiene "firma" digital pagada — a Windows le pasa lo mismo con casi cualquier
programa gratuito recien salido. Para abrirlo:

1. En esa ventana azul, haz clic en **"Mas informacion"** (el texto chico, abajo
   del mensaje).
2. Aparece un boton nuevo: **"Ejecutar de todas formas"**. Haz clic ahi.
3. Listo, el programa abre. Windows ya no te lo vuelve a preguntar.

> Si en vez de eso tu antivirus te dice que "elimino" o "puso en cuarentena" el
> archivo, es un **falso positivo** (le pasa a muchos programas empaquetados en un
> solo `.exe`). Puedes restaurarlo desde el propio antivirus y agregarlo a la lista
> de permitidos. Si quieres estar 100% seguro de que el archivo es el original,
> compara su codigo **SHA-256** con el que aparece en las notas de cada release.

## Estado actual

Fase 3 completada. 23 herramientas funcionales organizadas en 5 categorias + auto-updater. Editor de PDF expandido a 11 funciones. v2.8.0: se agrega **PDF a Word** (extrae el texto de un PDF a un .docx editable, via PyMuPDF + python-docx). v2.7.0 activo PDF a imagenes; v2.6.1 cerro la segunda ronda de la auditoria (updater atomico, rescate, congelamientos, deuda) y v2.6.0 dejo la app como ventana limpia. Ver [CHANGELOG](CHANGELOG.md).

### Uso rapido (desde codigo)

```bash
pip install -r requirements.txt
python main.py
```

### Menu principal

| # | Categoria | Herramientas |
|---|-----------|--------------|
| 1 | Recuperar y arreglar archivos (Word/Excel) | Recuperar archivos perdidos, Quitar espacios en celdas, Unir Excel, Comparar Excel, Desbloquear archivo |
| 2 | Arreglar impresoras | Destrabar impresora `admin`, Quitar duplicadas `admin`, Probar conexion, Compartir en red `admin` |
| 3 | USB, WiFi y Red | Quitar virus USB, Revisar USB, Respaldar a USB, Ver claves WiFi `admin`, Expulsar USB, Conectar carpetas de red |
| 4 | Limpieza y mantenimiento | Ver datos del equipo, Liberar espacio `admin` |
| 5 | Calculadoras y herramientas | Editar PDF, Generar contrasenas, Finiquito y prestaciones, Convertir imagenes, Sueldo neto, Retenciones |
| 6 | Volver a la version con ventanas | Las mismas 23 herramientas, con mouse en vez de numeros de menu |

### Buscar archivos de Office perdidos - Estrategias de busqueda

| # | Estrategia | Que busca |
|---|-----------|-----------|
| 1 | Buscar por nombre | Ejecuta todas las estrategias filtrando por el nombre que ingreses |
| 2 | Office recientes (30 dias) | Archivos Office modificados en el ultimo mes en todos los discos |
| 3 | Papelera de reciclaje | Archivos Office que fueron eliminados |
| 4 | Temporales / autorecuperacion | Archivos que Office guarda automaticamente en carpetas de respaldo |
| 5 | Archivos recientes de Windows | Historial de archivos Office abiertos recientemente |
| 6 | Busqueda completa | Todas las estrategias anteriores combinadas |

#### Donde busca

- Papelera de reciclaje (via PowerShell COM object)
- Todos los discos (C:\, D:\, etc.)
- Autorecuperacion de Office (`%APPDATA%\Microsoft\{Excel,Word,PowerPoint}\`, `%LOCALAPPDATA%\Microsoft\Office\UnsavedFiles\`, `%TEMP%\`)
- Archivos recientes de Windows (shortcuts `.lnk`)
- Shadow Copies VSS (requiere ejecutar como administrador)

## Requisitos

- Windows 10 / 11
- Python 3.10+
- Dependencias: `rich>=13.7.0`, `pypdf>=4.0.0`, `openpyxl>=3.1.0`, `Pillow>=10.0.0`, `PyMuPDF>=1.25.0` (opcional, solo para PDF a Imagenes)
- Para shadow copies, reset de spooler y limpieza de impresoras: ejecutar como administrador

## Troubleshooting

**"Se requieren permisos de administrador"**
Clic derecho en la terminal o acceso directo > "Ejecutar como administrador". Las herramientas marcadas con `admin` necesitan esto para funcionar completamente.

**No encuentra archivos que se que existen**
El buscador omite carpetas del sistema (`$Recycle.Bin`, `Windows`, `Recovery`). Si el archivo esta en una USB, asegurate de que este conectada antes de buscar.

**El spooler no reinicia**
Si `net start spooler` falla, abre `services.msc`, busca "Print Spooler" y reinicialo manualmente. Si sigue fallando, puede haber un driver de impresora corrupto.

**"ModuleNotFoundError: No module named 'rich'"**
Ejecuta `pip install -r requirements.txt` desde la carpeta del proyecto. Si tienes varias versiones de Python, usa `python -m pip install -r requirements.txt`.

**El comparador de Excel tarda mucho**
Archivos muy grandes (>50,000 celdas) pueden tardar. Considera comparar hojas especificas en lugar del libro completo.

**La USB no aparece en el desinfectante**
Solo detecta unidades removibles. Discos duros externos pueden no aparecer si Windows los reconoce como "disco fijo".

## Licencia

Este proyecto esta bajo la licencia GPL v3. Ver [LICENSE](LICENSE) para mas detalles.

El `.exe` empaqueta componentes de terceros (entre ellos PyMuPDF/MuPDF bajo
AGPL-3.0, para "PDF a imagenes"). Ver [NOTICE](NOTICE) para la lista completa y
sus licencias. El codigo fuente completo esta en este mismo repositorio, como
exigen la GPL y la AGPL.

## Roadmap

### Fase 1 - Quick wins
- [x] Recuperacion de Archivos Excel
- [x] Ampliar recuperacion a Word y PowerPoint
- [x] Reset de Spooler
- [x] Info del Sistema
- [x] Desinfectante de USB
- [x] Unir/Dividir PDFs
- [x] Recuperador de Contrasena WiFi
- [x] Generador de Contrasenas

### Fase 2 - Alto valor
- [x] Limpiador de Celdas
- [x] Consolidador de Libros
- [x] Comparador de Excel
- [x] Desbloquear Archivos en Uso
- [x] Limpiador de Impresoras Fantasma
- [x] Verificador de Conexion (Ping)
- [x] Verificador de USB
- [x] Respaldo Rapido a USB
- [x] Liberador de Espacio
- [x] Simulador de Prestaciones

### Fase 3 - Evaluar
- [x] Compartir Impresora en Red
- [x] Expulsion Segura USB
- [x] Mapeo de Unidades de Red
- [x] Conversor de Imagenes
- [x] Calculadora de Sueldo Neto (ISR/IMSS)
- [x] Calculadora de Retenciones (Honorarios/RESICO)

### Fase 4 - Infraestructura
- [x] Auto-updater desde GitHub Releases
- [x] Version visible en banner
- [x] Editor de PDF expandido (rotar, eliminar, reordenar, extraer texto, imagenes a PDF, PDF a imagenes, proteger/desproteger, metadatos)

### En veremos
- Transformador de Texto (cuando haya GUI)
- Compresor PDF (dependencia Ghostscript)
- OCR Basico (dependencia Tesseract)

## Bugs, sugerencias o ideas

Encontraste un error o quieres pedir una funcionalidad nueva? Dejalo en los comentarios de cualquiera de mis redes:

- [YouTube — @el_becerril](https://www.youtube.com/@el_becerril)
- [Facebook — El Becerril](https://www.facebook.com/elbecerrilslim)

## Autor

**El_Becerril**
