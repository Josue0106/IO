# Layout SLP + Optimizacion

Proyecto en Python con interfaz Streamlit para:
- Matriz relacional (SLP)
- Heuristica SLP
- Optimizacion con OR-Tools CP-SAT
- Comparacion de indicadores

## Requisitos
- Python 3.10+

## Instalacion

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
streamlit run src/app.py
```

## Datos
- Archivo de ejemplo: [data/sample_case.json](data/sample_case.json)

## Estructura
- `src/app.py`: UI
- `src/core`: datos, matrices y metricas
- `src/slp`: heuristica
- `src/optimization`: modelo matematico
- `src/visualization`: graficos
