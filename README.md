# Proyecto de Reportes de Deudas (sin web)

Este proyecto genera y envía reportes usando datos de **SAP Business One (Service Layer)**.

- **Vendedores**: 1 **PDF por vendedor** (adjunto por email).
- **Clientes**: 1 **email por cliente** con el **estado de cuenta en el cuerpo** (sin PDF).

## Estructura del Proyecto

El proyecto está estructurado de la siguiente manera:

- **`config.py`**: Contiene la configuración de la aplicación, incluyendo la ruta de la base de datos, la configuración del servidor de correo y otras variables de entorno.
- **`models.py`**: Define las funciones para interactuar con la base de datos SQLite, incluyendo la obtención de datos de clientes, vendedores y facturas.
- **`utils.py`**: Incluye funciones de utilidad, como el formateo de números para la presentación en reportes.
- **`services.py`**: Implementa la lógica de negocio de la aplicación, como la generación de informes en PDF, el envío de correos electrónicos y la actualización de datos.
- **`scheduler.py`**: Configura y ejecuta las tareas programadas, como la actualización de datos y el envío de reportes.
- **`run_full.py`**: Flujo completo para **vendedores** (actualiza datos → genera PDFs → envía emails).
- **`run_headless.py`**: Solo **genera PDFs por vendedor** (no envía correos).
- **`run_clients.py`**: Flujo completo para **clientes** (actualiza datos → envía mails con estado de cuenta en el cuerpo).
- **`run_clients_test.py`**: Prueba controlada (toma 5 clientes y envía todo a un mail de test).
- **`run_all.py`**: Ejecuta **vendedores + clientes** en un solo comando.
- **`get_Data_SAP/Z_run_scripts.py`**: Script encargado de obtener datos de SAP y actualizarlos en la base de datos SQLite.

## Dependencias

Instalación recomendada (usando `requirements.txt`):

```bash
pip install -r requirements.txt
```

## Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto y define las siguientes variables:

```env
MAIL_USERNAME="tu_email@example.com"
MAIL_PASSWORD="tu_password"
MAIL_SERVER="smtp.example.com"
MAIL_PORT=587
MAIL_DELAY_SECONDS=2.5
```

Reemplaza estos valores con los de tu cuenta de correo.

`MAIL_DELAY_SECONDS` controla la pausa entre correos a clientes para evitar límites del servidor SMTP (errores 450).

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
3. Ejecuta el flujo que necesites.

### Windows / PowerShell (recomendado)

En este repo se recomienda usar el launcher de Python:

```powershell
py --version
```

#### Enviar reportes a vendedores (PDF adjunto)

```powershell
py run_full.py
```

#### Enviar reportes a clientes (sin PDF, estado de cuenta en el cuerpo)

```powershell
py run_clients.py
```

#### Enviar ambos (vendedores + clientes) en un solo comando

```powershell
py run_all.py
```

#### Solo generar PDFs por vendedor (sin enviar mails)

```powershell
py run_headless.py
```

#### Prueba a clientes (5 clientes a un mail fijo)

```powershell
py run_clients_test.py
```

## Funcionalidades

- **Actualizar datos**: ejecuta extracción de SAP y refresca SQLite.
- **Generar reportes PDF**: 1 PDF por vendedor con sus clientes.
- **Enviar emails a vendedores**: envía el PDF al vendedor (y CC a administración).
- **Enviar emails a clientes**: envía el estado de cuenta en el cuerpo del correo (sin PDF).

## Tareas Programadas

El proyecto incluye una tarea programada que se ejecuta los lunes y jueves a las 07:00:

- **Actualizar Datos**: Ejecuta los scripts de SAP para actualizar la base de datos.
- **Generar y Enviar Reportes**: Genera reportes individuales para cada vendedor y los envía por correo electrónico.

## Consideraciones

- Asegúrate de que el script `get_Data_SAP/Z_run_scripts.py` esté correctamente configurado y funcione para obtener los datos de SAP.
- Verifica la configuración de tu servidor de correo en el archivo `.env`.
- Es posible que necesites ajustar la zona horaria del scheduler, ya que los horarios en `scheduler.py` se encuentran en hora UTC.
- Los PDFs de vendedores se generan con **ReportLab/Platypus**.

