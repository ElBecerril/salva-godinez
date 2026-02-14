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

**by El_Becerril** | v2.2.2

[![GitHub Release](https://img.shields.io/github/v/release/ElBecerril/salva-godinez)](https://github.com/ElBecerril/salva-godinez/releases/latest)

## Modulos

### Office (El Rescatista)

- **Recuperacion de Archivos** - Busqueda automatica de archivos temporales (.asd, .tmp, .xlb) de Word, Excel y PowerPoint tras cierres inesperados
- **Limpiador de Celdas** - Eliminacion de espacios dobles o invisibles que rompen las formulas de Excel
- **Consolidador de Libros** - Unir varias hojas o archivos de Excel en uno solo de forma automatica
- **Comparador de Excel** - Comparar dos versiones de un archivo y marcar las diferencias celda por celda
- **Desbloquear Archivos en Uso** - Detectar que proceso tiene abierto un archivo y ofrecer cerrarlo

### Impresoras (El Doctor)

- **Reset de Cola (Spooler)** `admin` - Boton de panico para limpiar documentos trabados y reiniciar el servicio de impresion
- **Limpiador de Fantasmas** `admin` - Identificacion y eliminacion de impresoras duplicadas o inactivas (Copia 1, Copia 2, etc.)
- **Verificador de Conexion** - Prueba de comunicacion (Ping) para saber si la impresora de red responde
- **Compartir en Red** `admin` - Compartir o dejar de compartir impresoras en la red local

### USB y Red (El Escudo)

- **Desinfectante de USB** - Eliminacion de virus de "acceso directo" y recuperacion de carpetas ocultas por malware
- **Verificador de USB** - Diagnostico de estado: filesystem corrupto, deteccion de USBs falsas, errores de lectura/escritura
- **Respaldo Rapido a USB** - Copiar carpetas importantes (Escritorio, Documentos) a USB con barra de progreso
- **Recuperador de Contrasena WiFi** `admin` - Mostrar las claves WiFi guardadas en el equipo
- **Expulsion Segura USB** - Expulsar unidades USB de forma segura (mismo mecanismo que el Explorador de Windows)
- **Mapeo de Unidades de Red** - Ver, conectar y desconectar unidades de red mapeadas

### Sistema (El Conserje)

- **Info del Sistema** - Muestra rapida del nombre del equipo y la direccion IP (datos que siempre pide el area de Sistemas)
- **Liberador de Espacio** `admin` - Limpiar temporales, cache de Windows Update y descargas viejas para liberar disco

### Utilidades

- **Editor de PDF** - Combinar varios documentos en uno solo o separar paginas especificas
- **Generador de Contrasenas** - Crear contrasenas seguras y copiarlas al portapapeles
- **Simulador de Prestaciones** - Estimacion de aguinaldo, vacaciones, finiquito y liquidacion segun la LFT
- **Conversor de Imagenes** - Convertir imagenes entre PNG, JPG, BMP, WEBP e ICO con barra de progreso
- **Calculadora de Sueldo Neto** - Desglose de deducciones IMSS e ISR para calcular el sueldo neto mensual
- **Calculadora de Retenciones** - Calculo de retenciones para Honorarios y regimen RESICO

> `admin` = Requiere ejecutar como administrador. Sin permisos de admin la herramienta lo indica y funciona de forma limitada o se omite.

## Descarga

Baja el `.exe` de la [ultima release](https://github.com/ElBecerril/salva-godinez/releases/latest) y ejecutalo directamente, no requiere instalacion. Al abrir, SalvaGodinez verifica automaticamente si hay una version nueva disponible.

## Estado actual

Fase 3 completada. 23 herramientas funcionales organizadas en 5 categorias + auto-updater.

### Uso rapido (desde codigo)

```bash
pip install -r requirements.txt
python main.py
```

### Menu principal

| # | Categoria | Herramientas |
|---|-----------|--------------|
| 1 | Office (El Rescatista) | Rescate de Archivos, Limpiador de Celdas, Consolidador, Comparador, Desbloquear |
| 2 | Impresoras (El Doctor) | Reset de Spooler `admin`, Limpiador de Fantasmas `admin`, Verificador de Conexion, Compartir en Red `admin` |
| 3 | USB y Red (El Escudo) | Desinfectante USB, Verificador USB, Respaldo Rapido, Recuperador WiFi `admin`, Expulsion Segura, Mapeo de Red |
| 4 | Sistema (El Conserje) | Info del Sistema, Liberador de Espacio `admin` |
| 5 | Utilidades | Editor de PDF, Generador de Contrasenas, Simulador de Prestaciones, Conversor de Imagenes, Calculadora de Sueldo Neto, Calculadora de Retenciones |

### Rescatista de Archivos - Estrategias de busqueda

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
- Dependencias: `rich>=13.7.0`, `pypdf>=4.0.0`, `openpyxl>=3.1.0`, `Pillow>=10.0.0`
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
