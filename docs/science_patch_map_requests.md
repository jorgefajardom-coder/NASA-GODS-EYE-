# Mapas propuestos para Daniel

Solicitud científica local, 14 de noviembre de 2026. Deriva del
[barrido de 17 sectores](science_patch_survey.md), no sustituye el escenario
experimental aprobado ni modifica el preparador de datos. El propietario
confirmó que los nuevos recortes aún no están entregados: este documento
especifica qué generar y comprobar primero.

## Orden de entrega propuesto

| Orden | Mapa | Centro aproximado de consulta: latitud, longitud este | Contexto | Ventana anidada |
|---:|---|---|---|---|
| 0 | Control Jezero actual | Mantener el origen, datos y A/B aprobados | 128 m existentes | Sin cambios |
| 1 | **Bright Angel–Neretva Vallis / Beaver Falls** | **18,49680°, 77,30451°** | **512 y 1.024 m** | 128 y 256 m para escoger el workspace |
| 2 | **Hawksbill Gap–Hogwallow Flats** | **18,45835°, 77,40733°** | **512 y 1.024 m** | 128 y 256 m sobre la exposición elegida |
| 3 | **Bunsen Peak–Margin Unit** | **18,49182°, 77,32719°** | **512 m**; 1.024 m si la revisión exige más contexto | 128 y 256 m |
| 4, condicional | **Tributario de Mawrth Vallis** | El producto DTM indica **22,45°, 341,7°**; todavía no es centro de una ventana científica elegida | 2.048 m de estudio; recorte final por localizar | Elegir después de cruzar producto y rasgo |

Los tres primeros centros sirven para **buscar productos y revisar recortes**.
No son coordenadas exactas de un afloramiento, una base A, un objetivo B o una
pose del escenario. Los dígitos no expresan precisión de localización. Todas
las solicitudes permanecen `PROPOSED_NOT_READY` y las huellas verificadas son
`null`. El contexto tampoco prescribe un recorrido de esa longitud.

La versión [JSON de solicitudes](../evidence/science-patch-survey-20261114/map_requests.proposed.json)
conserva centros sin redondear, envolventes de consulta aproximadas y condiciones.
La [selección de anclas](../evidence/science-patch-survey-20261114/waypoint_anchors.selected.json)
conserva los cinco registros NASA originales utilizados y su procedencia.

## Cómo se obtuvieron las anclas

Se consultó el
[GeoJSON público histórico de NASA/MMGIS](https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json),
no una ruta del evaluador ni una ejecución de nuestro proyecto. El archivo
recibido contiene 708 features y se identifica por SHA-256
`bd143ee69241229926abd373e6305b8bbb326d6b5a7b4a8d6935262696f93dc4`.
Las asociaciones a la zona de interés son propuestas de selección, no una
localización instrumental verificada del núcleo de roca.

| Solicitud | Registros conservados | Relación con la literatura y cautela |
|---|---|---|
| Bright Angel | Sol 1177, RMC `54_0`; sol 1210, RMC `56_0`; centro como punto medio de sus latitudes/longitudes | La [publicación Nature](https://www.nature.com/articles/s41586-025-09413-0) muestra Walhalla Glades en sol 1178 (figura 1b) y Beaver Falls en sol 1217 (figura 2). Desde Walhalla Glades sitúa Beaver Falls a unos 110 m cuesta arriba y Grapevine Canyon a unos 50 m cuesta abajo. Los soles citados no tienen registro exacto en el feed usado: las anclas cercanas no son los propios blancos. |
| Hawksbill | Sol 535, RMC `26_1652`; se usa la posición publicada | La [figura 5 de Stack et al.](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023JE008187) identifica una travesía de los soles 535–538 en Hawksbill Gap. No localiza por sí sola cada muestra o contacto superficial. |
| Bunsen Peak | Sol 1084, RMC `51_0`; sol 1092, RMC `51_30`; centro como punto medio | El [catálogo NASA](https://science.nasa.gov/mission/mars-2020-perseverance/mars-rock-samples/) registra Comet Geyser/Bunsen Peak y sellado en sol 1088. Las dos localizaciones próximas, separadas unos 2,32 m, no prueban inmovilidad durante los soles intermedios ni la posición exacta del núcleo. |

Solo se seleccionaron registros `final="y"`; no se usaron posiciones
interpoladas o de mitad de recorrido como ancla final. No se interpola una
trayectoria durante intervalos sin datos. Se conservan las coordenadas como
publicadas. El GeoJSON no aporta por sí solo toda la definición de CRS y
convención de latitud: Daniel debe conciliarlas con el producto marciano antes
de transformar a ENU. No se interpreta GeoJSON como WGS84 terrestre.

Las envolventes numéricas usan provisionalmente la esfera de la configuración
actual, radio 3.396.190 m: para un lado L, semiancho angular norte
`(L/2)/R` y este `(L/2)/(R*cos(latitud))`, convertidos a grados.
Son cajas aproximadas de consulta; no una huella ya validada sobre un raster.
No se reutiliza la elevación histórica de Perseverance como Z de una base.

## Contenido que se necesita de cada paquete

| Componente | Solicitud y criterio de aceptación |
|---|---|
| Identidad y huella | ID por sector/tamaño; centro solicitado y centro realmente extraído; polígono geográfico, extensión ENU, CRS completo, convención de latitud/longitud y datum vertical. Rechazar o explicar una cobertura insuficiente. |
| Topografía pública | Prior del CTX DTM nativo de 20 m donde tenga cobertura. Producto, versión, URL, términos, método de extracción/remuestreo y hashes del original disponible y del derivado, distinguiendo sus alcances. No afirmar un hash remoto que no se comprobó. |
| Imagen | Ortoimagen CTX de 6 m co-registrada; geometría y máscaras propias. Separar resolución de imagen, DTM y rejilla computacional. |
| Rejilla | Comparación controlada a 4 m: 128/256/512/1.024 m equivalen a 32/64/128/256 celdas por eje. Si el contexto no se transporta al planificador, documentar esa separación. |
| Conocimiento | Máscaras explícitas de NoData y observación; sigma justificada con sus unidades y significado. Los píxeles orbitales válidos siguen estimados, sin fabricar observaciones locales ni reducir incertidumbre por remuestrear. |
| Geología | Contexto SIM 3464 en Jezero y, donde exista, interpretación espectral CRISM o mapa publicado. Mantener escala, procedencia, registro e incertidumbre; una capa ausente se declara ausente. No convertir color, pendiente o interpolación en mineralogía. |
| Controles | Tres puntos no colineales, uno asimétrico, con fuente de comprobación y residuos. Distinguir control de georreferenciación de mera autoconsistencia de la transformación y de precisión de campo. |
| Aislamiento | Productos/roles públicos y referencia del evaluador separados. No introducir el HiRISE reservado como prior ni duplicar el mismo dato como entrada y verdad independiente. |
| Diagnóstico | Geometría/orientación/unidades, cobertura y porcentaje NoData, estadística de incertidumbre, hashes, versión y comando reproducible. NoData no se rellena como libre y la falta de cobertura no se oculta. |

**No desplazar silenciosamente el centro a una zona con datos.** Si una
opción del preparador ajusta coordenadas, registrar desplazamiento, motivo y
rasgo cubierto, y devolver la selección para revisión científica. Un recorte
numéricamente válido que pierde el afloramiento solicitado no satisface esta petición.

La existencia de estos productos en catálogos no asegura cobertura coincidente.
Para el primer lote basta producir el contexto y seleccionar después una o dos
ventanas anidadas: no es necesario generar todas las combinaciones de golpe.
Mantener el recorte actual de 128 m como control reproducible.

## Relevo posterior, sin cambiar módulos desde misión

Una vez entregados los mapas, misión comprobará identidad y selección científica.
Diego medirá planificación y reservas sobre los mismos tamaños; Jesús revisará
coherencia de batches, captura y volumen del replay; Jorge comprobará carga y
representación. El número de celdas crece 4×, 16× y 64× al pasar del control a
256, 512 y 1.024 m; esas proporciones no predicen por sí solas tiempos reales.

Si el afloramiento no queda identificado con suficiente confianza, devolver
`NOT_READY` y elegir otra exposición. No bajar tolerancias, fabricar suelo,
observaciones o tareas, ni mover A/B para conseguir una ruta. El tamaño
final del mapa operativo y los A/B nuevos se decidirán después de la entrega,
con los recursos y evidencias de ejecución pendientes de acuerdo.
