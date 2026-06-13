# Layout SLP + Optimizacion

Proyecto en Python con interfaz Streamlit para:

## Requisitos

- Python 3.10 o superior

## Instalacion

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecutar

```powershell
$env:PYTHONPATH='src'
python -m streamlit run src/app.py --server.port 8502
```

## Tests

Con el entorno `.venv` activado:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
```

## Datos

## Estructura
