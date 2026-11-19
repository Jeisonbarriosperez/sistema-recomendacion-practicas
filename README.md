# Sistema de recomendación de sitios de práctica – CECAR

Prototipo académico (Proyecto Final Parte II – e-Business y Tecnologías).
Le recomienda al coordinador de prácticas los sitios más adecuados para cada estudiante.

## Estructura
- `datos/` – datos sintéticos (estudiantes, organizaciones, historial de prácticas).
- `generar_datos.py` – crea los datos con semilla fija (siempre salen iguales).
- `recomendador.py` – motor: filtros, cobertura de habilidades, puntaje y explicación.
- `app.py` – interfaz web en Streamlit.

## Instalación (Windows, PowerShell)
```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución
```
streamlit run app.py              # interfaz web
python recomendador.py EST-011    # versión por consola
```
