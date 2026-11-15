# Replay 3D del visor Web y revisión de la ventana de misión

**[Ver video 3D definitivo —82,2 s](capture-final/mission-web-3d-final.mp4).**
1600×900,30 fps,H.264 nivel4.0,sin audio. Se codificaron2466 fotogramas a
partir de3134 imágenes reales del compositor de Chrome con GPU Intel/D3D11.
La conversión sólo repite/descarta imágenes por sus tiempos; no sintetiza
movimiento. El error de duración respecto al registro es0,0101 s, menor que
un fotograma. Vista previa clara: `capture-final/mission-web-3d-final.hero-moving.png`.

Este corte conserva el experimento analítico original
`local-cost-eva-bunsen-20261115-02` y lo adapta al formato de replay que ya
consume el visor. La captura usa el **visor publicado real** de main
`9013bebf2400d605f5a3d68e79dadbd5d1c57d03`, compilado sin modificar sus fuentes.
La cámara de astronauta en tercera persona, el terreno, el modelo animado,
los controles y la telemetría son los del visor. No es otro renderizador 3D.

La procedencia continúa siendo **SIMULATED**. El paquete objetivo usa los
valores existentes `mode=REPLAY`, `source_mode=SIMULATION` y el esquema
`mge-web-0.1-draft`. Es una adaptación de presentación, no un registro ROS
canónico, ejecución de MissionManager ni evidencia nueva de misión. El video
mantiene la marca `AI-generated | SIMULATED | NOT LIVE` en cada fotograma.

## Por qué el mapa de512 m era excesivo para este caso

Los512 m provenían de las ventanas del barrido de escala. Se reutilizó un
caso explicativo factible; sus puntos A/B no se diseñaron para abarcar todo el
parche. Por eso la trayectoria quedó junto a la esquina suroccidental. Ese
experimento no demostraba un beneficio científico u operativo del dominio
completo y el encuadre anterior desperdiciaba espacio.

| Medida | Resultado |
|---|---:|
| A, ENU x/y |(-226,-218) m|
| B, ENU x/y |(-238,-82) m|
| Separación horizontal A–B |136,53 m|
| Envolvente de recorridos ejecutados y candidatos |12×136 m|
| Envolvente incluyendo el círculo de observación |24×136 m|
| Área de esa envolvente respecto a512² |1,245 %|
| Ventana local comprobada |256×256 m,64×64 celdas de4 m|
| Ventana original |512×512 m,128×128 celdas de4 m|

El1,245 % es una envolvente geométrica: **no** mide cobertura observada ni
cuánto espacio exploró la búsqueda. La observación contiene29 muestras de
rejilla, no29 mediciones CTX independientes. La resolución nativa sigue en20 m.

Un recorte de128 m alineado con esta rejilla no contiene la separación de136 m
en norte entre A y B. Uno de160 m cabe geométricamente, pero no se ha probado
su planificación. El recorte256 m se comprobó realmente: filas0:64/columnas0:64,
origen(-256,-256), conservando las coordenadas absolutas y alturas. No se
recentra ni desplaza la misión para mejorar su apariencia.

## Comprobación del recorte

Se repitieron las solicitudes inicial y posterior a la observación con el
planificador publicado y la composición científica exacta, sobre512 y256 m.
Las cuatro respuestas fueron FEASIBLE bajo2 s/200.000 etiquetas. Cada pareja
produjo **las mismas geometrías de ida/regreso y los mismos costes de
tiempo/Wh/O2**, con3033 y1804 etiquetas respectivamente. Los29 índices de
observación se remapearon explícitamente, conservando sus centros ENU.

La ventana256 m reduce las celdas un75 %. Aquí es una ventana activa suficiente;
512 m queda como contexto regional o caso de escalabilidad. No se afirma
equivalencia general: cambiar fronteras puede eliminar alternativas en otras
misiones. Si se quiere demostrar valor de áreas mayores, hace falta una misión
que realmente demande destinos, alternativas o preguntas científicas más
extensas, con sus propios recursos y comprobaciones.

Los detalles reproducibles están en `map-analysis/README.md`, `footprint.json`
y `crop-comparison.json`. El paquete `replay-256` sólo presenta el mismo
experimento; la comparación de planificación es una comprobación separada.

## Qué hace la adaptación y la grabación

El exportador conserva el run_id, XYZ absoluto, recursos, rutas candidatas y
momento de la observación. Añade muestras de visualización de hasta1 s para
la interpolación que ya usa el visor; no son mediciones nuevas. Los cambios
de mapa/ruta no se adelantan. Los estados/eventos de presentación se identifican
como derivados y no inventan COMPLETE, DONE ni trabajo científico verificado.

La reproducción utiliza sólo los controles públicos de tiempo, velocidad y
cámara del visor, con10× durante el recorrido. Abrevia visualmente la espera
inicial de600 s conservando íntegro su consumo y hace una pausa explicativa
en la invalidación registrada. Esas acciones son edición de replay, no cambios
en el reloj o evidencias originales. El perfil temporal y los fotogramas se
registran junto con estados del visor, fuentes, peticiones y validación ffprobe.

Se conservan los intentos de captura: prueba de cámaras, renderizado por software
con baja frecuencia de fotogramas y prueba de GPU nativa. Ninguno modifica los
datos científicos. Los perfiles nuevos de Chrome (`.browser-profile`) son
estado local de herramientas y **no forman parte de los artefactos publicables**.
No se arrancaron ROS, Gazebo, gateway ni planificador durante la grabación.

La primera codificación de la captura continua no superó el control de tiempo:
la cuantización por imagen y el relleno de fin del filtro/codificador añadían
fotogramas. Se conservaron esos archivos y se finalizaron las mismas imágenes
con tiempos absolutos en microsegundos y un límite explícito en el instante
registrado de final de captura. No se amplió la tolerancia ni se repitió la
misión. `finalize_video.mjs` reproduce esa finalización y
`capture-final/video-finalization-final.json` vincula comandos, tiempos y hashes.
El script principal incorpora después el mismo límite para futuras capturas;
el original ejecutado se conserva en cada intento. No se efectuó otra captura
completa después de esa corrección del codificador.

## Validación y límites

Python del checkout:1116 pruebas pasadas /21 omitidas por entorno /una
advertencia existente. Visor publicado aislado:311 pasadas /una omitida;
build correcto. El primer intento de sus pruebas carecía de las muestras
publicadas de `data/sample`; se restauraron desde el mismo SHA y se conservó
el fallo previo. El exportador tiene8 pruebas específicas, incluyendo
coordenadas, cronología, observación, NoData, recorte y rechazo de sobrescritura.
La prueba real en navegador confirmó WebGL 3D y la lectura del paquete.

La aceptación de simulación, producción, perfiles, registro geológico exacto,
trabajo/recorrido y misión ROS siguen con sus límites anteriores. Cambiar a
3D no convierte el experimento en una ejecución verificada. Los criterios de
`docs/mission_simulated_verification.md` se mantienen.

## Atribuciones y procedencia

Terreno: mosaico DTM CTX Mars2020 TRN, USGS Astrogeology/NASA;
[producto USGS](https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_ctx_dtm_mosaic).
El recorte y su hash original se vinculan en `replay-256/adapter-receipt.json`.
La asociación con un afloramiento concreto sigue sin registro independiente.

Modelo humano: “Animated Astronaut Character in Space Suit Loop”,
[LasquetiSpice](https://skfb.ly/o9nHu),
[CC BY4.0](https://creativecommons.org/licenses/by/4.0/). Conversión de materiales,
escala y animación según THIRD_PARTY_NOTICES.md y el visor publicado. Las fuentes
del visor mantienen sus licencias; no se redistribuyen fuentes del sistema.
Los elementos de base son escenografía del visor, no agentes adicionales
ejecutados. No se usan marcas gráficas de NASA en la captura.

Código y material de presentación asistidos con OpenAI Codex, declarados en
los dos registros obligatorios de IA. Todo permanece local: sin commits,
pushes, merges ni publicación autorizada. El organizador y su aval explícito
siguen siendo un requisito de entrega; este corte no anuncia preparación
final para enviar el proyecto.
