# Parches científicos de Marte: selección y escala

Revisión local del 14 de noviembre de 2026, America/Bogota. Base de trabajo:
`c3ec4c1f1515dbc981ba82eed2ab1f54e9586264`, `feat/mission`. Este dossier desarrolla
CONT-DAV-03: propone qué mapas solicitar, sin cambiar el escenario aprobado,
los perfiles, contratos o implementaciones de otros módulos. No es una misión
ejecutada, una nueva detección ni una aprobación científica. Se conserva local
durante la auditoría de conciliación, sin commits, pushes ni merges.

## Decisión propuesta

**Conservar 128 × 128 m como control y ventana de trabajo; ampliar el contexto
científico a 512–1.024 m para los primeros candidatos de Jezero.** No es
imperativo sustituir inmediatamente el mapa operativo por uno kilométrico.
Sí hace falta contexto mayor para representar un valle, varios lóbulos de un
delta o una meseta, y para escoger una estación local con una pregunta científica.

La primera solicitud a Daniel sería **Bright Angel–Neretva Vallis**, seguida
por **Hawksbill Gap–Hogwallow Flats** y **Bunsen Peak–Margin Unit**. Mawrth Vallis
es la primera alternativa fuera de Jezero si se decide abrir otra región.
Se proponen tamaños de diseño, no tamaños prescritos por NASA. La
[solicitud de mapas](science_patch_map_requests.md) concreta productos,
anclas de búsqueda y condiciones para que Daniel genere los recortes.

No se ha demostrado que el B actual pertenezca a un afloramiento de interés.
Su aprobación como punto experimental no se convierte en una identificación
geológica. Tampoco se trasladan las nuevas regiones a `mission_jezero.experimental.yaml`.

## Qué se buscó y qué cuenta como evidencia

Se revisaron publicaciones primarias de NASA/JPL, USGS, equipos de instrumentos
y artículos originales sobre sectores de Jezero y alternativas de Gale,
Mawrth, NE Syrtis, Nili Fossae, Eberswalde, Holden, Oxia, Gusev y Meridiani.
El resultado son **17 sectores candidatos**: seis de Jezero y once alternativas
o reservas, con fuentes y límites de interpretación en dos catálogos:

- [Jezero: seis sectores y sus fuentes](../evidence/science-patch-survey-20261114/jezero_candidates.proposed.json).
- [Alternativas: once sectores y sus fuentes](../evidence/science-patch-survey-20261114/alternative_candidates.proposed.json).

Es una búsqueda amplia y dirigida, no un inventario exhaustivo de Marte ni una
comparación estadística de todos sus lugares de interés. Se distinguen:

| Nivel | Qué permite afirmar | Qué no permite afirmar |
|---|---|---|
| Publicación de instrumentos en superficie | Existe una observación científica histórica en ese lugar | Nuestro agente la midió o puede reproducirla con sus sensores actuales |
| Interpretación orbital o geológica publicada | Hay una hipótesis espacial que merece inspección | Cada celda contiene ese mineral, o el terreno es transitable |
| Propuesta de misión de este dossier | Conviene buscar ciertos contrastes y obtener un mapa | Existe un POI ejecutable, una tarea asignada o una detección futura garantizada |

Los objetivos históricos conocidos no deben anunciarse como descubrimientos
inesperados de nuestro sistema. Las oportunidades secundarias del catálogo
orientan la selección del escenario; no son una lista oculta de tareas que se
carga al núcleo. Cualquier hallazgo de una ejecución necesitará entradas
públicas tipadas, procedencia y evidencia recibida.

## Primera lista: Jezero

| ID | Sector y pregunta | Potencial durante un recorrido local | Contexto propuesto / ventana de trabajo | Límite decisivo |
|---|---|---|---|---|
| JZ-ROI-01 | **Bright Angel–Beaver Falls, Neretva Vallis**: relaciones entre lutitas, materiales granulares, contactos y alteración | Comparar texturas, capas y fracturas en un mismo workspace; estudiar contrastes hacia Walhalla Glades o Grapevine Canyon | **512 y 1.024 m / 128–256 m** | El valle tiene unos 400 m de ancho; una caja de 128 m no representa sus dos márgenes. No todos los blancos cabrán en la misma caja. |
| JZ-ROI-02 | **Hawksbill Gap–Hogwallow Flats**: cambios de facies y estratigrafía del frente deltaico | Laminación, vetas, clastos y diferencias entre afloramientos próximos | **512 y 1.024 m / 128–256 m** | La aptitud para muestrear cambia entre rocas; la topografía no demuestra estabilidad mecánica. |
| JZ-ROI-03 | **Cape Nukshak–Enchanted Lake**: relación del delta con el suelo del cráter | Contactos visibles frente a contactos cubiertos, exposición desigual y cambios laterales | **1.024 m / 128–256 m** | Hay contactos interpretados con radar; una cámara no los descubre directamente. |
| JZ-ROI-04 | **Bunsen Peak–Margin Unit**: interacción roca–agua y diversidad de materiales carbonatados/silíceos | Contrastar roca masiva, fracturas y materiales adyacentes antes de elegir muestra | **512 m / 128–256 m** | Composición histórica confirmada con instrumentos; el origen del depósito no se resuelve por aspecto o DEM. |
| JZ-ROI-05 | **Krokodillen–Laknes/Strong Island**: materiales antiguos y variación de alteración | Buscar diferencias entre exposiciones; evitar suponer arcillas uniformes | **1.024 m / 128–256 m** | Cobertura al oeste por verificar; una meseta de unas 30 ha no queda representada por 1,64 ha. |
| JZ-ROI-06 | **Witch Hazel Hill–Broom Point–Tablelands**: rocas antiguas, impactos y alteración | Contrastes entre capas, bloques y superficies alteradas | **1.024–2.048 m / estación local por seleccionar** | Caso de alta ciencia y posible rechazo por acceso/recursos; no escogerlo como nominal humano sin validación. |

**Bright Angel es la primera opción por la combinación de evidencia y proximidad
de objetivos, no por una promesa de encontrar vida.** La comunicación de
[NASA/JPL de septiembre de 2025](https://www.jpl.nasa.gov/news/nasa-says-mars-rover-discovered-potential-biosignature-last-year/)
describe el interés del material y mantiene abiertas explicaciones abióticas.
[Murphy et al., 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13292988/) aportan
resultados sobre carbono orgánico complejo; su análisis Raman no determina un
origen biológico. Esto justifica comparar materiales y su contexto.

Las figuras de [Hurowitz et al., 2025](https://www.nature.com/articles/s41586-025-09413-0)
documentan blancos próximos y un workspace con varios objetivos. Las distancias
y anclas se detallan en la solicitud de mapas. Es una oportunidad de comparación,
sin demostrar rutas de ida/retorno ni acceso entre puntos.

Para el frente deltaico, el
[resumen SuperCam en NTRS](https://ntrs.nasa.gov/citations/20230000534) registra
unos 400 m entre Hawksbill Gap y Cape Nukshak. El
[estudio estratigráfico de Stack et al.](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023JE008187)
separa datos de superficie e interpretación del subsuelo. Las
[operaciones publicadas de la campaña](https://ntrs.nasa.gov/api/citations/20230000588/downloads/Williams%20et%20al_LPSC%202023%20Delta%20Front%20Overview%20abstract_v5.pdf)
también incluyen intentos de abrasión fallidos: un blanco interesante puede
ser inadecuado para trabajar. No se usa una cifra de distancia de travesía mal
extraída del PDF como dato cuantitativo.

[Comet Geyser](https://science.nasa.gov/blog/comet-geyser-perseverances-21st-rock-core/)
apoya el interés de Bunsen Peak y mantiene abierta la interpretación de origen.
En Krokodillen, la
[descripción de NASA](https://www.nasa.gov/missions/mars-2020-perseverance/perseverance-rover/nasas-perseverance-mars-rover-to-take-bite-out-of-krokodillen/)
da la escala de la meseta, mientras una
[actualización posterior](https://science.nasa.gov/blog/clay-minerals-from-mars-most-ancient-past/)
señala variación en las firmas de arcillas. Una caja de 128 m cubre 1,6384 ha,
aproximadamente el 5,46 % de 30 ha; esa fracción geométrica no mide cuánto
interés científico contiene. Una caja de 512 m tiene 26,21 ha y tampoco asegura
cubrir la forma irregular del afloramiento.

La [descripción del borde de Jezero](https://www.nasa.gov/missions/mars-2020-perseverance/perseverance-rover/nasas-perseverance-mars-rover-studies-trove-of-rocks-on-crater-rim/)
incluye una ladera de 135 m de altura. El
[estudio de Broom Point de julio de 2026](https://doi.org/10.1029/2026JE009779)
analiza espesor estratigráfico; espesor, desnivel y longitud de recorrido no son
intercambiables. Este sector sirve para estudiar límites de acceso, no para
dar por aprobada una excursión humana.

## Alternativas y controles científicos

| ID | Sector | Pregunta y oportunidades secundarias | Selección de escala propuesta |
|---|---|---|---|
| ALT-ROI01 | **Yellowknife Bay, Gale** | Comparar Sheepbed, Gillespie Lake y Point Lake: facies, granulometría y erosión | Estación 128–256 m, contexto 512–1.024 m. Hay afloramientos interesantes a decenas de metros en la [imagen oficial](https://science.nasa.gov/photojournal/view-of-yellowknife-bay-formation-with-drilling-sites/). |
| ALT-ROI02 | **Pahrump Hills, Gale** | Estratificación basal de Murray; relación con arena y materiales erosionados | Ventana 256–512 m, contexto 512–1.024 m. Los 18 m de la [descripción NASA](https://science.nasa.gov/resource/curiosity-mars-rovers-approach-to-pahrump-hills/) son sección vertical, no un recorrido. |
| ALT-ROI03 | **Glen Torridon, Gale** | Cambios sedimentarios y alteración diagenética hacia el pedimento | Estación 256–512 m dentro de 1–2 km de contexto. La [campaña publicada](https://ntrs.nasa.gov/api/citations/20230001618/downloads/JGR%20Planets%20-%202022%20-%20Bennett%20-%20The%20Curiosity%20Rover%20s%20Exploration%20of%20.pdf) recorrió 5 km; una estación no representa toda la campaña. |
| ALT-ROI04 | **Tributario de Mawrth Vallis** | Capas con distinta mineralogía y manto oscuro; contactos y ventanas erosivas | Primera alternativa de importación fuera de Jezero: contexto 2.048 m y subventanas. Hay [DTM de 1 m y ortoimágenes identificados](https://hirise.lpl.arizona.edu/dtm/PSP_002074_2025); falta recorte validado y reparto de datos. |
| ALT-ROI05 | **Contacto antiguo de NE Syrtis** | Basamento/megabrechas, unidades superpuestas y alteración | Contexto de 2.048 o 4.096 m; estación 512–1.024 m por localizar. La [ficha de selección JPL](https://marsnext.jpl.nasa.gov/documents/LandingSiteWorksheet_NESyrtis_final.pdf) es contexto científico; el catálogo DTM no basta para demostrar cobertura. |
| ALT-ROI06 | **Exposición olivino–carbonato de Nili Fossae** | Contrastar minerales y su orden estratigráfico; materiales de cobertura | Contexto regional de varios km; subventana 512–1.024 m. La [composición publicada](https://science.nasa.gov/photojournal/carbonate-olivine-relationship-in-nile-fossae-mars/) usa CRISM e HiRISE, no el DEM. |
| ALT-ROI07 | **Lóbulo deltaico de Eberswalde** | Canales invertidos, frente erosionado y arquitectura de depósitos | Contexto regional mayor y ventana 512–2.048 m. La [ficha JPL](https://marsnext.jpl.nasa.gov/documents/LandingSiteWorksheet_Eberswalde_final.pdf) describe un delta de 10 × 10 km; existe un [DTM identificado](https://www.uahirise.org/dtm/dtm.php?ID=ESP_016065_1560), cuya huella debe cruzarse con el lóbulo elegido. |
| ALT-ROI08 | **Depósitos estratificados del SW de Holden** | Capas finas bajo materiales aluviales, variación lateral y contactos | Contexto de 2.048 o 4.096 m, estación 512–1.024 m. Las capas se siguen cientos de metros a km en la [descripción primaria](https://science.nasa.gov/photojournal/a-closer-look-at-holden-crater/). |
| ALT-ROI09 | **Oxia Planum** | Arcillas, canales y contacto con cobertura posterior | Reserva de investigación. La [fuente ESA](https://www.esa.int/articles/oxia-planum-favoured-for-exomars-surface-mission) sustenta geología, no su antiguo calendario de lanzamiento. DTM concreto pendiente. |
| ALT-ROI10 | **Home Plate, Gusev** | Alteración e indicios hidrotermales; contraste de suelo claro y afloramientos | Reserva de contexto 512–1.024 m. [Spirit encontró material rico en sílice](https://www.jpl.nasa.gov/news/mars-rover-investigates-signs-of-steamy-martian-past/) durante operaciones: buen análogo de oportunidad incidental, cuya composición requirió instrumentos. |
| ALT-ROI11 | **Aproximación a Endurance/Burns Cliff, Meridiani** | Estratos y procesos de depósito/alteración; oportunidad de inspeccionar y rechazar accesos | Contexto 512–1.024 m, estación periférica por verificar. El [registro NASA](https://science.nasa.gov/photojournal/endurance-crater-overview/) documenta accesos y dunas que no se cruzaron por seguridad. |

En Mawrth, el equipo HiRISE describe colinas de aproximadamente 1,6 km y
publica el producto `DTEEC_002074_2025_002140_2025_U01`. El centro indicado,
22,45° N / 341,7° E, es **del producto**, no un POI ni una base. La existencia
del DTM no aprueba consumirlo como prior si ese mismo producto se reserva a
evaluación. Esta distinción también afecta a los DTMs públicos de Eberswalde.

## Qué representa realmente el recorte actual

El [manifiesto público](../data/sample/manifest.json) y la
[configuración de terreno](../config/terrain.yml) fijan origen aproximado
18,45° N / 77,45° E, 32 × 32 celdas a 4 m y DTM CTX nativo de 20 m. La
[auditoría reproducible](../evidence/science-patch-survey-20261114/scale_assessment.json)
conserva hashes del Git y de los archivos realmente leídos. El paquete tiene
0 celdas NoData y 0 observadas al inicio, con sigma declarado de 2,5 m.
Validez del paquete, precisión física y evidencia de recorrido son conceptos distintos.

| Lado del recorte | Rejilla a 4 m | Celdas | Lado / separación nativa de 20 m | Carga de celdas relativa |
|---:|---:|---:|---:|---:|
| 128 m | 32 × 32 | 1.024 | 6,4 | 1× |
| 256 m | 64 × 64 | 4.096 | 12,8 | 4× |
| 512 m | 128 × 128 | 16.384 | 25,6 | 16× |
| 1.024 m | 256 × 256 | 65.536 | 51,2 | 64× |
| 2.048 m | 512 × 512 | 262.144 | 102,4 | 256× |

**128 × 128 celdas a 4 m equivalen a 512 × 512 m**. La relación 128/20 no
cuenta píxeles independientes: la extracción usa margen, interpolación y una
ventana fuente mayor. Tampoco 1.024 celdas computacionales implican 1.024
mediciones topográficas independientes. La
[documentación CTX de USGS](https://astrogeology.usgs.gov/docs/concepts/missions/mro/ctx-data/)
se refiere a imágenes de unos 6 m/píxel; no convierte en 6 m este DTM de 20 m.

Un recorte de 128 m puede contener una estación valiosa y varios blancos
pequeños. No representa por defecto la diversidad de una región ni identifica
materiales milimétricos. Ampliarlo aumenta contexto y número de celdas, pero
no mejora la resolución nativa ni elimina errores de registro. La escala del
mapa geológico SIM 3464 es 1:75.000; el repositorio advierte desplazamientos
entre bases cartográficas que requieren revisión. Los 100–200 m mencionados
en el informe no se adoptan aquí como sigma universal validada de contactos.

La representatividad debe definirse respecto a la pregunta: una estación,
un contacto o una secuencia de facies. Un mapa mayor tampoco garantiza esa
representatividad. Para generalizar resultados de navegación harán falta varios
recortes seleccionados con criterios explícitos, no solo el lugar más vistoso.

## Mapa, alcance y recursos son tres escalas distintas

Con los presupuestos aprobados y los perfiles aún propuestos, el cálculo sobre
plano da estos **techos ideales de desplazamiento de ida con vuelta por el mismo
trayecto**, después de servicio, espera y reserva:

| Agente | Servicio/espera usados | Techo ideal de ida, aproximado | Limitante |
|---|---|---:|---|
| Humano | 120 s de observación/check-in visual, costeado como trabajo ligero, + 60 s de espera | 222,98 m | Energía metabólica |
| Rover | 120 s de inspección + 60 s de espera | 14,04 m | Tiempo |
| Dron | 30 s de observación suspendida + 10 s en tierra | 103,57 m | Energía eléctrica |

Se calcula el coste de un metro con `estimate_segment`; para cada recurso se
restan reserva y costes estacionarios, se divide por dos veces el coste por
metro y se escoge el mínimo. No se acepta una ruta en el límite ni se concede
crédito por redondeo. Añadir 180 s de adquisición pesada al humano reduce su
techo ideal a unos 140,18 m. El dron excluye despegue, ascenso, descenso,
aterrizaje y obstáculos; los demás excluyen pendientes, desvíos y retrasos extra.
No son círculos de alcanzabilidad, coberturas de sensor ni límites físicos certificados.

Por tanto, **un contexto de 1 km no autoriza una misión de 1 km**. El rover
actual solo puede trabajar muy cerca de su estación con esta asignación.
No se aumentan velocidades o presupuestos para hacer caber un lugar atractivo.
Reubicar estaciones, cambiar consumibles o revisar duración de tareas exige
otra propuesta y aprobación. Las reservas se conservan intactas.

## Cómo crear oportunidades secundarias defendibles

Para el primer caso propongo una pregunta principal sobre un afloramiento y
contrastes secundarios del mismo entorno: textura/capa distinta, contacto
parcialmente cubierto o un corredor alternativo que merece observación. El
reconocimiento decide dónde inspeccionar; la inspección fundamenta cualquier
muestreo posterior a B. Una roca lejana de alto interés puede quedar rechazada
si compromete retorno, precedencias o reservas.

La misión necesita discriminar **interés científico**, **información para decidir**
y **viabilidad**. La ciencia puede ordenar candidatos que ya cumplen las
restricciones; no compensa una violación de recursos o un tramo injustificado.
No se asignan porcentajes de descubrimiento, entropías de minerales ni pesos
de utilidad llamados oficiales sin un modelo de detección y datos para estimarlos.

Para comparar A/B/C se mantiene el mismo recorte, estado inicial, capacidades,
POIs admisibles, presupuestos y semillas. Cambiar a la vez tamaño y estrategia
confundiría los efectos. Se registran propuestas, detecciones reales recibidas,
omisiones y rechazos. La estrategia informativa puede gastar más sin mejorar
el resultado; el estudio no presupone que C venza a B o que B tenga coste cero.

## Ajustes necesarios al informe de partida

| Afirmación del informe | Criterio que se usará en esta propuesta |
|---|---|
| CTX DEM a 6 m | Separar imagen CTX 6 m, DTM entregado 20 m y rejilla 4 m. |
| El delta de Jezero mide 45 km | Ese orden de tamaño describe el cráter; comprobar la dimensión del rasgo concreto. |
| No hay atmósfera fina que limite al dron | Marte tiene atmósfera muy tenue: la [ficha de Ingenuity](https://www.jpl.nasa.gov/news/press_kits/ingenuity/landing/quick_facts/) da aproximadamente el 1 % de la densidad terrestre superficial. No se modela vuelo certificado. |
| CTX/DEM detectan arcillas o carbonatos | CTX aporta morfología; la mineralogía requiere espectros u otros instrumentos. [CRISM](https://www.jhuapl.edu/destinations/instruments/crism) es un ejemplo de la fuente pertinente. |
| Observado es irrevocable; no transitado es otro estado de conocimiento | Una observación puede corregirse o contradecirse. Haber transitado es una propiedad distinta de haber observado. Se conserva procedencia temporal. |
| Pendiente orbital baja implica seguro; usar umbrales EDL como criterio de marcha | La selección de aterrizaje no certifica EVA, rodadura o suelo. No importar un umbral de 20° o 30° como límite operativo nuevo. |
| Llanura basáltica equivale a bajo interés | Puede aportar cronología, petrogénesis y controles de comparación. El valor depende de la pregunta científica. |
| Terreno desconocido en cierto porcentaje exige un veto universal | Distinguir estimado válido, NoData y observación. D-EST-01 permite propuesta hipotética; no crear un umbral sin justificación ni declarar implementación cerrada. |
| Un modelo de terreno fino equivale a validación de rocas o suelo | Ni siquiera un DTM de 1 m demuestra cohesión, fricción, deslizamiento o peligros decimétricos. |
| Los ejemplos de misión del informe son resultados del proyecto | Son narraciones hipotéticas. Solo una ejecución con evidencias puede sostener esos resultados. |

Los objetivos de ciencia y diversidad se apoyan en los
[criterios científicos de Mars 2020](https://www.jpl.nasa.gov/news/press_kits/mars_2020/launch/mission/science/).
Los pesos, tamaños y priorización de este dossier son propuestas propias.
La precisión geométrica y la seguridad se revisan por separado.

## Datos y límites de acceso

[Mars Trek](https://trek.nasa.gov/mars/) y los
[recursos de cartografía USGS](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars)
son puntos de partida oficiales. Sus páginas dinámicas no permitieron extraer
todos los detalles en este navegador. Se complementaron con páginas de producto,
publicaciones y catálogos. La
[ruta ilustrada de Curiosity](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/)
sirve como referencia de contexto multicapas; no es una ruta calculada para el
escenario. NASA Worldview corresponde a la Tierra y no suministra el terreno de Marte.

La [ampliación HiRISE de USGS de 2025](https://www.usgs.gov/data/mars-sample-return-hirise-mosaics-terrain-relative-navigation)
identifica nuevos DEM/ortoimágenes hacia el oeste de Jezero. Eso no prueba la
cobertura de cada caja. El acceso a parte de ScienceBase/DOI devolvió 403; no
se descargaron grandes productos ni se verificaron todos sus píxeles.
El folleto completo SIM 3464 también devolvió 403 en esta sesión; su escala y
referencia bibliográfica se comprobaron en metadatos oficiales. Las limitaciones
de acceso de NE Syrtis y de los dossiers PDS se conservan en los catálogos.

No se abrió `data/reference/` ni se extrajo detalle del evaluador para elegir
microobjetivos. Los productos HiRISE públicos se catalogan como posibles datos
de una futura partición acordada; no se incorporan al prior actual. Tampoco
las fotografías históricas de los rovers se convierten en observaciones del run.

El propietario indicó que Daniel dispone de herramientas para generar otros
recortes, pero todavía no de las entregas nuevas solicitadas.
Su rama publicada/cacheada se inspeccionó solo en lectura; no se integra ni
se sustituye su preparador. Tener parámetros de tamaño no prueba cobertura,
co-registro o rendimiento de los mapas futuros.

## Salida para revisión

La decisión solicitada después de revisar estos datos será qué **familia de
mapas** generar primero, no aprobar una misión ni anunciar descubrimientos.
La propuesta es comparar 128/256/512 m para integración, manteniendo 1.024 m
como contexto de selección cuando el rasgo lo requiera. El mapa contextual
puede consultarse aparte; no debe enviarse una rejilla grande al planificador
o al replay sin las comprobaciones de Daniel, Diego y Jesús.

Permanecen pendientes las coordenadas operativas A/B de cada escenario nuevo,
huella final, partición pública/evaluador, modelo de observación/instrumentos,
costes acordados, aprobación de perfiles y evidencias de ejecución. La aprobación
JZ-P01..07 del escenario original y sus restricciones permanecen intactas.
