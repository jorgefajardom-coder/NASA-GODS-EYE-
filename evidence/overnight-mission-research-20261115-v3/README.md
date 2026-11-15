# Auditoría nocturna local: resultados y límites

**Se recomienda 512 m como primera ventana de planificación científica, con
contexto anidado de 1.024 m y estaciones de 128/256 m.** Los tres sectores
conservan preguntas científicas complementarias. El reconocimiento necesita
una selección condicionada al corredor y al margen: las dos heurísticas aéreas
ensayadas no demostraron una mejora general de acceso a B al pagar sus costes.

Este paquete contiene investigación **SIMULATED del planificador**, no misiones
ejecutadas ni nuevos descubrimientos. Los perfiles, las asignaciones CAM, el
acuerdo de costes y la ejecución siguen pendientes de aprobación/aceptación.
La propuesta no amplía el escenario oficial ni el cierre de entrega.

## Identidad y alcance

Inicio: **2026-11-15 04:25:01 UTC**, 14-Nov 23:25:01 America/Bogota.
Captura de nuevos casos cerrada a **11:46:18 UTC**, antes del corte de 11:55:01.
Barrido, pruebas y reproducción cerrados a **11:47:32 UTC**. El sellado final
registra su hora y duración en [FINAL_MANIFEST.json](FINAL_MANIFEST.json);
el límite original es **12:25:01 UTC**, 15-Nov 07:25:01 local.

- Fuente publicada consumida: `7ad605039a524d5b5cbe2c983f2da9113f8b1ce9` (PR33).
- Checkout conservado: `feat/mission`, `5220bdd8314f6568a5211c5821adfe4bafb68b48`.
- Registro de contrato publicado `1.0.0-rc.2`, sin congelación; ICD-ROS2-V1,
  interfaces/gateway/replay `1.0.0`, modelo propuesto `mge-science-1.0.0`.
- [Protocolo](protocol.json), [entradas congeladas](input-lock.json),
  [código de ejecución](research-code-lock.json), [fuentes](source-lock.json),
  [instantánea exacta](execution-snapshot.json) y [versiones reales](validation/checks.json).
- Trabajo local: sin commits, pushes, merges, renderizado, ROS/Gazebo, nuevos
  mocks ni modificaciones de implementaciones de otros propietarios.
  No se incorporaron entregas nuevas durante el barrido.

La semilla raíz es `20261115`. Misión, mundo y sensor tienen flujos separados.
Los coeficientes LHS se comparten entre tamaños; geometrías/mundos/huellas
incluyen tamaño en su derivación. Los rangos no se ajustaron tras ver resultados.
Las revisiones v1/v2 quedan [excluidas y conservadas](revision-provenance.json).

## Cobertura y muestras pendientes

| Régimen | Previsto | Bloques completos | Sin candidato inicial dirigido | Pendientes | Episodios |
|---|---:|---:|---:|---:|---:|
| Amplio, 512/1.024 m | 480 | 408 | — | 72 | 4.896 |
| Dirigido, 128/256 m | 480 | 75 | 405 | 0 | 900 |
| Dirigido, 512/1.024 m | 480 | 26 | 239 | 215 | 312 |
| Total | 1.440 | 509 | 644 | 287 | 6.108 |

Cada bloque completo tiene dos agentes, dos modos y tres políticas. Estos
**episodios dependientes no son mundos independientes**. El amplio incluye
3.456 episodios exploratorios y los **1.440 previstos de comprobación**
(índices 12–15). Sus arrays privados tienen 252 hashes distintos; las familias
sin perturbación pueden reutilizar exactamente el mismo terreno.
No hubo bloques `ERROR` definitivos. Se conservan límites y familias no realizadas.

El [catálogo completo](case-catalogue-114730.csv) enumera cada clave, incluidas
las pendientes. La [síntesis](summary-114730.json),
[episodios CSV](episodes-114729.csv), [inventario](inventory-114730.json) y
[árbol hipótesis → escenario → observación → decisión → conclusión](decision-tree-114730.jsonl)
remiten a secuencia y hash del diario. Los tres bloques de preflight, 36
episodios, están separados; la verificación contabiliza 512 bloques/6.144
episodios **incluyéndolos**, mientras las tablas de resultados los excluyen.

El [núcleo balanceado](final-analysis.json) conserva índices
`0..8,12..15` en todos los 30 estratos: **390 bloques/4.680 episodios**.
No se seleccionó por factibilidad. Faltan completar parte del índice 9 y los
índices 10/11 en el amplio; el catálogo conserva la distribución exacta.

## Mapas públicos y representatividad

Se obtuvieron las 15 ventanas regionales de 128/256/512/1.024/2.048 m y se
conservó el control original. Las 15 tienen **100% de píxeles públicos válidos,
0 NoData y 0 observados inicialmente**, con sigma de prior de 2,5 m. Los
recortes anidados coinciden exactamente en sus zonas compartidas.
Se verificaron hashes, dimensiones, orientación norte, transformación local,
NoData y separación del evaluador. Se consumió únicamente `crop_source("CTX")`;
no se ejecutó la preparación completa de Daniel ni se usó HiRISE evaluador
como entrada del planificador o de los mundos.

| Lado físico | Rejilla de 4 m | Muestras nativas aproximadas por lado | Memoria pico del proceso nuevo, MiB |
|---:|---:|---:|---:|
| 128 m | 32×32 | 6,4 | 91,42–91,96 |
| 256 m | 64×64 | 12,8 | 91,58–93,00 |
| 512 m | 128×128 | 25,6 | 93,36–100,66 |
| 1.024 m | 256×256 | 51,2 | 99,75–111,30 |
| 2.048 m | 512×512 | 102,4 | 127,99–140,89 |

Memoria: seis procesos nuevos por tamaño, una consulta FAST por proceso,
incluyendo importaciones; [medidas completas](isolated-memory.jsonl).
**128×128 celdas equivale a 512 m**, mientras el control de 128 m tiene 32×32.
La rejilla de 4 m interpola un DTM CTX nativo de **20 m**; no añade detalle
observacional de rocas ni convierte el residual sintético en una reconstrucción.

La cobertura de píxeles **no confirma el registro exacto del afloramiento**.
Son ventanas sobre anclas históricas de consulta fijas, no nuevos A/B aprobados.
Faltan ortoimagen co-registrada, controles independientes y confirmación de la
convención de latitud. Se conserva el datum del producto MOLA/DeltaGeoid sobre
esfera marciana de 3.396.190 m. Los hashes corresponden a ventanas/derivados;
el SHA del TIFF completo sigue desconocido y no se sustituye por su ETag.
Fuente: [producto CTX de USGS](https://www.usgs.gov/data/mars-2020-terrain-relative-navigation-ctx-dtm-mosaic).

Las tres regiones tuvieron datos; **ninguna quedó sin cobertura de píxeles en
este corte**. Los otros 14 sectores del [catálogo previo](../../docs/science_patch_survey.md)
quedan diferidos, sin importación ni prueba de ausencia de cobertura orbital.

## Escala computacional y acceso encontrado

Hubo **768 consultas** de escala: 256 configuraciones × tres repeticiones,
incluyendo plano 2D, prior 2.5D, FAST/SAFE y sigma1/sigma3. Se mantuvieron
200.000 etiquetas y dos segundos por consulta.
En el prior de Bunsen, la consulta regional corta FAST fue FEASIBLE en todos
los tamaños: mediana humano/rover de **0,136/0,066 s en 512 m**,
**0,172/0,131 s en 1.024 m**, y **0,474/0,342 s en 2.048 m**.
Bright humano y Hawksbill ambos agentes devolvieron NO_PATH para esos A/B;
Bright rover alcanzó SEARCH_LIMIT en 512/1.024/2.048 m.

Estos A/B regionales están separados 45,25 m y mantienen ubicación física
entre tamaños; el control original conserva 62,23 m. No son rutas kilométricas.
Las misiones aleatorias sí respetan L/8–L/2 sin filtrar por ruta, de modo que
también aumenta su separación con el mapa. Ese cambio de misión impide
atribuir todo `UNKNOWN` al número de celdas.

Ejemplo descriptivo balanceado, **FAST, sin reconocimiento previo**, 65
episodios por fila. «B» requiere candidato que pase la auditoría de movimiento,
servicio y retorno con las reservas actuales; no autoriza ejecutarlo.

| Ventana | Humano: B / agenda completa / UNKNOWN | Rover: B / agenda completa / UNKNOWN |
|---|---:|---:|
| Bright 512 m | 14 / 1 / 0 | 15 / 15 / 6 |
| Bright 1.024 m | 2 / 0 / 5 | 2 / 2 / 14 |
| Hawksbill 512 m | 14 / 1 / 1 | 12 / 12 / 0 |
| Hawksbill 1.024 m | 10 / 1 / 16 | 10 / 7 / 19 |
| Bunsen 512 m | 10 / 0 / 9 | 3 / 3 / 1 |
| Bunsen 1.024 m | 2 / 0 / 36 | 2 / 1 / 41 |

Los presupuestos y agendas difieren entre sectores. Esta tabla caracteriza
los candidatos encontrados bajo esos supuestos; UNKNOWN no demuestra
inaccesibilidad física y el buscador aún usa costes proyectados incompatibles.
Véanse [todas las combinaciones](balanced-access.csv), las
[latencias/estados](report-metrics.json) y el
[diagnóstico geométrico](endpoint-geometry-diagnostic.json).
El filtro de escalón de 0,2 m entre centros de 4 m puede excluir aristas que
pasan el límite de pendiente (unos 2,86° axiales/2,03° diagonales).
Se cuantificó ese efecto; no prueba la causa única de un NO_PATH ni mide rocas.
Diego y Daniel deben revisar su significado antes de cambiar parámetros.

## Adaptación y valor del reconocimiento

| Régimen | Cambios contextuales exploración / comprobación | Cambios por demora exploración / comprobación |
|---|---:|---:|
| Amplio | 27 / 12 | 6 / 0 |
| Dirigido 128/256 m | 71 / 74 | 6 / 12 |
| Dirigido 512/1.024 m | 26 / 24 | 0 / 0 |

Son comparaciones desde **igual pose, recursos y parámetros**, con/ sin
información contextual. Se compara acción y geometría, no ID de ruta.
Las comparaciones con búsquedas incompletas quedan censuradas. Los cambios
de información combinan alturas, obstáculo y reducción de sigma; no aíslan
por sí solos un único mecanismo. Los casos dirigidos están condicionados al
corredor inicial y no estiman una frecuencia de Marte.

Seis [casos explicativos completos](curated-cases.json) conservan XYZ,
observaciones tipadas, versiones, recursos, reservas y candidatos:

| Caso y agente | Estado comparado → respuesta | Observación y recursos restantes |
|---|---|---|
| `bright-512-relief-3`, rover FAST | KEEP → DETOUR con contexto | 29 celdas; 33.866,77 s y 1.157,11 Wh; margen de retorno/servicio/reserva positivo |
| `bunsen-128-detour-0`, rover FAST | KEEP → DETOUR con contexto | 13 celdas; 15.389,31 s y 563,28 Wh |
| `bunsen-128-blocked-13`, rover FAST, comprobación | KEEP → RETURN con contexto | 29 celdas; 16.551,98 s y 564,50 Wh; candidato de regreso auditado |
| `bright-256-resource-14`, humano FAST, comprobación | KEEP → DROP_OPTIONAL por demora | 13 celdas; 2.672,63 s, 307,83 Wh metabólicos, 62,87 L O2; información sola no causa el cambio |
| `bunsen-512-unchanged-12`, rover FAST, comprobación | KEEP → KEEP | 29 celdas; 23.116,18 s y 796,08 Wh; observar no cambió la decisión |
| `hawksbill-1024-resource-12`, rover SAFE/corredor, comprobación | RETURN antes y después | Comparación censurada por SEARCH_LIMIT; no se cuenta como retorno causado por demora |

Además, el amplio produjo `bunsen-512-resource-5`: **KEEP → RETURN** al añadir
2.932,41 s de espera, dentro del margen conjunto congelado de 0,5–1,5 veces
la espera nominal. Permanecían 13.636,45 s y 511,99 Wh; el retorno seleccionado
costaba 2.753,84 s y 68,43 Wh. El mismo caso aparece en seis brazos dependientes,
no en seis mundos: [registro completo](broad-delay-cases.json).

La [reducción de umbrales](margin-thresholds.jsonl) evaluó nueve de doce grupos
posibles: dos cambios acotados, cinco sin transición y dos censurados; tres
grupos no tenían un punto elegible. En comprobación, el humano de
`bright-256-resource-14` cambia recomendación entre **0 y 10,079 s** de demora
adicional; el rover de `bright-512-resource-14`, entre **1.384,075 y 1.419,564 s**.
Son brackets de la recomendación en esos checkpoints, no umbrales únicos de
factibilidad global ni límites físicos. No se reponen consumos reales.

La comparación de políticas usa mundos iguales y paga el vuelo/observación.
En el núcleo balanceado FAST hay 390 pares por agente/política:

| Agente / política | Candidatos B | Agenda completa | Salidas realizadas / rechazadas por cap | Wh aéreos sumados entre episodios independientes |
|---|---:|---:|---:|---:|
| Humano / sin previo | 52 | 3 | 0 / 0 | 0 |
| Humano / corredor | 52 | 3 | 99 / 291 | 1.085,70 |
| Humano / alternativas | 52 | 3 | 91 / 299 | 1.005,64 |
| Rover / sin previo | 44 | 40 | 0 / 0 | 0 |
| Rover / corredor | 43 | 39 | 96 / 294 | 1.060,69 |
| Rover / alternativas | 44 | 40 | 92 / 298 | 1.024,91 |

**Frente empírico descriptivo:** con los objetivos limitados a candidatos B
encontrados, agenda completa y menor coste aéreo, «sin previo» domina las dos
heurísticas FAST en este conjunto. Es un análisis posterior con pesos de
muestreo fijos; no demuestra superioridad de seguridad o ciencia de esa política.
La frecuencia alta de vuelos rechazados y las huellas únicas pequeñas limitan
el contraste. Una huella del corredor no cubre todo el corredor; la alternativa
es un desplazamiento lateral público, no una política óptima de información.
Los costes sumados de la tabla no son autonomía de una campaña del dron.
Las políticas pueden alcanzar poses y consumos distintos; su comparación no
es el contrafactual causal contextual. [Todos los pares](policy-pairs.csv).

## Frente científico y mapas que conviene preparar

La recomendación científica es una cartera de opciones con preguntas distintas,
no un ranking numérico de probabilidades de descubrimiento:

| Opción | Pregunta sustentada y aporte al frente | Recomendación condicionada |
|---|---|---|
| Bright Angel–Neretva | Asociaciones de orgánicos/minerales, matriz y fracturas; [Murphy et al., 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13292988/) no determinan origen biológico | Priorizar el registro del workspace; 512 m activo y 1.024 m de contexto; caso contextual no censurado disponible |
| Hawksbill–Hogwallow | Facies y correlaciones laterales; [Stack et al., 2024](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023JE008187) y [estrategia NASA](https://science.nasa.gov/blog/sampling-strategy-for-the-delta-front-campaign/) sustentan observar antes de seleccionar muestras | Mantenerlo como frente complementario de selección de estaciones; 512 m y contexto 1.024 m; no atribuir su acceso solo al terreno |
| Bunsen Peak–Margin Unit | [Carbonato/sílice](https://www.nasa.gov/solar-system/rock-sampled-by-nasas-perseverance-embodies-why-rover-came-to-mars/) e [historia regional de alteración revisada en 2026](https://www.nasa.gov/solar-system/planets/mars/nasa-discovery-reveals-complex-water-systems-on-early-mars/) | Conservar 512 m y estación 128/256 m como frente de alteración y control nominal corto; la región no queda descrita por un único A/B |

El sistema numérico no implementa detección química/espectroscópica; el DEM
no identifica esos materiales. Las tres preguntas no tienen un valor cardinal
común acordado. El frente científico queda candidato, con límites de costes,
instrumentación y censura explícitos. 2.048 m permanece como extensión de
escalabilidad, sin propuesta de incorporarlo ahora a la entrega oficial.

Para Daniel: confirmar convención de coordenadas y asociación al afloramiento;
preparar ortoimagen co-registrada y controles independientes en las ventanas
fijas; entregar paquete público canónico con incertidumbre, NoData, datum y
hashes. El DTM de 20 m no determina un escalón físico de 0,2 m. Krokodillen,
Witch Hazel, Mawrth y Glen Torridon mantienen sus
[justificaciones y límites diferidos](supplemental-context.json).

## Costes, verificación y límites de aceptación

Una pasada posterior auditó **4.799 itinerarios FEASIBLE registrados**, con
605 combinaciones distintas perfil/camino/servicio: movimientos dirigidos y
actividades mediante las APIs científicas, incluidas las tres repeticiones de
escala. **94** coincidían numéricamente bajo las tolerancias fijas; eso no
establece acuerdo de producción. [Todos los costes](post-analysis/itinerary-audits.jsonl)
y [cobertura de la auditoría](post-analysis/itinerary-audit-summary.json).
Entre los 563 candidatos seleccionados auditados del amplio, **ninguno**
coincidía en todos sus costes con la proyección. No se ampliaron tolerancias.
La API publicada `ScientificCosts` pasa sus controles aislados; en el SHA fijado
todavía no alimenta el buscador ni vincula las actividades/esperas al contexto
ROS. La autorización queda bloqueada. Diego y Jesús conservan ese relevo.

La [verificación](verification-114728.json) releyó diarios e identidades,
reprodujo mundos y perfiles desde semillas, comprobó promedios por bloques
computacionales de 20 m dentro de 1 mm, causalidad, fases únicas, recursos
monótonos, costes dirigidos, reservas y oxígeno solo humano. El
[control humano original](approved-control-check.json) preserva A/B, 120 s
de servicio, 60 s de espera, recursos y reservas: sigma1 UNKNOWN y la copia
sigma3 con candidatos costeados, nunca autorizados.

| Comprobación nueva | Resultado |
|---|---|
| Python completo del checkout | 1.069 passed / 21 skipped / 1 warning |
| Costes/oráculo/guardia de recursos de fuente publicada fijada | 86 passed / 1 warning |
| Oráculo plano pequeño | 6 controles; FAST mínimo, SAFE cota y coste de camino, sin validar terreno real |
| Geometría pública / consumidor científico | 15 mapas / 3 casos del adaptador, conformes |
| Repositorio / whitespace | Correctos; repetición final registrada al sellar |
| Frontend | 201 passed / 1 skipped; build correcto |
| Ubuntu 24.04 / Jazzy / colcon / intercambio ROS | NOT_RUN, excluidos de este corte |

Las omisiones Python corresponden a entorno ROS y permisos de symlink de
Windows. Las advertencias son Starlette existente y caché pytest de la
instantánea sin permiso de escritura. [Comandos, tiempos, versiones y logs](validation/checks.json).
Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1, rasterio 1.5.2;
Node 24.18.0 y npm 12.0.1. Se descargaron **17 MiB** de raster, frente al cap
de 2 GiB; tamaños de archivos y hashes finales constan en el manifiesto.

Límites materiales: sensor ideal sin ruido/oclusiones y sigma asumida de 0,25 m;
geometría privada usada solo para detener el prefijo analítico antes de un
segmento inadmisible, sin probar frenado físico; comparación en nodos realmente
alcanzados con XYZ conservado; reloj de actividades separado de latencia CPU;
agenda virtual, sin servicios realmente terminados; episodios por agente
independientes; balance completo de campaña aérea NOT_ESTIMATED. Se mantienen
desconocidos, incertidumbre, NoData y ausencia de referencia evaluadora en las
entradas de planificación. Se documentan el
[orden léxico de la serie inicial](protocol-deviations.json) y la
[recuperación del auxiliar de reducción](closure-recovery.json), que falló antes
de su primera consulta al leer índices JSON como listas; su revisión conserva
método, rangos y fuentes. No se borró ningún intento.

## Reproducción y relevo

Desde este checkout y la instantánea local conservada:

```text
python scripts/run_mission_research.py verify --root evidence/overnight-mission-research-20261115-v3
python scripts/run_mission_research.py report --root evidence/overnight-mission-research-20261115-v3
python -m pytest
python scripts/check_repository.py
# Desde web:
npm test -- --maxWorkers=1 --minWorkers=1 --no-file-parallelism
npm run build
```

El reporte crea nuevas exportaciones y conserva las anteriores. El diario
cerrado no reanuda misiones fuera de plazo. Para otro barrido hace falta otra
identidad/inicio y revisión de alcance; no modificar este protocolo. Se
reproducen arrays, semillas y perfiles; latencia y agotamiento del límite de
dos segundos pueden variar con hardware/carga. El sellado retiene los resultados
observados y los SHA exactos; no promete latencias idénticas en otro equipo.

Relevo: revisar nuevo SHA/contrato publicado antes de integrar; conciliar costes
con Diego, semántica del escalón con Diego/Daniel, registro cartográfico con
Daniel y evidencias/servicio/stop-replan con Jesús. Se mantienen pendientes la
ejecución integrada de tres agentes, retorno verificado y replay/video del
mismo run. La notificación y el aval explícito del organizador siguen siendo
gate de entrega: Jesús coordina, David respalda, con al menos cuatro horas
de margen o el plazo solicitado. Este paquete no declara preparación para
entregar ni envía mensajes externos. Ambos registros obligatorios de IA están
actualizados; las fuentes públicas siguen atribuidas y separadas de los datos
SIMULATED y de las medidas de software.
