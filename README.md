# 🐙 Octopus Photos Backend

Octopus Photos es una solución de almacenamiento y gestión de fotografías **self-hosted**, diseñada bajo principios de soberanía de datos, código abierto y rigor técnico. 

## ¿De dónde sale OctopusPhotos?
OctopusPhotos es un proyecto self-hosted para almacenar tus fotos. Ustedes dirán: ¿Pero como que otro más? Si aquí ya tienes una lista enorme: https://meichthys.github.io/foss_photo_libraries/ Y tienen razón. Pero como todo en esta vida, cuando buscas entre las opciones resulta que no tienen algo que quieres o, si lo tienen, no está a tu alcance. Eso fue lo que me pasó a mi.

Muchos de estos proyectos no cumplían parte de lo que quería en estética y en funciones (el mío tampoco en eso último, pero ya iremos solventando eso), así que decidí solucionar eso y el problema del mensaje insistente de Google de que Drive iba a dejar de funcionar porque luego de 20 años al fin estoy llenando mis 15Gb de almacenamiento.

Soluciones como Immich son bellísimas, y no pretendo suplantarlas, ojalá pudiera usarla, pero la verdad es que dispongo de muy pocos recursos (los requisitos mínimos son unos 2 núcleos de procesador, que es todo lo que tengo, y al menos 6Gb de ram, que definitivamente no tengo). Y solo pensé: ¿No podría encontrar una forma de obtener al menos unas pocas de estas funciones y solventar el problema real de mi almacenamiento sin tener que usar un servidor en postgres, un redis, un grafana (aún no sé qué hace) y un módulo de machine-learning? Decidí que quería crear un servicio que pudiera ejecutar en una canaimita y luego ir escalando sobre esa base sin estirar tanto el consumo de recursos.

Así que esto es un poco experimental.

## Stack

Mi stack es sencillo:

* Python
* Flutter

Y ya. Ahí termina la lista. El backend usa FastAPI y SQLAlchemy para almacenar los metadatos e información del usuario en una base de datos en SQLite3. Ya tengo más de un año y medio programando en python y me sentí lo suficientemente seguro para intentar esto. Pero en el frontend la verdad no soy muy bueno, y TS/JS no es definitivamente lo mío. Decidí hace un tiempo probar con Flutter y me ha gustado mucho más (aunque tiene lo suyo, me ha sacado canas verdes desde que empecé con esto). Es por ello que el frontend lo he construido en flutter y encontrarán su código aquí: https://github.com/gabrielbaute/octopus-photos-webfront. Mantengo todo bajo la política de código 100% abierto y licencia MIT.

Lo que he hecho ha sido compilar todo el front a webassembly y copiarlo en el directorio de static definido para la app.

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

## Roadmap
¿Qué sigue? Pues hay varias cosas que aún me faltan tanto en el back como en el front, así que he aquí una lista de funciones a desarrollar en ambos flancos:
- **App de android**: tenemos una base en el frontend web, al ser flutter podemos reutilizar muchos de sus bloques, pero hay mucha lógica de negocio adicional que agregar allí como sicncronización con el servidor, un sistema de respaldo, eliminar fotos del celular que ya hayan sido respaldadas, etc… digamos que todo eso está en 0
- **App de iOS**: no soy fan de Apple (me caen mal), pero en teoría es posible perfectamente compilar el código de Flutter a swift y a una app para iOS, aunque necesitaría una máquina con ese OS y no la tengo, pero si llega a ser una necesidad no veo por qué no cubrirla si es virtualmente posible.
- **Vault**:Incorporar la funcionalidad de vault/cifrado de fotos en el web/front.
- **Recuerdos**: Incorporar la funcionalidad de memories/recuerdos (“Un día como hoy”) en el front, el servicio ya está pero no se han creado los widgets
- **Tests**: Continuar expandiendo y montando los tests unitarios que ya están, pero no los he seguido actualizando ni incorporando los nuevos servicios.
- **Webhooks**: no he incorporado un servicio que escuche o que envíe webhooks pero es importante tenerlo para comunicación entre el server y las apps cliente. He pensado en usar NTFY y habilitar un servicio de ello.
- **Sección de Favoritos/”Me Gusta”**: No existe, aunque durante el desarrollo ya un par de personas me comentaron que les gusta esa funcionalidad en GooglePhotos y la usan con frecuencia. En teoría, implicaría unas cuantas modificaciones en la base de datos, lo que me lleva al siguiente punto:
- **Migración**: no tengo implementado un servicio de migración aún, por lo que cualquier upgrade que actualice la base de datos puede potencialmente causar pérdida de información. Este es un punto CRÍTICO a solventar.
- **Búsqueda**: aún no he pensado cómo habilitar que se hagan queries sobre el server, pero es una función que ayudaría, ya que hay la opción de agregar tags a las fotos, razón por la cual se puede realizar búsqueda a partir de términos en los tags.
- **Docker**: aún no he preparado ni testeado una Dockerfile ni un compose. Es un punto importante.
- **Instalador de Windows**: estoy pensando en una versión para windows, que no use docker (que la mayoría de la gente que conozco que usaría esto no sabe que es el WSL2 o no disponen de equipos con capacidad de soportar WSL2), así que he pensado en una forma de usar un instalador (pyinstaller) que cree una versión portable que ejecute el servidor en segundo plano.
- **Manejo de duplicados**: aún no estoy seguro de cómo manejar esto, pero es un punto que hay que trabajar, una forma de escanear para que el usuario detecte fotos duplicadas que haya subido por error y que decida qué hacer o como solventar el tema.
- **Detección de rostros**: aún no sé si hacer esto o no, en teoría con unos binarios optimizados podría ejecutarse en una PC de pocos recursos, ya que no es una tarea que se ejecute a cada momento, sino que podrían programarse escaneos periódicos y que se guarden los vectores en la BDD, o en un directorio alternativo que almacene los binarios generados (olvidaba que SQLite no maneja bien el tema de los binarios y tampoco queremos que crezca demasiado, ya veremos, hay que decisiones técnicas que tomar alli)

De momento no se me ocurre nada más a decir verdad… pero si alguien piensa en algo, no dude en comentarlo!


## 📝 Licencia

Este proyecto es Open Source. El conocimiento debe ser libre y de acceso abierto.