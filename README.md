# Salva Godinez

La navaja suiza para sobrevivir la oficina. Herramientas para resolver los problemas mas comunes del godinez: archivos perdidos, impresoras trabadas, USBs infectadas, PDFs imposibles y mas.

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

La Recuperacion de Archivos Excel ya esta funcional. El resto de modulos estan en desarrollo.

### Recuperador de archivos - Uso rapido

```bash
pip install rich
python BuscadorExcel.py
```

O ejecuta la version PowerShell sin dependencias:

```powershell
powershell -ExecutionPolicy Bypass -File BuscadorExcel.ps1
```

#### Estrategias de busqueda disponibles

| # | Estrategia | Que busca |
|---|-----------|-----------|
| 1 | Buscar por nombre | Ejecuta todas las estrategias filtrando por el nombre que ingreses |
| 2 | Excel recientes (30 dias) | Archivos Excel modificados en el ultimo mes en todos los discos |
| 3 | Papelera de reciclaje | Archivos Excel que fueron eliminados |
| 4 | Temporales / autorecuperacion | Archivos que Excel guarda automaticamente en carpetas de respaldo |
| 5 | Archivos recientes de Windows | Historial de archivos Excel abiertos recientemente |
| 6 | Busqueda completa | Todas las estrategias anteriores combinadas |

#### Donde busca

- Papelera de reciclaje (via PowerShell COM object)
- Todos los discos (C:\, D:\, etc.)
- Autorecuperacion de Excel (`%APPDATA%\Microsoft\Excel\`, `%LOCALAPPDATA%\Microsoft\Office\UnsavedFiles\`, `%TEMP%\`)
- Archivos recientes de Windows (shortcuts `.lnk`)
- Shadow Copies VSS (requiere ejecutar como administrador)

## Requisitos

- Windows 10 / 11
- Python 3.10+ (para desarrollo)
- Para shadow copies: ejecutar como administrador

## Roadmap

### Fase 1 - Quick wins
- [x] Recuperacion de Archivos Excel
- [ ] Ampliar recuperacion a Word y PowerPoint
- [ ] Reset de Spooler
- [ ] Info del Sistema
- [ ] Desinfectante de USB
- [ ] Unir/Dividir PDFs
- [ ] Recuperador de Contrasena WiFi
- [ ] Generador de Contrasenas

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
