# Changelog

Todos los cambios notables del proyecto se documentan aqui.

## [2.7.0] - 2026-07-22

### Agregado
- **PDF a imagenes.** Convierte cada pagina de un PDF en una imagen PNG o JPG,
  con resolucion configurable (72-600 DPI). La herramienta ya existia en el menu
  pero salia como "(no disponible)" porque faltaba el motor; ahora PyMuPDF viaja
  dentro del `.exe` y la funcion esta activa. Verificado en Windows real.

### Cambiado
- El `.exe` crece ~17 MB (de ~23 a ~40 MB) por empaquetar PyMuPDF/MuPDF.
- Se agrega el archivo `NOTICE` con la atribucion de PyMuPDF/MuPDF (AGPL-3.0) y
  demas componentes de terceros. El codigo fuente completo sigue abierto (GPL/AGPL).

## [2.6.1] - 2026-07-22

Segunda ronda de la auditoria completa de v2.6.0: se cierran los bugs con
impacto real que quedaron abiertos (updater, rescate, congelamientos de la
interfaz, falsos positivos) y se paga deuda tecnica. Verificado en Windows real.

### Seguridad
- **Auto-updater: instalacion atomica.** El .exe nuevo se descarga a un temporal
  EN el mismo Escritorio y se coloca con un rename atomico. Antes, si la
  descarga se interrumpia a la mitad, podia quedar un .exe truncado; ahora un
  corte solo deja un archivo temporal inofensivo. Ademas el aviso de descarga no
  se puede cerrar mientras baja y verifica.
- **Auto-updater: encuentra el Escritorio real.** En equipos con OneDrive (comun
  en oficinas), el Escritorio esta redirigido; antes la actualizacion fallaba al
  guardarse. Ahora se resuelve la ruta real.
- **Verificacion de la firma mas robusta.** El SHA-256 de las notas del release
  se lee aunque este dentro de un bloque de formato; antes, en ese caso, el
  updater rechazaba la actualizacion como "sin firma".

### Corregido
- **Recuperar archivos: ya no oculta resultados de la papelera.** Dos archivos
  borrados sin carpeta original registrada se mostraban como uno solo; ahora
  aparecen todos.
- **La ventana ya no se congela** al guardar/comparar archivos de Excel grandes
  ni al recuperar un archivo pesado (esas tareas corren en segundo plano). La
  tabla de diferencias se limita para no trabar la app con archivos enormes.
- **Menos crashes silenciosos en la interfaz:** cambiar de pantalla o de
  operacion a media tarea ya no deja la ventana trabada ni impide cerrarla.
- **PDF protegido con contrasena:** al dividirlo ya no se reporta como "danado";
  ahora avisa que esta protegido.
- **Revisar USB: menos falsos "USB falsa".** La prueba ya no marca como
  sospechosa una USB legitima casi llena.
- **Comparar Excel** avisa cuando el resultado "identicos" puede deberse a
  formulas sin valor guardado (evita un falso negativo).
- **Carpetas de red:** si `net use` falla, se muestra el error real en vez de
  decir "no hay carpetas conectadas".
- **Datos del equipo:** si no se puede leer la MAC real, se muestra "No
  disponible" en vez de una direccion inventada.
- **Desbloquear archivo en uso:** ya no afirma "sin procesos" con falsa certeza
  cuando el sistema no pudo consultarlo.

### Cambiado
- **Guardar respeta "Reemplazar".** Al unir/crear PDF o guardar un Excel limpio,
  si confirmas reemplazar un archivo existente se escribe con ese nombre exacto
  (antes creaba una copia con "_1"). Nunca se pisa un archivo de ENTRADA.
- **Guardar Excel conserva la extension** del original (no guarda un .xlsm con
  macros como .xlsx, que las perderia).
- **Prestaciones/liquidacion:** la antiguedad acepta decimales para pagar la
  parte proporcional del anio; mensajes de ayuda mas claros por campo.
- **Menos parpadeos y mensajes ambiguos** (papelera vacia vs. no vaciada, avisos
  de carpetas de red) y limpieza interna de codigo sin uso.

## [2.6.0] - 2026-07-22

Ronda grande: se cierra la consola negra de Windows 11, el auto-updater vuelve
a funcionar en el `.exe`, y una auditoria completa de la app (7 areas) cierra
crashes y afina los calculos fiscales antes de lanzar.

### Seguridad
- **Auto-updater: verificacion HTTPS restaurada en el `.exe` congelado.** El
  `ssl` de PyInstaller no encontraba los certificados raiz del sistema, asi que
  la conexion a `api.github.com` fallaba EN SILENCIO y el aviso de version nueva
  nunca salia. Ahora se empaqueta el CA bundle de `certifi` y se usa un contexto
  SSL explicito; la verificacion de certificado nunca se desactiva. Verificado
  en Windows real.
- **Contrasena de red fuera de la linea de comandos.** Al conectar una carpeta
  de red con credenciales, la clave iba como argumento de `net use` (visible en
  el Administrador de tareas). Ahora se entrega por entrada estandar, no queda
  en la lista de procesos.

### Corregido
- **La consola negra ya no aparece.** La app se compila como aplicacion de
  ventana; el modo texto crea su consola solo cuando hace falta. En Windows 11
  ya no queda una ventana de terminal detras ni un icono de consola al arrancar.
- **Nombres con corchetes ya no tumban la app.** Un archivo `informe[final].xlsx`,
  una USB con `setup[1].exe`, o una celda con `[texto]` hacian crashear la
  version de texto al mostrarlos. Se escapan todos los datos externos que van a
  pantalla (rescate, USB, impresoras, PDF, Excel, imagenes).
- **Liberar espacio ya no borra lo que Recuperar archivos rescata.** La limpieza
  de temporales destruia los autorecuperados de Office (`.asd`, `~$...`) que
  viven en `%TEMP%` — justo lo que la herramienta de rescate recupera. Ahora se
  protegen: la limpieza los salta y el espacio estimado ya no los cuenta.
- **Archivos que no tumban la app al abrirse/guardarse.** Un Excel viejo `.xls`,
  un PDF con pagina danada, o un archivo de salida abierto en Excel/bloqueado
  por OneDrive ahora dan un mensaje claro en vez de cerrar el programa.
- **Vacaciones/finiquito con dias mal capturados.** Si se escribian mas de 365
  dias trabajados, las vacaciones proporcionales se inflaban por encima del
  derecho de un anio; ahora se topan como el aguinaldo.
- **El aviso de version nueva ya no se cae con etiquetas `-beta`/`-rc`.** El
  parseo de version toleraba solo numeros; un tag con sufijo lo tronaba en
  silencio.

### Cambiado
- **Calculos de liquidacion mas apegados a la ley.** Los 3 meses
  constitucionales y los 20 dias por anio se calculan con el Salario Diario
  Integrado (SDI); la prima de antiguedad y los 20 dias/anio se pagan tambien
  por la fraccion de anio (los campos de antiguedad aceptan decimales); el
  calculo de cuotas IMSS usa el Salario Base de Cotizacion con factor de
  integracion. Sigue siendo una estimacion informativa.
- **Se acabo el parpadeo de consola negra en Carpetas de red.** Los comandos de
  red ya no muestran una ventana al ejecutarse.

### Agregado
- **Aviso de origen oficial y auto-update como ventanas.** Al arrancar, la app
  avisa (una vez por version) desde donde es seguro bajarla, y el aviso de
  actualizacion es una ventana con boton, no un mensaje en negro.

## [2.5.4] - 2026-07-21

### Corregido
- **Volvio a aparecer el mensaje de apoyo al cerrar la app.** Vivia solo en la
  despedida del modo texto, que dejo de correr cuando la version con ventanas
  paso a ser la que abre por default (v2.5.0): al cerrar la ventana, ese codigo
  nunca se ejecutaba y nadie volvia a ver la invitacion a YouTube/Facebook. Es
  el mismo tipo de fallo que el aviso de version nueva de la v2.5.2 — algo que
  colgaba del arranque viejo quedo huerfano al mover el punto de entrada

### Agregado
- **Despedida en la version con ventanas.** Al cerrar la app sale un cuadro de
  agradecimiento con botones que abren YouTube, Facebook e Instagram con un
  clic (antes, en el modo texto, habia que escribir un numero). El mensaje solo
  sale al cerrar para salir, no al volver al modo texto (que ya tiene el suyo)
- **Instagram** (@el_becerril) se suma a las redes, tanto en la despedida de
  ventanas como en la de texto

### Cambiado
- Las redes ahora viven en un solo lugar (`config.CANALES_APOYO`), usado por las
  dos despedidas (ventanas y texto), para no repetir las direcciones

## [2.5.3] - 2026-07-21

Ronda de arreglos salidos de probar las 23 pantallas en Windows real. Ninguna
tronaba; lo que se corrige es lo que se veia mal o confundia.

### Corregido
- **El boton de accion de abajo se cortaba.** En laptops de pantalla chica
  (1366x768) la ventana se abria mas alta que el espacio util, y el boton de
  "Guardar", "Unir", etc. quedaba pegado al borde o fuera de la vista. Ahora la
  ventana se ajusta al tamano de la pantalla y se centra, y las listas de
  resultados piden menos alto para dejarle lugar al boton
- **Rutas con las diagonales mezcladas** (`C:/Users/...\archivo.pdf`) en los
  avisos de PDF y de unir Excel. Ahora se muestran con un solo estilo
- **La revision de espacios mostraba `\xa0`** (el codigo interno de un "espacio
  duro") en la columna de antes/despues. Ahora dice `[espacio duro]`, y las
  comillas dejan ver los espacios al inicio y al final
- **Comparar dos Excel decia "son identicos en las hojas comunes"** aunque los
  archivos no tuvieran ninguna hoja en comun. Ahora lo aclara
- Detalles de redaccion: "1 imagen" en vez de "1 imagenes"

### Cambiado
- **"PDF a imagenes" avisa desde el principio** cuando esta version no trae el
  componente necesario (aparece marcada como "no disponible" en la lista), en
  vez de dejar elegir archivo, formato, resolucion y carpeta para recien
  entonces decir que no se puede

## [2.5.2] - 2026-07-20

### Corregido
- **El aviso de version nueva no aparecia.** Desde que la app abre con ventanas
  por default (v2.5.0), la revision de actualizaciones se quedo colgada del
  menu de texto, que ya no se ejecuta al abrir normalmente. Nadie se enteraba
  de que habia una version mas nueva
- **La advertencia de origen oficial tampoco se mostraba**, por el mismo
  motivo. Es el aviso de que SalvaGodinez solo es legitimo si se bajo de
  github.com/ElBecerril/salva-godinez, y sirve para que nadie use una copia
  falsa con virus. Llevaba dos versiones sin verse

Las dos ahora ocurren al arrancar, sin importar si abres la version con
ventanas o el modo texto.

> **Si vienes de la v2.4.0, v2.5.0 o v2.5.1**, esas versiones tienen el fallo y
> no te van a avisar de esta actualizacion: hay que bajarla a mano una vez.
> A partir de aqui el aviso vuelve a funcionar solo.

## [2.5.1] - 2026-07-20

### Corregido
- **Ya se pueden ver todas las herramientas de la lista.** Con 23 en la barra
  lateral, las ultimas quedaban fuera de la pantalla y no habia forma de
  llegar a ellas: la barra de scroll existia pero quedaba escondida detras de
  la lista, y la rueda del mouse no hacia nada
- **La rueda del mouse ya desplaza la lista**, que es lo primero que uno
  intenta. Funciona igual pasando el cursor sobre los botones
- **"Volver al modo texto" queda siempre a la vista**, abajo de la barra, sin
  desplazarse con la lista

## [2.5.0] - 2026-07-20

Al abrir SalvaGodinez ahora sale directo la version con ventanas. Es el mismo
programa y las mismas 23 herramientas; solo cambia con cual te recibe.

### Cambiado
- **La version con ventanas es la que abre por default.** En v2.4.0 estaba
  como opcion 6 del menu de texto y la gente que abria la app por primera vez
  simplemente no la encontraba: uno abre un programa esperando una ventana, no
  se pone a leer un menu para descubrir que hay una
- **El modo texto no desaparece**, solo dejo de ser el primero que ves. Se
  llega de tres formas: con el boton **"Volver al modo texto"** abajo en la
  barra lateral, abriendo `SalvaGodinez.exe --consola`, y automaticamente si
  la version con ventanas no se puede abrir en esa computadora
- **Ya no sale la ventana negra detras.** Al abrir la version con ventanas se
  esconde la ventana de texto, y vuelve a aparecer si regresas al modo texto

### Agregado
- **Boton "Volver al modo texto"** al fondo de la barra lateral

## [2.4.0] - 2026-07-20

Ahora SalvaGodinez tambien se puede usar con ventanas y mouse, sin escribir
numeros de menu. Es la misma app: las 23 herramientas de siempre, con los
mismos calculos y las mismas confirmaciones antes de borrar nada.

### Agregado
- **Version con ventanas (interfaz grafica)**: se abre con la opcion **6** del
  menu principal. Las 23 herramientas estan ahi, agrupadas en las mismas 5
  categorias del menu de texto, con una barra lateral para moverse entre ellas
- **Resultados de busqueda en vivo**: al buscar un archivo perdido, los
  resultados van apareciendo conforme se encuentran. Lo que esta en la papelera
  sale de inmediato, sin esperar a que termine de revisar todo el disco
- **Editar PDF con lista de operaciones**: las 10 operaciones (unir, dividir,
  rotar, proteger...) se eligen de una lista y cada una pide solo lo suyo
- **Contrasenas WiFi ocultas por default**: se muestran con puntos y hay que
  pedir ver cada una, o copiarla al portapapeles sin mostrarla — util si estas
  proyectando la pantalla en una junta

### Corregido
- **Recuperar archivos ya no se limita a Word y Excel**: la papelera, los
  temporales y los archivos recientes ahora listan CUALQUIER tipo de archivo
  (un .zip, un .pdf, una foto). Antes se llamaba "Recuperar archivos perdidos"
  pero solo encontraba archivos de Office
- **Archivos de la papelera con el nombre completo**: Windows viene de fabrica
  ocultando la extension de los archivos conocidos, y eso hacia que algunos
  archivos borrados no aparecieran en la busqueda. Ahora la extension se lee
  del archivo real, sin importar como este configurado Windows
- **El reporte de error ya no se pierde**: si la app truena, el archivo con los
  detalles queda junto al programa y no en una carpeta temporal que Windows
  borra al cerrar

### Cambiado
- **Una sola forma de limpiar**: el orden en que se borra, que cuenta como
  espacio liberado y que hacer si algo falla ahora viven en un solo lugar, en
  vez de estar duplicados entre el menu de texto y las ventanas. Menos
  probabilidad de que las dos versiones se comporten distinto
- **La ventana no se deja cerrar a media limpieza**: avisa y espera a terminar,
  para no dejar el trabajo por la mitad sin que te enteres

## [2.3.8] - 2026-07-20

Se cierran los dos hallazgos que quedaban abiertos de la auditoria del 19 de
julio: el rescate desde la papelera, que nunca llegaba a recuperar nada, y el
monto del subsidio al empleo, que estaba mal calculado.

### Corregido
- **Recuperar un archivo de la papelera ya funciona**: la app encontraba el
  archivo, lo mostraba en la tabla y al intentar recuperarlo decia "el archivo
  ya no existe". El motivo es que un archivo borrado no esta en la carpeta de
  donde salio, sino guardado con otro nombre dentro de `$Recycle.Bin`; ahora la
  copia se hace desde ahi. La tabla sigue mostrando la ruta original (que es la
  que uno reconoce) pero la recuperacion usa la ubicacion real
- **Subsidio al empleo 2026: monto incorrecto**: se usaba $536.22, que no
  corresponde a ningun periodo — parece el monto de enero ($536.21) con un
  digito cambiado. El Decreto DOF 31/12/2025 no fija pesos sino una formula:
  15.02% del valor mensual de la UMA, o sea $3,566.22 x 15.02% = **$535.65**
  vigente de febrero a diciembre. El transitorio de enero usaba 15.59% porque
  la UMA nueva entra en vigor hasta el 1 de febrero. Ademas el comentario del
  codigo afirmaba que 15.02% y 15.59% daban el mismo monto, lo cual es
  aritmeticamente imposible
- **Mensaje mas claro al no poder recuperar**: antes decia "el archivo ya no
  existe en: C:\..."; ahora explica que puede que se haya vaciado la papelera

### Cambiado
- **El subsidio al empleo se calcula, ya no se escribe a mano**: se deriva del
  valor de la UMA en `config.py` en vez de estar fijo en pesos, para que al
  actualizar la UMA del proximo anio el subsidio se mueva solo en lugar de
  quedarse congelado en un monto viejo

## [2.3.7] - 2026-07-20

Endurecimiento a partir de un premortem del proyecto: se cierra un flanco del
auto-actualizador, se advierte contra descargas falsas y se refuerza el aviso
de las calculadoras fiscales.

### Seguridad
- **Auto-actualizador**: ahora RECHAZA instalar una actualizacion si el Release
  no incluye un hash SHA-256 de referencia para verificarla (antes se instalaba
  "con precaucion"). El Escritorio solo se toca con un `.exe` verificado
- **Aviso de origen oficial**: al abrir, la app recuerda que el unico lugar de
  descarga legitimo es `github.com/ElBecerril/salva-godinez`, para no caer con
  copias falsas distribuidas por terceros con el mismo nombre

### Cambiado
- **Calculadoras fiscales/laborales**: el aviso ahora deja claro que es una
  ESTIMACION (no lo que legalmente te deben), lista los casos que NO modela
  (comisiones, salario variable, bonos, convenios, antiguedad interrumpida) y
  remite a las instancias oficiales gratuitas: PROFEDET (laboral) y SAT
  (impuestos)

## [2.3.6] - 2026-07-19

Version de robustez a partir de una auditoria completa: se blindan los puntos
donde un dato inesperado (un corchete en un nombre de archivo, un acento en la
salida de Windows) podia tumbar una herramienta, y se agrega una confirmacion
que faltaba antes de un borrado.

### Seguridad
- **Limpiar la cola de impresion** (destrabar impresora) ahora pide una
  confirmacion explicita antes de borrar: cancela las impresiones pendientes de
  TODOS los usuarios de la PC y es irreversible; antes lo hacia sin preguntar

### Corregido
- **Crash por caracteres especiales en nombres**: un archivo, carpeta, USB o
  etiqueta con un corchete (`[`) en el nombre tumbaba la vista por el markup de
  la consola. Se blindaron todos los puntos que muestran datos externos: el
  reporte de archivos encontrados (el flujo principal), el desinfectante de USB,
  el estado de USB, el desbloqueo de archivos, el respaldo a USB y las unidades
  de red
- **Crash por acentos en Windows en espanol**: cinco comandos de sistema
  (desbloqueo de archivos, estado de USB, desinfeccion) podian fallar al leer
  salida con caracteres no-ASCII; ahora la decodifican de forma tolerante
- El mensaje "no hay archivos para limpiar" del liberador de espacio vuelve a
  aparecer cuando de verdad no queda nada (papelera incluida)

### Cambiado
- La confirmacion de "Expulsar USB" ya no viene con "si" por defecto

## [2.3.5] - 2026-07-18

Correccion de dos bugs reportados en uso real.

### Corregido
- **Liberar espacio / Papelera**: el resumen mostraba "Archivos eliminados: 0"
  y "Espacio liberado: 0.0 B" aunque la papelera si se vaciaba (la API de
  vaciado no devuelve conteo). Ahora se consulta el tamano y el numero de
  archivos de la papelera (SHQueryRecycleBin) antes de vaciarla, y el resumen
  refleja lo que realmente se libero; la tabla tambien muestra cuanto ocupa la
  papelera antes de limpiar
- **Expulsar USB con seguridad**: no expulsaba la unidad y, en Windows en
  espanol, abria la carpeta en vez de expulsar (el verbo "Eject" del Shell no
  coincide con el localizado). Se reemplazo por la secuencia estandar de
  Windows (bloquear, desmontar y expulsar via DeviceIoControl); si la unidad
  esta en uso, ahora lo indica claramente

## [2.3.4] - 2026-07-18

Version de usabilidad: menos jerga tecnica visible, busqueda de archivos
perdidos mas directa, e instrucciones para abrir el .exe cuando Windows lo
marca como desconocido.

### Cambiado
- **Menos jerga tecnica en pantalla**: "shadow copies (VSS)" ahora se llama
  "copias de seguridad automaticas de Windows" (en los mensajes de busqueda y
  en la columna de origen de cada resultado); la columna "Driver" de las
  tablas de impresoras pasa a "Controlador"
- **Buscar archivos perdidos mas directo**: la opcion 1 es ahora "Buscar mi
  archivo por nombre (recomendado)", que revisa todos los lugares de una vez;
  las busquedas de un solo lugar (papelera, temporales, recientes) quedan
  agrupadas bajo "Busqueda avanzada". Se elimino una opcion que duplicaba a
  la busqueda completa
- Al pedir el nombre del archivo, si se deja vacio ahora se vuelve a preguntar
  y se ofrece "0 para volver", en vez de sacar al usuario del flujo

### Agregado
- Instrucciones en el README para abrir el .exe cuando aparece "Windows
  protegio tu PC" (SmartScreen), y que hacer si el antivirus lo marca como
  falso positivo

## [2.3.3] - 2026-07-17

Version de usabilidad: nombres de menu mas claros para gente sin
conocimientos tecnicos, e icono propio en el ejecutable.

### Cambiado
- **Nombres de menu orientados al problema**, sin jerga tecnica. Las
  categorias pasan de apodos ("El Rescatista", "El Doctor", "El Escudo",
  "El Conserje") a nombres descriptivos: "Recuperar y arreglar archivos
  (Word/Excel)", "Arreglar impresoras", "USB, WiFi y Red", "Limpieza y
  mantenimiento", "Calculadoras y herramientas"
- Sub-items renombrados a lo que el usuario quiere lograr, no al mecanismo
  tecnico: "Reset de Spooler" -> "Destrabar impresora atascada"; "Limpiador
  de Fantasmas" -> "Quitar impresoras duplicadas"; "Consolidador de Libros"
  -> "Unir varios Excel en uno"; "Mapeo de Unidades de Red" -> "Conectar
  carpetas de red"; "Verificador de Conexion" -> "Probar si la impresora
  responde"; "Limpiador de Celdas" -> "Quitar espacios que rompen formulas";
  "Recuperador de WiFi" -> "Ver contrasenas WiFi guardadas"; y mas
- Los encabezados internos de cada herramienta y el README se sincronizaron
  con los nombres nuevos

### Agregado
- **Icono propio** del ejecutable (taza de cafe, acorde al banner), en
  resoluciones 16/32/48/64/128/256 para verse nitido en barra de tareas y
  escritorio (antes usaba el icono generico de Python)

## [2.3.2] - 2026-07-17

Segunda auditoria completa (interna): 5 agentes en
paralelo por area + verificacion manual y funcional de los fixes. Sin
vectores de inyeccion (cero shell=True/eval); todos los fixes de la auditoria
previa siguen en pie.

### Seguridad
- Liberador de Espacio: un Enter ya no borra nada por defecto; vaciar la
  papelera y borrar descargas antiguas (ambos permanentes e irreversibles)
  ahora exigen una confirmacion explicita separada
- Desinfectante de USB: ya no borra en bloque los ejecutables sueltos
  legitimos (.exe/.bat/etc.); solo elimina automaticamente las amenazas de
  riesgo alto conocidas, los demas se listan para revision manual
- Limpiador de Impresoras Fantasma: una impresora legitima renombrada "(N)"
  ya no se borra en bloque; el borrado requiere seleccion e confirmacion
- Auto-updater: mueve el nuevo .exe ANTES de borrar las versiones anteriores
  del Escritorio (si el move falla, no te quedas sin nada); aborta si la
  descarga viene incompleta o excede un tamano maximo; el hash se ata al
  nombre del archivo correcto
- Contrasenas WiFi: el modo enmascarado ya no revela el primer/ultimo
  caracter; SSID y claves con caracteres especiales ya no rompen ni falsean
  la vista (escape de markup)
- Verificador de conexion (ping): rechaza destinos que empiecen por `-`/`/`

### Corregido
- Sueldo Neto: la base del ISR ya no resta el IMSS (las cuotas obrero no son
  deducibles de la base, Art. 96 LISR) — antes subestimaba el ISR y pagaba de
  mas; el subsidio al empleo ya no vuelve negativo el ISR ni se entrega en
  efectivo (esquema 2026)
- Simulador de Prestaciones: el finiquito por renuncia ahora incluye la prima
  de antiguedad con 15+ anios (Art. 162-III LFT); la indemnizacion de 20
  dias/anio usa el salario diario integrado (SDI, Art. 89); el aguinaldo topa
  los dias trabajados a 365
- Editor de PDF: un PDF con contrasena ya no tumba la app (rotar, eliminar,
  reordenar, extraer texto, metadatos); un PDF cifrado en una union se salta
  en vez de abortar todo; imagenes enormes ya no crashean al convertir a PDF
- Limpiador de Celdas: un Excel corrupto o cifrado ya no tumba la app; la
  salida no sobrescribe un archivo previo
- Consolidador de Libros: ya no puede sobrescribir un archivo de entrada; los
  guardados no crashean si el archivo esta abierto en Excel; avisa que las
  formulas se convierten a valores; no genera .xlsm corruptos
- Comparador de Excel: el reporte no sobrescribe silenciosamente otros
  archivos existentes
- Mapeo de Unidades de Red: la ruta remota y el estado se leen bien en
  Windows en espanol (antes mostraban basura y todo en amarillo)
- Impresoras (compartir/fantasma): los nombres con caracteres no-ASCII ya no
  crashean el listado (encoding); los datos externos se escapan para Rich
- Conversor de Imagenes: respeta la orientacion EXIF (fotos de celular ya no
  salen giradas) y avisa cuando un GIF/TIFF multipagina pierde frames
- Restaurar archivo encontrado: acceso defensivo para no crashear si faltan
  metadatos

### Cambiado
- Verificador de USB: una memoria legitima casi llena ya no se reporta como
  "posible USB falsa"; se distingue "no se pudo completar la prueba"
- Desbloquear archivos: cuando el metodo de respaldo no puede determinar el
  proceso, lo dice honestamente en vez de afirmar que el archivo esta libre
- config.py: se descartan rutas de limpieza no absolutas (defensa si faltan
  variables de entorno)
- CI: PyInstaller pineado a 6.21.0 y las GitHub Actions pineadas por SHA de
  commit (hardening de cadena de suministro)

## [2.3.1] - 2026-07-15

Auditoria completa del proyecto (bugs reales, riesgo de perdida de datos y
formulas fiscales/laborales incorrectas), con verificacion adversarial y
correccion de todos los hallazgos criticos, altos y medios.

### Seguridad
- USB Desinfectante: el prompt de "eliminar amenazas" ya no borra por
  defecto al presionar Enter; el escaneo ahora es recursivo (antes solo
  revisaba la raiz) y los ejecutables sueltos bajan de riesgo "Alto" a
  "Medio" para reducir falsos positivos
- Auto-updater: ahora descarga y verifica el SHA-256 ANTES de borrar la
  version anterior del Escritorio (antes borraba primero, arriesgando dejar
  al usuario sin ejecutable si la descarga fallaba)
- Editor de PDF: la contrasena para proteger un PDF ya no se muestra en
  pantalla (input oculto)

### Corregido
- Prima de antiguedad (Simulador de Prestaciones): topaba con 2x UMA en vez
  de 2x salario minimo (Art. 162/486 LFT), subestimando liquidaciones reales
- Vacaciones de 21 a 24 anios de antiguedad: calculaban 0 dias extra por un
  error de formula, ahora dan los 28 dias correctos (LFT Art. 76)
- Calculadora de Retenciones RESICO: usaba un modelo marginal incorrecto en
  vez de tasa fija sobre el ingreso total (Art. 113-E LISR)
- Calculadora de Sueldo Neto: el SBC ahora topa a 25 UMA mensuales (Art. 28
  LSS) y se agrego el subsidio al empleo 2026 (monto unico $536.22/mes segun
  Decreto DOF 31/12/2025, reemplaza la tabla obsoleta de 2013)
- Papelera de reciclaje: la restauracion nunca funcionaba y la busqueda
  colapsaba archivos distintos en uno solo porque solo se obtenia la carpeta
  original, no la ruta completa del archivo
- Limpiador de Celdas: los archivos .xlsm perdian sus macros al procesarlos
  (faltaba `keep_vba=True`); las formulas ya no se alteran al limpiar
- Respaldo Rapido a USB: los archivos que fallaban al copiarse se ignoraban
  en silencio; ahora se cuentan y se reportan al final
- Expulsion Segura USB: reportaba exito sin verificar que la unidad
  realmente se hubiera expulsado; ahora lo confirma antes de avisar
- Editor de PDF: ninguna operacion (unir, dividir, rotar, etc.) protegia
  contra sobrescribir el archivo de salida por accidente
- Verificador de Conexion VSS (busqueda por shadow copies): el parser de
  fecha nunca coincidia con el formato real de `vssadmin`, siempre mostraba "?"
- Verificador de USB: el chequeo de chkdsk daba falso positivo permanente
  (la palabra "bad"/"problema" aparece incluso en el mensaje de un disco
  sano); el test de autenticidad de USB solo probaba el primer MB, ahora
  prueba varios puntos de la capacidad reportada
- Comparador de Excel: un archivo corrupto tumbaba toda la aplicacion; el
  reporte podia sobrescribir accidentalmente el archivo original
- Consolidador de Libros: el modo "unir hojas" descartaba la primera fila de
  cada hoja asumiendo encabezado, ahora avisa y permite evitarlo
- Mapeo de Unidades de Red: el orden de argumentos de `net use` con
  credenciales no seguia la sintaxis estandar de Windows
- Reset de Spooler: ahora verifica el estado real del servicio tras
  reiniciarlo en vez de asumir exito
- Limpiador de Impresoras Fantasma / Compartir en Red: distingue "no hay
  impresoras instaladas" de un error real al consultarlas; deteccion de
  impresoras fantasma ampliada (sufijos numericos, impresoras redirigidas)
- Varios modulos (WiFi, Mapeo de Red, Ping) podian crashear con caracteres
  no-UTF8 en la salida de comandos de Windows en espanol

### Cambiado
- Salario minimo diario 2026 actualizado a $315.04 (CONASAMI/DOF 09/12/2025)
- Se agrego una advertencia en tiempo de ejecucion si las tablas fiscales
  (ISR, UMA, RESICO) quedan desactualizadas para el anio en curso
- Normalizado el fin de linea a LF en todo el repositorio (`.gitattributes`)
  para evitar diffs espurios entre sesiones editadas en distinto SO

## [2.3.0] - 2026-02-18

### Agregado
- **Rotar Paginas** — Rota todas o paginas especificas 90°, 180° o 270°
- **Eliminar Paginas** — Elimina paginas por indice (1,3,5 o 2-4)
- **Reordenar Paginas** — Cambia el orden de las paginas del PDF
- **Extraer Texto** — Extrae todo el texto del PDF a un archivo .txt UTF-8
- **Imagenes a PDF** — Convierte JPG/PNG/BMP/WEBP a PDF (soporta transparencia RGBA)
- **PDF a Imagenes** — Renderiza cada pagina como PNG/JPG con DPI configurable (requiere PyMuPDF)
- **Proteger/Desproteger PDF** — Agrega o quita password de un PDF
- **Ver/Limpiar Metadatos** — Muestra titulo, autor, fechas y permite limpiar metadatos
- Helpers reutilizables: `_get_pillow()`, `_get_pymupdf()`, `_open_pdf_reader()`, `_parse_page_selection()`
- PyMuPDF como dependencia opcional en requirements.txt (solo para PDF a Imagenes)

### Cambiado
- Menu de Herramientas PDF expandido de 2 a 10 opciones

## [2.2.2] - 2026-02-14

### Agregado
- Panel de despedida al salir con links a YouTube y Facebook para apoyar el proyecto
- Mensajes descriptivos en herramientas de unir/dividir PDF
- Seccion de bugs y sugerencias en README con links a redes

### Corregido
- Auto-updater: ahora elimina versiones anteriores del Escritorio antes de descargar la nueva
- CONTRIBUTORS: link al perfil de GitHub y descripcion actualizada
- Eliminar datos personales del codigo (rutas hardcodeadas, ruta absoluta en .spec)

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
