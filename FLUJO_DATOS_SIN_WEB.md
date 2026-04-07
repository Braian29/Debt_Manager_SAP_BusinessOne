# Flujo de datos (SAP → reportes PDF → emails) **sin web**

Este documento describe el flujo de punta a punta que hoy existe en el repo y cómo queda **si eliminamos la web** (rutas/HTML de navegación), manteniendo la funcionalidad de **actualizar datos desde SAP** y **enviar reportes por correo a los vendedores**.

## Objetivo

- **Mantener**:
  - Extracción de datos desde SAP (Service Layer).
  - Persistencia/transformación local (JSON + SQLite).
  - Generación de reportes PDF por vendedor.
  - Envío por email (con CC a casillas internas).
  - Ejecución manual y/o programada (scheduler).
- **Eliminar**:
  - Sitio web (rutas Flask, páginas de dashboard/listados).

## Fuentes y datos extraídos desde SAP

La actualización corre en `get_Data_SAP/Z_run_scripts.py` y ejecuta:

### 1) Vendedores (endpoint `SalesPersons`)
Archivo: `get_Data_SAP/A_get_salesperson_info.py`

- **SAP Service Layer**: `SalesPersons`
- **Campos**: `SalesEmployeeCode`, `SalesEmployeeName`, `Telephone`, `Mobile`, `Email`
- **Salida**: `data/SalesPersons.json`

### 2) Clientes con deuda (endpoint `BusinessPartners`)
Archivo: `get_Data_SAP/A_get_client_info.py`

- **SAP Service Layer**: `BusinessPartners`
- **Campos**: `CardCode`, `CardName`, `PayTermsGrpCode`, `PriceListNum`, `SalesPersonCode`, `Cellular`, `EmailAddress`, `CurrentAccountBalance`
- **Filtro**:
  - `CardType eq 'cCustomer'`
  - `CurrentAccountBalance gt 1000`
  - `U_Empleado eq 'N'`
- **Salida**: `data/clientes_con_deuda.json`

### 3) Facturas abiertas (QueryService, join Invoices + BusinessPartners)
Archivo: `get_Data_SAP/A_get_invoice.py`

- **SAP Service Layer**: `QueryService_PostQuery` usando `"$crossjoin(Invoices,BusinessPartners)"`
- **Campos (Invoices)**: `CardCode`, `CardName`, `DocTotal`, `PaidToDate`, `NumAtCard`, `DocDate`, `DocDueDate`
- **Filtro**:
  - Relación: `Invoices/CardCode eq BusinessPartners/CardCode`
  - `BusinessPartners/U_Empleado eq 'N'`
  - `Invoices/DocumentStatus eq 'O'` (abiertas)
  - `BusinessPartners/CurrentAccountBalance gt 10`
  - Paginación por `$top`/`$skip`
- **Salida**: `data/invoicesAbiertas.json`

## Persistencia local y transformaciones

Archivo: `get_Data_SAP/C_load_db.py`

### Base SQLite
Archivo: `mi_base_datos.db` (ruta configurada en `config.py` → `Config.DATABASE_PATH`)

Se crean/limpian y cargan 3 tablas:

- **`clientes_con_deuda`**
  - Mapea los campos del JSON de clientes (arriba).
- **`vendedores`**
  - Mapea los campos del JSON de vendedores (arriba).
- **`facturas_abiertas`**
  - Carga campos de facturas + campos calculados:
    - `SaldoPendiente = DocTotal - PaidToDate`
    - `DiasDesdeCreacion`
    - `Clasificacion` (En Fecha / Proxima a Vencer / Vencida) según días

### Estructura “de negocio” para reportes

Archivo: `models.py` (función `obtener_datos(db_path)`)

Devuelve:
- **`clientes_con_info`**: lista de clientes enriquecidos con
  - vendedor asignado (por `SalesPersonCode`)
  - facturas (por `CardCode`)
  - `saldos_por_categoria` (En Fecha / Proxima a Vencer / Vencida)
  - `porcentaje_vencido`
- **`vendedores`**: lista de vendedores (incluye `Email`)
- **`vendedores_con_saldos`**: agregados por vendedor (para dashboards, no obligatorio para email)

## Generación de reportes PDF

Archivo: `services.py`

### Plantilla
- `templates/report_template.html`
  - Es HTML con estilos embebidos; se renderiza con variables `vendedor_name` y `clientes`.
  - Incluye `<img src="static/logo.png" ...>` (si el logo falta o la ruta no es accesible en PDF, puede quedar en blanco).

### Render a PDF
Función: `generate_report_pdf(template_name, data, output_path)`
- Renderiza el HTML (hoy usa `render_template(...)` de Flask/Jinja).
- Convierte a PDF con `xhtml2pdf` (`pisa.CreatePDF(...)`).
- Guarda en `reports/{SalesEmployeeCode}_report.pdf`.

## Envío de correos

Archivo: `services.py`

### SMTP
Función: `send_email(subject, body, to_email, pdf_path, cc=None)`

- Servidor: `Config.MAIL_SERVER`
- Puerto: `Config.MAIL_PORT`
- Usuario/clave: `Config.MAIL_USERNAME` / `Config.MAIL_PASSWORD`
- Envío: `STARTTLS` + `login` + `send_message`

### Lógica por vendedor
Función: `generate_and_send_reports(vendedores, clientes_con_info, format_number)`

- Por cada vendedor:
  - Filtra `clientes_con_info` por `vendedor_code == SalesEmployeeCode`
  - Ordena por saldo vencido (desc)
  - Genera PDF
  - Envía email a:
    - `vendedor.Email` si existe
    - si no existe, fallback `"superclinsys@gmail.com"`
  - CC fijo a:
    - `romina.galdos@super-clin.com.ar`
    - `cuentas@super-clin.com.ar`
    - `braian.alonso@super-clin.com.ar`
    - `horacio.rodriguezbarcelone@super-clin.com.ar`

## Orquestación: ejecución programada (scheduler)

Archivo: `scheduler.py`

La tarea `scheduled_task()` hace:

1) `run_scripts()`  
   - Corre `get_Data_SAP/B_get_allinfo.py` (descarga JSONs)  
   - Corre `get_Data_SAP/C_load_db.py` (carga/calcula SQLite)

2) `get_data()` → `models.obtener_datos(Config.DATABASE_PATH)`

3) `generate_and_send_reports(...)`

### Cron actual
- `CronTrigger(day_of_week='mon,thu', hour=7)`
  - Lunes y jueves a las 07:00 (minuto por defecto 0).

### Dependencia “web” dentro del scheduler
Actualmente `scheduled_task()` ejecuta:

- `from routes import app`
- `with app.app_context(): ...`

Esto **no es para servir páginas**, sino para que `render_template(...)` funcione al generar el PDF (Jinja/Flask necesita contexto de aplicación para resolver templates).

## Qué se puede borrar si “no usamos la web”

Si el objetivo es **no tener UI web**, lo que hoy es puramente “web” es:

- `controllers.py` (rutas/handlers que renderizan páginas)
- `routes.py` (creación de `Flask app` y registro de blueprint)
- Templates de navegación:
  - `templates/index.html`
  - `templates/cliente_detail.html`
  - `templates/vendedores.html`
  - `templates/vendedores_con_saldos.html`
  - `templates/dashboard.html`
  - `templates/update_result.html`
  - `templates/report_result.html`

Pero **ojo**: `templates/report_template.html` es parte del flujo de reportes PDF, no de la UI web. Si lo eliminás, no hay PDF.

## Flujo objetivo “sin web” (recomendado)

La idea es que el sistema quede en 2 modos:

- **Manual**: ejecutar un script CLI para:
  1) actualizar datos
  2) generar y enviar reportes
- **Automático**: dejar `apscheduler` corriendo como servicio/tarea programada para ejecutar lo mismo según cron.

Para eso, el flujo mínimo a mantener es:

1) **Sesión SAP**: `get_Data_SAP/sesion.py` (cookies + refresh)
2) **Extracción SAP**: `A_get_salesperson_info.py`, `A_get_client_info.py`, `A_get_invoice.py`
3) **Carga SQLite**: `C_load_db.py`
4) **Modelo**: `models.py` (`obtener_datos`)
5) **Reportes + email**: `services.py` (`generate_and_send_reports`, `send_email`)
6) **Template PDF**: `templates/report_template.html`

### Punto clave a resolver al eliminar Flask
`services.generate_report_pdf()` hoy depende de `flask.render_template`.

Dos opciones equivalentes:

- **Opción A (mínimo cambio)**: mantener Flask solo como motor de templates (sin rutas) y crear un `app` mínimo para contexto.
- **Opción B (más limpio “sin web”)**: reemplazar `render_template` por Jinja2 puro (cargando `templates/` con `jinja2.Environment(FileSystemLoader(...))`) y así eliminar Flask por completo.

Este documento deja el flujo; la implementación final depende de cuál opción elijas.

## Checklist de funcionalidad (sin web)

- **SAP**
  - Login/renovación de sesión (cookies) funciona.
  - Se descargan 3 datasets: vendedores / clientes con deuda / facturas abiertas.
- **Datos locales**
  - Se recalcula `mi_base_datos.db` con tablas limpias y datos nuevos.
  - Se calculan `SaldoPendiente`, `DiasDesdeCreacion`, `Clasificacion`.
- **Reportes**
  - Se generan PDFs en `reports/` por vendedor con clientes asignados.
  - Orden por mayor vencido (desc).
- **Email**
  - SMTP con `STARTTLS` y credenciales `.env`.
  - Envío a `vendedor.Email` (o fallback) + CC fijo.
- **Scheduler**
  - Cron lunes/jueves 07:00 ejecuta (update + reportes).

