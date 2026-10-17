# Servicio Externo de Identidad y Evidencias — Python/Django

Microservicio satélite desarrollado en **Python 3.12 + Django 5.x** como proveedor externo para la API principal de torneos en Node.js.

## Responsabilidades

- **Validación de Identidad:** Verifica si un `gamer_tag` existe y está registrado para un juego determinado.
- **Almacenamiento de Evidencias:** Recibe, almacena y sirve capturas de pantalla de partidos.
- **Simulación de Fallas:** Expone comportamientos de timeout y error 500 para validar el principio "Fallar Cerrado" de la API principal.

## Requisitos

- Python 3.11 o 3.12
- pip
- Docker y Docker Compose (opcional)

## Arranque rápido con venv

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar variables de entorno
cp .env.example .env

# 4. Aplicar migraciones y levantar servidor
python manage.py migrate
python manage.py runserver 8000
```

## Arranque rápido con Docker

```bash
cp .env.example .env
docker compose up -d
```

El servicio quedará disponible en `http://localhost:8000`.

## Contrato de API

| Método | Endpoint                     | Descripción                       |
| ------ | ---------------------------- | --------------------------------- |
| GET    | `/api/health/`               | Chequeo de estado del servicio    |
| POST   | `/api/jugadores/validar/`    | Valida existencia de un gamer_tag |
| POST   | `/api/evidencias/upload/`    | Sube una captura de pantalla      |
| GET    | `/media/evidencias/<nombre>` | Sirve la imagen almacenada        |

## Integración con la API principal

Este servicio corre en el puerto **`8000`**, coincidiendo con la variable `DJANGO_SERVICE_URL=http://localhost:8000` de la API en Node.js.
