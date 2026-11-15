# Propuesta local: campaña robótica, EVA y vuelos por parche

14 de noviembre de 2026, America/Bogota. Estado: **propuesta para revisión,
no aprobada ni operativa**. Fuente local `c3ec4c1`; los recortes nuevos siguen
pendientes de Daniel. Se conservan el escenario JZ-P01..07, sus recibos, perfiles,
contratos y resultados anteriores. No se hacen commits, pushes o merges.

## Decisión propuesta

Separar tres programas: **reconocimiento previo y acompañamiento del rover**,
**EVA humana desde su salida de la base**, y **salidas individuales del dron**.
El reloj global continúa para todos. Comenzar la EVA no devuelve al rover la
energía o el tiempo consumidos antes, ni reinicia la batería del dron.

Dimensionar cada asignación desde desplazamiento dirigido, trabajo, espera y
retorno, en lugar de imponer 20 minutos a todos. La propuesta conserva el
20% como política de comparación con el control y estudia 10/20/30%; **no lo
presenta como una reserva prescrita por NASA ni garantía de cubrir incertidumbre**.
No aumenta velocidades o eficiencias para conseguir que una tarea quepa.

Los [supuestos](../evidence/agent-campaign-proposal-20261114/assumptions.proposed.json)
y el [cálculo completo](../evidence/agent-campaign-proposal-20261114/campaign_analysis.json)
son un estudio paramétrico. Las distancias/desniveles siguientes no son rutas
calculadas sobre mapas reales; son cargas de trabajo propuestas para evaluar
los [parches solicitados](science_patch_map_requests.md).

| Caso | Asignación EVA humana | Asignación de campaña rover | Dron: subtotal conocido de las salidas deseadas |
|---|---|---|---|
| **Bunsen** | **35 min; 225 Wh metabólicos; 45 L O2** | **6 h 30 min; 800 Wh eléctricos brutos** | 1 salida: **150 s; 12 Wh** |
| **Bright Angel** | **60 min; 400 Wh; 80 L O2** | **10 h; 1.200 Wh** | 2 salidas: **450 s; 38 Wh** |
| **Hawksbill/Hogwallow** | **85 min; 550 Wh; 115 L O2** | **14 h 30 min; 1.800 Wh** | 2 salidas: **390 s; 29 Wh** |

Todas incluyen un 20% separado como reserva del presupuesto correspondiente.
La tercera columna comprende trabajo antes de la EVA, espera durante ella y
regreso. La última comprende **solo fases de salida conocidas**, no la energía
del dron durante todas esas horas: su campaña completa sigue sin estimar.
El redondeo del subtotal conjunto no tiene por qué igualar la suma de los
límites individuales redondeados; ambos deben comprobarse con un ledger acumulado.

**Estas son asignaciones nominales de experimento, no capacidades físicas ni
presupuestos robustos ya validados.** Las nueve envolventes nominales cumplen
por la construcción de la asignación; las nueve combinaciones adversas
estudiadas se rechazan. Aprobar las cifras exigiría primero acotar incertidumbre
y demostrar el trabajo realmente previsto, sin hacer pasar los extremos a la fuerza.

## Criterios científicos y alcance de las referencias

| Referencia primaria | Aplicación a esta propuesta | Límite |
|---|---|---|
| [D-RATS: muestra documentada de unos 10 min](https://ntrs.nasa.gov/api/citations/20120011761/downloads/20120011761.pdf) | Un bloque completo por muestra, con documentación incluida | Análogo terrestre; 420 s de trabajo ligero + 180 s pesado es nuestra asignación pendiente, no una medición marciana |
| [Apollo 17: EVAs de varias horas](https://www.nasa.gov/missions/apollo/apollo-17-mission-details/) | Confirma que la escala histórica EVA no se reduce a una demostración de 20 min | No determina duración segura de un traje o una EVA en Marte; no se adopta automáticamente una salida de 7 h |
| [Perseverance: movilidad](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/) | Mantener velocidades del orden de centímetros por segundo y reconocer que cientos de metros requieren horas | La máxima velocidad sobre suelo plano no es productividad diaria garantizada |
| [Perseverance: suministro eléctrico](https://www.jpl.nasa.gov/news/press_kits/mars_2020/landing/mission/spacecraft/power/) | Análogo de arquitectura MMRTG y baterías, coherente con la masa de referencia usada | Los aproximadamente 110 W iniciales son generación; dos baterías de 43 Ah no permiten inferir Wh utilizables sin otras especificaciones |
| [Ingenuity: vuelo y energía](https://www.jpl.nasa.gov/news/press_kits/ingenuity/landing/mission/spacecraft/) | Calcular vuelos por fases y distinguir presupuesto por salida de campaña | Los 90 s iniciales eran un plan de pruebas, no límite universal |
| [Ingenuity: ventana de carga](https://science.nasa.gov/blog/when-should-ingenuity-fly/) | La siguiente salida depende de estado térmico y energía disponible | No se presupone recarga instantánea ni una cantidad solar fija |

El [registro de fuentes y límites](../evidence/agent-campaign-proposal-20261114/sources.json)
amplía estas referencias. Los consumos conservan el modelo científico propuesto
actual, sin nueva calibración: Wh metabólicos para humanos, eléctricos para
robots y O2 únicamente humano como litros equivalentes secos a 273,15 K y
101,325 kPa. No son capacidades de traje, depósito o batería ni una validación
de CO2, refrigeración, fugas o soporte vital completo.

## Trabajo por parche antes de fijar el presupuesto

| Parche | Pregunta y estaciones propuestas | EVA: recorrido total / ascenso acumulado | Rover: recorrido total / ascenso acumulado |
|---|---|---:|---:|
| **Bunsen Peak** | Una muestra documentada y comparación visual previa entre dos estaciones robóticas | 200 m / 5 m; un bloque de muestra | 500 m / 10 m; dos inspecciones |
| **Bright Angel** | Comparar workspaces y materiales contrastantes; dos muestras condicionadas a inspección | 400 m / 10 m; dos bloques | 800 m / 15 m; tres inspecciones |
| **Hawksbill/Hogwallow** | Contrastar una sección deltaica y varias facies; tres muestras condicionadas | 600 m / 20 m; tres bloques | 1.200 m / 25 m; cuatro inspecciones |

Los 400 m del caso Bright Angel son un sobre de diseño que permite estudiar
desvíos en torno a workspaces cercanos, no el ancho del valle convertido en
trayectoria. Hawksbill no exige atravesar toda la región. Las magnitudes son
hipótesis de ingeniería según diversidad y escala, no distancias medidas entre
los futuros A/B. Cuando Daniel entregue los mapas, sustituirlas por itinerarios
georreferenciados y rechazar el caso si pierde interés, cobertura o viabilidad.

Cada par de tramos analíticos sale, asciende y regresa por separado; el ascenso
se cuenta una vez y el descenso no regenera energía. Esto permite auditar
contabilidad, no demostrar admisibilidad geométrica. El retorno está incluido
en la carga y la reserva se mantiene aparte después de pagarlo.

## EVA humana

Se conserva un check-in visual de 120 s en B, costeado como trabajo ligero,
sin convertirlo en una inspección opcional completada. Después se evalúan
los bloques de muestreo previstos, únicamente con B completado, inspección
pública compatible y regreso factible. Esta propuesta no crea ni completa tareas.

Cada muestra documentada ocupa **600 s en total**: 420 s ligeros y 180 s pesados.
No añadir otros 600 s de documentación a la misma muestra. Las pausas y
comprobaciones de campo son asignaciones explícitas de 10/15/20 min por caso,
pendientes de contraste; no se justifican por retardos Tierra–Marte dentro del
enlace ideal P0. El reconocimiento robótico previo ocurre antes de abrir el
reloj EVA, evitando gastar consumibles de traje esperando su preparación.

El [informe D-RATS](https://ntrs.nasa.gov/api/citations/20120011761/downloads/20120011761.pdf)
también sitúa la mayoría de sus EVA en unos 30–60 min y advierte contra medir
valor científico solo por cantidad de muestras. Aquí 1/2/3 son bloques opcionales
máximos del diseño, no cuotas de éxito: observar bien y regresar conserva
prioridad. Los 85 min de Hawksbill se derivan de nuestra carga mayor, no de una
duración marciana observada.

La tabla numérica definitiva está en el cálculo reproducible. Se deriva así:

`asignación = redondear_hacia_arriba(coste_nominal / (1 - reserva))`

Para humanos se redondea a 5 min, 25 Wh metabólicos y 5 L equivalentes de O2.
El redondeo facilita revisión del experimento; no describe precisión fisiológica.
Las reservas absolutas son el 20% de cada asignación, no un consumo añadido
dos veces al trayecto. Este cálculo compara reservas 10/20/30%, retirar una
muestra y extremos adversos conjuntos de perfiles y carga de trabajo. No
constituye un barrido aislado de cada coeficiente.

La duración obtenida es una **asignación de experimento**, no duración máxima
del astronauta. Estancia en el hábitat, preparación/despresurización y recuperación
quedan fuera del ledger EVA y necesitan modelos propios si se estudia la misión
completa. No se declaran gratuitos ni cubiertos por el O2 calculado aquí.

Las reservas propuestas son, respectivamente, 7/12/17 min, 45/80/110 Wh
metabólicos y 9/16/23 L equivalentes. El escenario nominal utiliza unos
26,4/45,8/65,6 min de EVA: el resto de la asignación no se añade como espera
para rellenar la ventana. Si ocurre una demora, se registra su duración y
consumo reales y se reevalúan regreso y margen antes de aceptar más trabajo.

## Campaña del rover

Programa causal propuesto:

1. Sale y reconoce la sección; realiza 2/3/4 estaciones de inspección.
2. Se confirma evidencia y posibilidad de retorno antes de liberar la EVA.
3. Durante la EVA permanece disponible; su espera sigue consumiendo recursos.
4. Regresa y cierra su propio registro; comenzar o terminar la EVA no lo reinicia.

Las inspecciones duran 600 s por estación como **ventanas propuestas de trabajo
visual/geométrico**, no como tiempos NASA de espectroscopia o perforación.
Se calculan 600 s nominales y 900 s dentro del adverso conjunto; el barrido
aislado de las alternativas 300/600/900 s queda pendiente. Se añaden 1.800 s de
coordinación previa y la espera durante la EVA nominal. El cálculo modifica esa espera si
el escenario adverso alarga la EVA. La actividad `inspect` conserva su potencia
actual; no implica que exista el sensor o ejecutor acordado para cada producto.

La asignación de campaña cubre horas, calculadas desde el programa completo,
y se redondea a 30 min y 100 Wh brutos. **Gasto eléctrico permitido, capacidad
almacenada y generación son tres cantidades distintas.** Los Wh propuestos
no acreditan que una batería física los pueda suministrar o almacenar.

Las reservas de tiempo del rover son 1 h 18 min / 2 h / 2 h 54 min y las
eléctricas 160/240/360 Wh. El programa nominal dura aproximadamente
5,13/7,94/11,53 h: no se llena todo el horizonte con trabajo y luego se exige
otra reserva temporal. Estos datos son requerimientos brutos que deberán
confrontarse con suministro y estado de carga, sin confundirlos con capacidad.

Se elige como referencia un rover inspirado en Perseverance/MMRTG, sin agregar
paneles solares ficticios. La generación de referencia no se resta del coste
ni se ingresa en la batería: el crédito de recarga es cero hasta disponer de
SOC, límites de potencia/carga, temperatura, pérdidas y un consumidor acordado.
Un rover solar requeriría otra propuesta con insolación, orientación, polvo y
temperatura; el viento que limpia paneles no se trata como recarga garantizada.

El sol medio de 88.775,244 s es una referencia de calendario. No se obliga a
rellenarlo con conducción o espera ni se confunde con el horizonte autorizado.
Si el trabajo acaba antes, el consumo posterior pertenece a otro episodio.
Si se alarga a uno o dos soles, toda pausa/noche añadida debe incluirse: el
modelo de espera despierto a 80 W no está calibrado como sueño o supervivencia
nocturna. El cálculo muestra su extrapolación solo como diagnóstico; la campaña
multisol permanece sin balance físico demostrado.

## Dron: presupuesto por salida y campaña pendiente

Cada salida incluye transición de despegue, ascenso, ida, observación, regreso,
descenso, transición de aterrizaje y espera terrestre. Se proponen 10 m de altura
relativa, 30 s de observación, transiciones de 5 s cada una costeadas como hover
y 10 s de espera terrestre. Son sustitutos de cálculo, no un modelo aerodinámico
ni una altitud con despeje validado. No se confunde Z del terreno con vuelo.

| Parche | Salidas deseadas | Desplazamiento de ida por salida | Condición importante |
|---|---:|---:|---|
| Bunsen | 1 | 50 m | Reconocimiento local, sin inferir área cubierta del tiempo de observación |
| Bright Angel | 2 | 110 m | Salida larga pendiente de validación; no asumir que dos vuelos cortos cubren el mismo recorrido sin trasladar físicamente el punto de lanzamiento |
| Hawksbill | 2 | 75 m | Sectores locales; no se promete cobertura de todo el contexto de 1 km |

En Bright Angel el modelo da **170 s en vuelo**, antes de los 10 s terrestres.
El [vuelo 12 de Ingenuity](https://science.nasa.gov/wp-content/uploads/2024/06/ingenuity-helicopter-flight-log.pdf)
duró 169,5 s: es una comparación histórica que obliga a revisar el sobre de vuelo,
no una certificación ni un límite físico universal.

Por salida, la asignación propuesta es 150 s/12 Wh en Bunsen, 240 s/19 Wh en
Bright Angel y 210 s/15 Wh en Hawksbill. Los tiempos en vuelo nominales son
110/170/135 s; el tiempo terrestre se cuenta aparte una sola vez. Dos salidas
deseadas no significan dos salidas disponibles: la segunda queda condicionada
a recursos restantes, geometría y estado térmico acreditados.

La [referencia de baterías de Ingenuity](https://www.nasa.gov/wp-content/uploads/2024/01/battery-system-design-testing-and-operation-for-the-mars-perseverance-rover-and-ingenuity-helicopter.pdf)
incluye energías de inicio de vida de 44,4 Wh a 25 C y 38,8 Wh a 0 C. No son
energía útil garantizada para nuestras salidas. Sumarlas no crea capacidad,
y un presupuesto por vuelo no se renueva después de aterrizar.

El cálculo acumula fases conocidas para todas las salidas deseadas y muestra
el coste adicional si el dron permaneciera despierto a 5 W durante la campaña.
**La energía de campaña completa queda NOT_ESTIMATED** mientras falten sueño,
calefacción, pausas reales y recarga acreditada. Una segunda salida no puede
autorizarse por reiniciar contadores; necesita recursos restantes observados.
No se supone transporte gratuito del dron, cambio de base o un SOC inicial nuevo.

## Sensibilidad, rechazos y criterios para adoptar la propuesta

Los presupuestos propuestos se derivan del caso nominal, no se inflan hasta
hacer pasar cualquier extremo. Se retienen casos adversos conjuntos con los
límites ya declarados del registro y una perturbación estructural explícita:
25% más distancia, 50% más ascenso y servicios 50% más largos. Son pruebas de
diseño, no intervalos de confianza ni probabilidades NASA.

| Caso adverso conjunto | Humano: min / Wh metabólicos / L O2 consumidos | Rover: h / Wh eléctricos consumidos | Dron: s / Wh en fases conocidas acumuladas |
|---|---|---|---|
| Bunsen | 36,2 / 287,5 / 73,4 | 14,02 / 2.540,9 | 185,6 / 17,52 |
| Bright Angel | 64,4 / 517,8 / 132,2 | 22,18 / 4.034,6 | 558,8 / 56,92 |
| Hawksbill | 93,8 / 767,7 / 196,0 | 32,86 / 5.994,5 | 449,4 / 44,16 |

Son consumos del modelo antes de una nueva reserva, no asignaciones alternativas
aprobadas. El rover Hawksbill adverso incluso supera un sol; eso muestra la
limitación del diseño, sin acreditar operación nocturna ni un balance multisol.

Un caso que compromete retorno o reserva se rechaza; se puede reducir trabajo
opcional o replantear la sección. Quitar una muestra no ahorra desplazamiento
automáticamente: el cálculo mantiene el recorrido salvo que exista una nueva
ruta. No se ocultan los fallos ni se reducen tolerancias para obtener aceptación.

Antes de ejecutar hacen falta:

- Recortes y rutas reales, estado inicial, pendiente, cobertura y georreferenciación.
- Aprobación diferenciada de nuevos programas/recursos y coeficientes de perfiles.
- Acuerdo de costes con Diego, incluyendo trabajo, espera y retorno dirigido.
- Contrato con Jesús para liberar cada agente, mantener el reloj global y el
  ledger por episodio sin reiniciar recursos, publicar avances y cerrar evidencias.
- Balance físico de suministro/almacenamiento, potencia y estados térmicos de robots.
- Instrumentos, huellas del dron y capacidades reales de inspección/muestreo.

La prioridad científica de recortes conserva Bright Angel primero. Para probar
la nueva separación de relojes, el piloto de menor carga sería Bunsen; Bright
Angel y Hawksbill ampliarían trabajo únicamente después de validar el anterior.
En cada caso se fijarán A/B y estaciones sobre el recorte registrado y se
comprobará que ida, posibles desvíos y regreso caben en su cobertura pública.
Un contexto de 512/1.024 m no garantiza por sí solo esa cobertura operativa.
Las celdas válidas estimadas pueden sustentar candidatos según D-EST-01; NoData
y obstáculos se conservan, y una ruta propuesta no certifica terreno observado.

No se añaden campos ROS ni se inventan mensajes para esos contratos. Los criterios
de éxito existentes siguen vigentes; una campaña de tres agentes requiere además
cerrar sus evidencias. Proponer estas asignaciones no autoriza una ruta ni declara
implementado el programa previo del rover. El control de 20 min se conserva
para comparar y reproducir lo anterior, sin convertirlo en límite del sistema.

## Verificación local de esta propuesta

Reproducción independiente equivalente salvo hora/comando; entradas y hashes
comprobados, rechazo de sobrescritura y contabilidad acumulada verificados.
Regresiones: Python 979 pasaron / 19 omitidas por entorno; frontend 161 pasaron /
1 omitida por paquete opcional; comprobación de repositorio y build correctos.
Ubuntu/Jazzy, colcon e intercambio ROS no ejecutados en este corte analítico.
El [registro completo](../evidence/agent-campaign-proposal-20261114/validation/validation.json)
conserva comandos, versiones, hashes, omisiones y límites. Son verificaciones
de software y del cálculo, sin evidencias nuevas de ejecución de misión.

## Publication after reconciliation

The owner authorized integration after reconciliation. Published main9198b3d
(PR28) is incorporated unchanged. The earlier local-only status describes
the preparation cut; this publication preserves all proposed/approval states.
D-COST-02 accepts reuse of the scientific API as implementation direction;
profile approval, cost-context agreement and execution evidence remain open.
The rc.2 contract record is not a scientific approval or a semantic freeze.
Original analysis/report hashes and pinned c3ec4c1 reproduction remain historical.
