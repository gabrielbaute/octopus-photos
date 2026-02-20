# 🐙 Octopus Photos Backend

Octopus Photos es una solución de almacenamiento y gestión de fotografías **self-hosted**, diseñada bajo principios de soberanía de datos, código abierto y rigor técnico. 

Como ingeniero, este sistema ha sido construido priorizando la eficiencia en el manejo de binarios, la extracción automática de metadatos y una arquitectura modular basada en capas (Services, Controllers, Models).

## 🚀 Características Principales

* **Gestión de Almacenamiento Inteligente**: Control de cuotas por usuario y persistencia organizada en disco local.
* **Procesamiento Automático**: Generación de miniaturas (thumbnails) y extracción de metadatos EXIF (GPS, cámara, ISO, etc.).
* **Seguridad Robusta**: Autenticación JWT, hashing de contraseñas con Salt y validación de propiedad de recursos (IDOR protection).
* **Arquitectura API**: Construido con FastAPI y SQLAlchemy 2.0 (Typed).
* **Diseño para Self-Hosting**: Estructura de directorios automática en el Home del usuario (`~/.OctopusPhotos`).

## 🛠️ Stack Tecnológico

* **Lenguaje**: Python 3.10+ (Tipado estricto).
* **Framework API**: FastAPI.
* **ORM**: SQLAlchemy 2.0 (PostgreSQL/SQLite compatible).
* **Validación**: Pydantic V2.
* **Procesamiento de Imágenes**: Pillow (PIL).

## 📦 Instalación y Configuración

Este proyecto utiliza [uv](https://github.com/astral-sh/uv) para una gestión de dependencias ultra-rápida y reproducible.

### 1. Preparar el entorno
Si no tienes `uv` instalado:
```bash
curl -LsSf [https://astral-sh.uv.run/install.sh](https://astral-sh.uv.run/install.sh) | sh
```

### 2. Sincronizar dependencias

```bash
# Crea el venv y sincroniza según el uv.lock
uv sync
```

### 3. Configurar el entorno

Copia el archivo de ejemplo y edita las variables de seguridad:

```bash
cp .env.example .env
```

### 4. Ejecución

Puedes ejecutar el servidor directamente con:

```bash
uv run python main.py
```
Al iniciar, el sistema creará automáticamente la siguiente estructura en tu directorio personal:

* `~/.OctopusPhotos/data/storage` (Fotos originales y thumbnails)
* `~/.OctopusPhotos/instance` (Base de Datos SQLite)
* `~/.OctopusPhotos/data/logs` (Registros del sistema)

## 📐 Arquitectura de Datos

## 📝 Licencia

Este proyecto es Open Source. El conocimiento debe ser libre y de acceso abierto.