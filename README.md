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

**by El_Becerril**

## Modulos

### Office (El Rescatista)

- **Recuperacion de Archivos** - Busqueda automatica de archivos temporales (.asd, .tmp, .xlb) de Word, Excel y PowerPoint tras cierres inesperados
- **Limpiador de Celdas** - Eliminacion de espacios dobles o invisibles que rompen las formulas de Excel
- **Consolidador de Libros** - Unir varias hojas o archivos de Excel en uno solo de forma automatica
- **Comparador de Excel** - Comparar dos versiones de un archivo y marcar las diferencias celda por celda
- **Desbloquear Archivos en Uso** - Detectar que proceso tiene abierto un archivo y ofrecer cerrarlo

### Impresoras (El Doctor)

- **Limpiador de Fantasmas** - Identificacion y eliminacion de impresoras duplicadas o inactivas (Copia 1, Copia 2, etc.)
- **Compartir en Red** - Configuracion automatica para compartir la impresora usando el nombre de la maquina
- **Reset de Cola (Spooler)** - Boton de panico para limpiar documentos trabados y reiniciar el servicio de impresion
- **Verificador de Conexion** - Prueba de comunicacion (Ping) para saber si la impresora de red responde

### Finanzas (Calculadora Fiscal)

- **Calculadora de Sueldo Neto** - Desglose de retenciones de ISR e IMSS para saber cuanto llega libre realmente
- **Calculadora de Retenciones (Honorarios/RESICO)** - Calculo automatico de IVA e ISR para facturacion profesional
- **Simulador de Prestaciones** - Estimacion de aguinaldo, vacaciones y finiquitos segun los dias laborados

### Red y USB (El Escudo)

- **Desinfectante de USB** - Eliminacion de virus de "acceso directo" y recuperacion de carpetas ocultas por malware
- **Verificador de USB** - Diagnostico de estado: filesystem corrupto, deteccion de USBs falsas, errores de lectura/escritura
- **Info del Sistema** - Muestra rapida del nombre del equipo y la direccion IP (datos que siempre pide el area de Sistemas)
- **Expulsion Segura Forzada** - Cerrar procesos que impiden retirar la USB
- **Recuperador de Contrasena WiFi** - Mostrar las claves WiFi guardadas en el equipo
- **Mapeo de Unidades de Red** - Asistente para conectar carpetas compartidas de red facilmente
- **Respaldo Rapido a USB** - Copiar carpetas importantes (Escritorio, Documentos) a USB con un clic
- **Generador de Contrasenas** - Crear contrasenas seguras y copiarlas al portapapeles

### Mantenimiento (El Conserje)

- **Liberador de Espacio** - Limpiar temporales, cache de Windows Update y descargas viejas para liberar disco

### PDF (El Editor)

- **Unir y Dividir** - Combinar varios documentos en uno solo o separar paginas especificas
- **Conversor de Imagenes** - Cambiar formato (PNG a JPG) y redimensionar imagenes para correo

## Estado actual

Fase 1 completada. El menu principal ofrece 7 herramientas funcionales.

### Uso rapido

```bash
pip install -r requirements.txt
python main.py
```

### Menu principal

| # | Herramienta | Descripcion |
|---|-------------|-------------|
| 1 | Rescatista de Archivos Office | Busqueda y recuperacion de Excel, Word y PowerPoint |
| 2 | Reset de Spooler | Limpia la cola de impresion trabada (requiere admin) |
| 3 | Info del Sistema | Hostname, IP, MAC, Windows, usuario |
| 4 | Desinfectante de USB | Detecta y elimina amenazas comunes en USBs |
| 5 | Editor de PDF | Unir y dividir archivos PDF |
| 6 | Recuperador de WiFi | Muestra contrasenas WiFi guardadas en Windows |
| 7 | Generador de Contrasenas | Genera contrasenas seguras y las copia al portapapeles |

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
- Dependencias: `rich>=13.7.0`, `pypdf>=4.0.0`
- Para shadow copies y reset de spooler: ejecutar como administrador

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
- [ ] Limpiador de Celdas
- [ ] Consolidador de Libros
- [ ] Comparador de Excel
- [ ] Desbloquear Archivos en Uso
- [ ] Limpiador de Impresoras Fantasma
- [ ] Verificador de Conexion (Ping)
- [ ] Verificador de USB
- [ ] Respaldo Rapido a USB
- [ ] Liberador de Espacio
- [ ] Simulador de Prestaciones

### Fase 3 - Evaluar
- [ ] Compartir Impresora en Red
- [ ] Expulsion Segura USB
- [ ] Mapeo de Unidades de Red
- [ ] Conversor de Imagenes
- [ ] Calculadora de Sueldo Neto (ISR/IMSS)
- [ ] Calculadora de Retenciones (Honorarios/RESICO)

### En veremos
- Transformador de Texto (cuando haya GUI)
- Compresor PDF (dependencia Ghostscript)
- OCR Basico (dependencia Tesseract)

## Autor

**El_Becerril**
