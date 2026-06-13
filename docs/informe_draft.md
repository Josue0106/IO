# Informe técnico: Diseño de layout con SLP y optimización matemática

Índice

1. Introducción al problema
2. Descripción del caso y de los datos
3. Diseño del algoritmo SLP
4. Formulación del modelo matemático
5. Implementación computacional
6. Resultados obtenidos
7. Comparación y discusión
8. Conclusiones
Anexos

---

**1. Introducción al problema**

Este informe documenta el desarrollo de una solución computacional para la planificación de la distribución física de un Centro de Servicios Universitarios. El trabajo integra dos enfoques complementarios:

- Un método heurístico inspirado en Systematic Layout Planning (SLP) que traduce relaciones cualitativas en reglas de colocación y genera propuestas de layout mediante heurísticas de colocación y reparación.
- Un modelo matemático de optimización (formulación MIP y alternativa CP‑SAT) que busca minimizar la distancia ponderada por flujo entre módulos, sujeto a restricciones geométricas y de no‑superposición.

Motivación

La planificación de distribución (facility layout) busca asignar áreas funcionales en un recinto de manera que se minimicen costos de desplazamiento y se respeten relaciones funcionales. En entornos universitarios, la eficiencia del flujo de usuarios y la coherencia operativa son prioritarias.

Objetivos del proyecto

- Implementar y validar un algoritmo SLP que tome en cuenta relaciones A/E/I/O/U/X.
- Desarrollar un modelo matemático que minimice la distancia ponderada por flujo y satisfaga restricciones espaciales básicas.
- Comparar ambos enfoques con métricas homogéneas (distancia ponderada, cumplimiento de relaciones, uso del área, tiempo de ejecución).

Alcance del informe

Se describe el caso de estudio (recinto 30×18 m, 8 módulos), la conversión de relaciones cualitativas a puntajes, el diseño heurístico SLP, la formulación MIP (PuLP/CBC) y el uso de OR‑Tools como comparador. Se incluyen instrucciones de reproducción y recomendaciones para mejoras.

---

**2. Descripción del caso y de los datos**

2.1 Caso de estudio

- Recinto: 30 m × 18 m = 540 m² (rectángulo fijo).  
- Módulos: 8 áreas funcionales (`A1`–`A8`) con áreas mínimas, ver Cuadro 1.  
- Suma mínima de áreas: 129 m²; holgura: 411 m².

Cuadro 1 — Áreas y área mínima (ejemplo)

| Código | Área / módulo             | Área mínima (m²) |
|--------|---------------------------|------------------:|
| A1     | Recepción                 | 18               |
| A2     | Caja                      | 12               |
| A3     | Información académica     | 20               |
| A4     | Bienestar estudiantil     | 16               |
| A5     | TI                       | 14               |
| A6     | Sala de espera            | 24               |
| A7     | Archivo                   | 10               |
| A8     | Coordinación              | 15               |

2.2 Relaciones cualitativas (SLP)

Se usa la escala clásica: A (absoluta), E (especialmente importante), I (importante), O (ordinaria), U (sin importancia), X (indeseable). El equipo definió una matriz base (ver Cuadro 2 en Anexos). En la implementación se transforman a puntajes (ej.: A=16, E=8, I=4, O=2, U=0, X=-10).

2.3 Flujos (para modelo matemático)

Se utiliza una lista de flujos diarios entre áreas (ej.: Recepción→Sala de espera 150, Recepción→Información 120, etc.). Estos valores son los ponderadores en la función objetivo: minimizar Σ f_ij · d_ij.

2.4 Formato de datos y reproducibilidad

- Casos en `data/` (JSON).  
- Scripts de prueba: `scripts/run_pulp_test.py`, `scripts/seed_then_pulp.py`.  
- Código fuente en `src/` (SLP y modelos). Para revisar los archivos: [src/slp/heuristic.py](src/slp/heuristic.py) y [src/optimization/pulp_model.py](src/optimization/pulp_model.py).

---

**3. Diseño del algoritmo SLP**

3.1 Principios y decisiones de diseño

SLP (Systematic Layout Planning) es un enfoque cualitativo que organiza áreas según relaciones funcionales. Nuestro diseño toma estas decisiones:

- Traducción de relaciones a puntajes numéricos (Cuadro 4).  
- Orden de colocación por prioridad: primero áreas con mayor suma de puntajes (más críticas).  
- Representación: grid discreto sobre metros enteros (coordenadas enteras) y dimensiones en metros enteros para simplificar conteo y visualización.  
- Estrategia de colocación: free‑rect / guillotine inspired packing con generación de candidatos adyacentes a áreas relacionadas.

3.2 Detalle de la heurística

Paso 1 — Matriz y puntajes
- Construir matriz simétrica de relaciones; validar consistencia; convertir a puntajes.  

Paso 2 — Selección de semilla
- Área semilla: área con mayor suma de puntajes (peso total de relaciones). Colocar semilla preferentemente en posición central o en un borde según heurística (se prueba ambas variantes y se queda la mejor por la heurística).

Paso 3 — Generación de candidatos
- Para cada área sucesiva, generar posiciones candidatas alrededor de áreas ya colocadas (adyacencias), más una lista de posiciones de prueba en huecos grandes.  
- Evaluar candidatos por función heurística: H = α·(suma_puntajes_relaciones satisfechas) − β·(penalización_solapamiento) − γ·(fragmentación_espacio) − δ·(violación_X)

Paso 4 — Reparaciones y backtracking
- Backtracking limitado: si no se coloca un área en N intentos, el algoritmo retrocede k pasos y reubica bloques menos prioritarios.  
- Relleno de huecos: tras la fase principal, intentar colocar áreas restantes en huecos con dimensiones suficientes.

3.3 Parámetros y justificación

- Puntajes: A=16, E=8, I=4, O=2, U=0, X=-10 (proporcionan una fuerte prioridad a A/E).  
- Coeficientes heurísticos (α, β, γ, δ): calibrados empíricamente usando los casos de ejemplo.  

3.4 Salidas del SLP

- Layout preliminar: coordenadas (x, y, w, h) para cada módulo.  
- `seed_sizes`: mapeo código→(w,h) si el SLP produce un tiling completo (sin unused_area).  

Archivo principal: [src/slp/heuristic.py](src/slp/heuristic.py).

---

**4. Formulación del modelo matemático**

4.1 Variables y conjuntos

- Conjuntos: áreas i ∈ A, pares (i,j) con flujo f_ij.  
- Variables continuas: `xc_i`, `yc_i` (centroides).  
- Variables de elección de dimensiones: para cada área i se considera un conjunto finito de candidatos (w_{i,k}, h_{i,k}) y variables binarias `choice_{i,k}`.
- Variables binarias de no‑superposición: `b_{i,j,L}, b_{i,j,R}, b_{i,j,A}, b_{i,j,B}`.
- Variables de linealización de distancia: `dx_{i,j}`, `dy_{i,j}` ≥ 0.
- Variable `unused_area` ≥ 0 para permitir relax temporal con penalización.

4.2 Función objetivo

min Z = Σ_{i,j} f_{ij}·(dx_{i,j} + dy_{i,j}) + λ·unused_area

Donde λ es una penalización para desalentar la falta de cobertura total.

4.3 Restricciones

1) Elección de dimensiones: Σ_k choice_{i,k} = 1, w_i = Σ_k choice_{i,k}·w_{i,k}, h_i similar.

2) Área total: Σ_i area_i + unused_area = Área_recinto.

3) Límites geométricos: xc_i − w_i/2 ≥ 0, xc_i + w_i/2 ≤ W, y análogos para y.

4) No‑superposición (big‑M): para cada par i≠j:

xc_i − xc_j + (w_i + w_j)/2 ≤ M·(1 − b_{i,j,L})
(... y otras 3 disyunciones ...)

Σ de las 4 binarias ≥ 1.

5) Linealización distancias: `dx_{i,j} ≥ xc_i − xc_j`, `dx_{i,j} ≥ xc_j − xc_i` (análogo para dy).

4.4 Notas de modelado y mejoras

- Big‑M: se toma M = W + H (mejora la relajación frente a elegir M grande innecesario).  
- Reducción de candidatos: `MAX_CANDIDATES` controla tamaño del MIP; estrategia recomendada: cap adaptativo proporcional al número de áreas.
- Relaciones cualitativas: pueden modelarse como penalizaciones en la función objetivo (costes altos por violar A) o como restricciones duras (exigir `dx+dy ≤ threshold` para pares A). Se describen dos caminos en la sección de recomendaciones.

---

**5. Implementación computacional**

5.1 Estructura del repositorio

- `src/app.py`: interfaz Streamlit y pipeline.  
- `src/slp/heuristic.py`: algoritmo SLP.  
- `src/optimization/pulp_model.py`: MIP con PuLP (CBC).  
- `src/optimization/ortools_model.py`: CP‑SAT alternativa.  
- `src/core/`: modelos de datos y métricas.  
- `scripts/`: scripts para tests y pipelines.

5.2 Dependencias y entorno

- Entorno virtual Python: crear y activar `.venv`.  
- Instalar: `pip install -r requirements.txt`.

Comandos de ejemplo

```powershell
$env:PYTHONPATH='src'; .venv\Scripts\python.exe scripts/run_pulp_test.py
$env:PYTHONPATH='src'; .venv\Scripts\python.exe scripts/seed_then_pulp.py data/example_case_small.json
``` 

5.3 Detalles de código relevantes

- SLP: búsqueda de candidatos y heurística de evaluación dentro de `src/slp/heuristic.py`.
- MIP: construcción de variables `choice_{i,k}`, binarias `b_{i,j,*}`, linealización `dx,dy` y objetivo en `src/optimization/pulp_model.py`.
- Integración SLP→MIP: `scripts/seed_then_pulp.py` obtiene `seed_sizes` y decide `seed_fix` si el SLP produce tiling completo.

5.4 Parámetros experimentales

- `time_limit_s` para el solver (puede pasarse por script).  
- `MAX_CANDIDATES` en `pulp_model.py` (ajustable): trade‑off entre calidad y tamaño del MIP.

---

**6. Resultados obtenidos**

6.1 Experimentos ejecutados

- Conjunto de casos: caso pequeño, caso grande, dos casos determinísticos de tiling completo.
- Para cada caso se ejecutó: SLP (registro de tiempo y status), PuLP (con y sin `seed_fix`), OR‑Tools (cuando procede).

6.2 Resultados representativos

- `sample_case.json` con el benchmark actual (`data/bench_results.csv`):
	- **Mejor (global):** 6320.0 — método `OPT` (`growth_percent=0.1`, `enforce_relations=True/False`).
	- **Mejor SLP:** 10140.0 — método `SLP` (`growth_percent=0.0`, `enforce_relations=True/False`).
	- **Ejemplo con relaciones forzadas:** `OPT` (`enforce_relations=True`) obtiene 7470.0, frente a `SLP` con 10140.0.
- En esta versión, `OPT` se resuelve mediante `INFEASIBLE_FALLBACK_PULP` en el caso de ejemplo, lo que explica que el tiempo quede alrededor de 5 a 10 s según la variante.
- SLP sigue siendo muy rápido (~0.001 s), pero la distancia total ponderada es mayor que la del modelo matemático.

6.3 Tablas y gráficos (a completar con ejecuciones)

- Tabla comparativa por caso (colocar aquí los resultados experimentales completos).  
- Gráficas de barras: tiempo (SLP vs PuLP vs OR‑Tools), distancia ponderada, % área utilizada.

6.4 Observaciones adicionales

- Introducir poda agresiva o `seed_bonus` puede introducir regresiones si no se calibra con la versión específica de PuLP/CBC (se observó `TypeError` al usar `fracGap` en la versión instalada).  
- Mejores prácticas: usar `seed_fix` cuando el SLP brinda tiling completo; limitar candidatos de forma adaptativa.

---

**7. Comparación y discusión**

7.1 Métricas de comparación

- Distancia total ponderada por flujo (objetivo primario).  
- Número de relaciones A/E satisfechas (cuenta absoluta).  
- Violaciones X (mínimo deseado).  
- % área utilizada (coverage).  
- Tiempo de ejecución (segundos).  
- Facilidad de interpretación (cualitativo).

7.2 Análisis

- El MIP optimiza objetivamente la distancia ponderada, pero su efectividad práctica depende de la parametrización (candidatos, límites, warm‑starts).  
- SLP ofrece propuestas interpretables y buenas en relaciones cualitativas; sin embargo, puede requerir ajustes para afinar la ocupación del espacio.

7.3 Recomendaciones prácticas para la entrega

- Presentar ejemplos donde SLP produce tiling completo y usar `seed_fix` para ilustrar la integración y la robustez del pipeline.  
- Incluir en la demo el proceso: cargar caso JSON → ejecutar SLP (mostrar matriz relacional) → ejecutar optimización (mostrar progreso y solución).  

---

**8. Conclusiones**

- La combinación de SLP y optimización brinda un enfoque práctico y pedagógico: SLP aporta estructura y cumplimiento de relaciones, el MIP ofrece ajuste fino respecto a flujos.  
- Controlar el tamaño del MIP (candidatos y fijación de tamaños) es esencial para tiempos aceptables.  
- Para la entrega se recomienda usar la versión actual del repositorio (MIP restaurado) y presentar casos representativos, junto con anexos de reproducibilidad.

---

**Anexos (sugeridos)**

A. Cuadros de datos: relaciones, flujos y áreas (incluir tablas completas).  
B. Fragmentos de código: `src/slp/heuristic.py`, `src/optimization/pulp_model.py`, `scripts/seed_then_pulp.py`.  
C. Instrucciones de ejecución reproducibles y entorno.  
D. Resultados experimentales detallados (tablas por caso) y capturas de layouts.

---

Fin del borrador.
