# Proyecto de Reportes de Deudas de Clientes

Este proyecto tiene como objetivo generar y enviar informes de deudas de clientes a sus respectivos vendedores, utilizando datos provenientes de una base de datos SQLite y ejecutando scripts que obtienen información de SAP.

## Estructura del Proyecto

El proyecto está estructurado de la siguiente manera:

- **`config.py`**: Contiene la configuración de la aplicación, incluyendo la ruta de la base de datos, la configuración del servidor de correo y otras variables de entorno.
- **`app.py`**: Es el punto de entrada principal de la aplicación Flask. Inicializa el scheduler, configura la aplicación y gestiona el inicio del servidor.
- **`models.py`**: Define las funciones para interactuar con la base de datos SQLite, incluyendo la obtención de datos de clientes, vendedores y facturas.
- **`utils.py`**: Incluye funciones de utilidad, como el formateo de números para la presentación en reportes.
- **`services.py`**: Implementa la lógica de negocio de la aplicación, como la generación de informes en PDF, el envío de correos electrónicos y la actualización de datos.
- **`routes.py`**: Define las rutas de la aplicación Flask y la configuración de los filtros Jinja.
- **`controllers.py`**: Contiene las funciones que manejan las solicitudes HTTP y la lógica de la aplicación.
- **`scheduler.py`**: Configura y ejecuta las tareas programadas, como la actualización de datos y el envío de reportes.
- **`get_Data_SAP/Z_run_scripts.py`**: Script encargado de obtener datos de SAP y actualizarlos en la base de datos SQLite.

## Dependencias

Asegúrate de tener instaladas las siguientes dependencias antes de ejecutar el proyecto:

```bash
pip install Flask
pip install python-dotenv
pip install SQLAlchemy
pip install xhtml2pdf
pip install apscheduler
```

## Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto y define las siguientes variables:

```env
MAIL_USERNAME="tu_email@example.com"
MAIL_PASSWORD="tu_password"
MAIL_SERVER="smtp.example.com"
MAIL_PORT=587
```

Reemplaza estos valores con los de tu cuenta de correo.

### Base de Datos

El proyecto utiliza una base de datos SQLite llamada `mi_base_datos.db`. Asegúrate de tener esta base de datos en la raíz del proyecto o que la ruta en `config.py` apunte correctamente a la ubicación del archivo.

La base de datos debe contener las siguientes tablas:

- `clientes_con_deuda`
- `vendedores`
- `facturas_abiertas`

### Script de SAP

El script `get_Data_SAP/Z_run_scripts.py` debe estar correctamente configurado para obtener los datos de SAP y actualizar las tablas de la base de datos SQLite.

## Ejecución

Para ejecutar el proyecto, sigue los siguientes pasos:

1. Asegúrate de tener todas las dependencias instaladas como se indica en la sección de dependencias.
2. Configura el archivo `.env` como se indica en la sección de configuración.
3. Ejecuta la aplicación:

```bash
python app.py
```

La aplicación se ejecutará en [http://0.0.0.0:5010/](http://0.0.0.0:5010/).

## Funcionalidades

- **Página Principal** (`/`): Muestra una lista de clientes con sus deudas.
- **Detalle de Cliente** (`/cliente/<card_code>`): Muestra el detalle de un cliente específico, incluyendo sus facturas.
- **Lista de Vendedores** (`/vendedores`): Muestra una lista de todos los vendedores.
- **Vendedores con Saldos** (`/vendedores_con_saldos`): Muestra una lista de vendedores con sus saldos totales y por categoría.
- **Dashboard** (`/dashboard`): Muestra un resumen de la deuda total, saldos por categoría y gráficos de deuda por vendedor.
- **Actualización de Datos** (`/update_data`): Permite actualizar los datos de la base de datos mediante los scripts de SAP.
- **Generación de Reportes** (`/generate_reports`): Genera reportes individuales para cada vendedor y los envía por correo electrónico, con copia a una lista de correos de administración.

## Tareas Programadas

El proyecto incluye una tarea programada que se ejecuta los lunes y jueves a las 17:18 (hora del servidor):

- **Actualizar Datos**: Ejecuta los scripts de SAP para actualizar la base de datos.
- **Generar y Enviar Reportes**: Genera reportes individuales para cada vendedor y los envía por correo electrónico.

## Consideraciones

- Asegúrate de que el script `get_Data_SAP/Z_run_scripts.py` esté correctamente configurado y funcione para obtener los datos de SAP.
- Verifica la configuración de tu servidor de correo en el archivo `.env`.
- Es posible que necesites ajustar la zona horaria del scheduler, ya que los horarios en `scheduler.py` se encuentran en hora UTC.
- El proyecto utiliza `xhtml2pdf` para la generación de PDF, que puede tener algunas limitaciones en el renderizado de HTML complejo.

