# Layout SLP + Optimizacion

Proyecto en Python con interfaz Streamlit para comparar un layout por heuristica SLP contra un modelo de optimizacion.

## Requisitos

- Python 3.10 o superior

## Instalacion

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecutar la app

```powershell
$env:PYTHONPATH='src'
python -m streamlit run src/app.py --server.port 8502
```

## Ejecutar tests

Con el entorno .venv activado:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
```

## Salidas generadas (no se suben a git)

### Comparacion SLP vs OPT con archivos en tests/output

```powershell
$env:PYTHONPATH='src'
python scripts/run_all_tests.py
```

Genera CSV/PNG en tests/output.

### Benchmark por lotes

```powershell
$env:PYTHONPATH='src'
python scripts/run_bench.py
```

Genera data/bench_results.csv.

## Politica de versionado

El archivo .gitignore fue configurado para excluir lo que no es indispensable:

- Entornos y caches de Python (.venv, __pycache__, .pytest_cache, coverage, etc.)
- Configuracion sensible local de Streamlit (.streamlit/secrets.toml)
- Resultados generados (reports/*.txt, reports/*.csv, reports/*.png, tests/output/*.csv, tests/output/*.png, data/bench_results.csv)
- Archivos temporales de trabajo (tmp_*.py, scripts/tmp_*.py, logs)
- Archivos de IDE/SO (por ejemplo .vscode, .idea, .DS_Store)

## Si ya tenias salidas generadas trackeadas

Si algun archivo generado ya estaba en git antes del .gitignore, quitale seguimiento con:

```powershell
git rm --cached data/bench_results.csv
git rm --cached reports/summary.txt
git rm --cached tests/output/*.csv
git rm --cached tests/output/*.png
```

Despues haz commit de la limpieza junto con .gitignore.
