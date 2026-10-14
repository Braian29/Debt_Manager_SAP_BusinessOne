# Contexto del proyecto — Deuda_SAP

Documento de contexto para humanos y agentes. Describe **qué es**, **cómo fluye**, **dónde está cada pieza** y **qué no hay que romper**.

---

## 1. Qué es

Aplicación **CLI (sin web)** de Super-Clin que:

1. Extrae de **SAP Business One Service Layer** vendedores, clientes con deuda y facturas abiertas.
2. Persiste en **JSON** (`data/`) y luego en **SQLite** (`mi_base_datos.db`).
3. Genera y envía reportes por correo:
   - **Vendedores**: 1 PDF por vendedor (adjunto) + CC a casillas internas.
   - **Clientes**: 1 email por cliente con el estado de cuenta **en el cuerpo** (sin PDF).

Empresa: Super-Clin. No hay UI Flask (se eliminó). El scheduler sigue existiendo pero el uso habitual es **ejecutar scripts a mano**.

---

## 2. Stack

| Pieza | Tecnología |
|---|---|
| Lenguaje | Python 3 (en Windows se usa `py`) |
| SAP | Service Layer OData (`httpx`, cookies en `cookies.json`) |
| Persistencia | JSON intermedio + SQLite |
| PDF vendedores | ReportLab / Platypus (`reportlab_report.py`) |
| Email | SMTP `STARTTLS` (puerto 587) |
| Config | `.env` + `config.py` |
| Scheduler | APScheduler (lunes y jueves 07:00) |

Dependencias: `requirements.txt` (`APScheduler`, `httpx`, `python-dotenv`, `reportlab`).

---

## 3. Flujo de datos (punta a punta)

```
SAP Service Layer
        │
        ▼
get_Data_SAP/sesion.py          login → cookies.json
        │
        ▼
B_get_allinfo.py (concurrente)
  ├── A_get_salesperson_info.py → data/SalesPersons.json
  ├── A_get_client_info.py      → data/clientes_con_deuda.json
  └── A_get_invoice.py          → data/invoicesAbiertas.json
        │
        ▼
C_load_db.py                    limpia e inserta SQLite
        │
        ▼
mi_base_datos.db
  ├── clientes_con_deuda
  ├── vendedores
  └── facturas_abiertas         (+ SaldoPendiente, DiasDesdeCreacion, Clasificacion)
        │
        ▼
models.obtener_datos()          une clientes + vendedor + facturas + KPIs
        │
        ├── run_full.py / scheduler  → PDF vendedor + email
        ├── run_headless.py          → solo PDF
        └── run_clients.py           → email texto por cliente
```

Orquestador de extracción: `get_Data_SAP/Z_run_scripts.py` → `run_scripts()` (B luego C).  
Reintento de sesión SAP: `services.update_data()` (hasta 2 intentos + `get_new_session()`).

---

## 4. Puntos de entrada (qué ejecutar)

En PowerShell, desde la raíz del repo:

| Script | Qué hace |
|---|---|
| `py run_full.py` | SAP → DB → PDF por vendedor → envía emails a vendedores |
| `py run_clients.py` | SAP → DB → 1 mail por cliente (tabla de facturas en el cuerpo) |
| `py run_all.py` | `run_full` y, si OK, `run_clients`. Si fallan vendedores, **no** corre clientes |
| `py run_headless.py` | SAP → DB → solo genera PDFs (no manda mails) |
| `py run_clients_test.py` | SAP → DB → 5 clientes (más vencido primero) a un mail de prueba |

Códigos de salida: `0` ok, `1` falló update SAP/DB, `2` falló generación/envío.

`run_all.py` actualiza SAP **dos veces** (una por cada flujo). Es intencional por simplicidad, no por diseño de caché.

---

## 5. Mapa de archivos

### Núcleo

| Archivo | Rol |
|---|---|
| `config.py` | Ruta DB, SMTP, `MAIL_DELAY_SECONDS` (default 2.5). Carga `.env` con varios encodings (Windows). |
| `models.py` | `obtener_datos(db_path)`: arma `clientes_con_info`, `vendedores`, `vendedores_con_saldos`. |
| `services.py` | Lógica de negocio: update, PDF, SMTP, mails vendedores y clientes. |
| `utils.py` | `format_number` con locale `es_AR.utf8`. |
| `scheduler.py` | Cron lun/jue 07:00 → update + reportes **solo vendedores** (no clientes). |

### Reportes PDF

| Archivo | Rol |
|---|---|
| `reportlab_report.py` | PDF de vendedor (portada KPIs + detalle clientes). Salida: `reports/{SalesEmployeeCode}_report.pdf`. |
| `reportlab_client_report.py` | PDF de estado de cuenta por cliente. **No está cableado** al flujo de mails actuales. |
| `templates/report_template.html` | Plantilla HTML legacy (xhtml2pdf). **Ya no se usa**; el PDF va por ReportLab. |

### Extracción SAP (`get_Data_SAP/`)

| Archivo | Rol |
|---|---|
| `sesion.py` | Login Service Layer. Env: `COMPANY_DB`, `PASSWORD`, `USERNAME_SAP`, `URL`. Cookies → `cookies.json`. |
| `A_get_salesperson_info.py` | GET `SalesPersons`. |
| `A_get_client_info.py` | GET `BusinessPartners` con filtros. |
| `A_get_invoice.py` | POST `QueryService_PostQuery` (`$crossjoin` Invoices + BusinessPartners), paginado 1000. |
| `B_get_allinfo.py` | Corre las 3 A_* en paralelo (`ThreadPoolExecutor`). |
| `C_load_db.py` | Crea tablas, **DELETE** de las 3, inserta JSON. Calcula saldo y clasificación. |
| `Z_run_scripts.py` | Orquesta B → C. |
| `D_Inconsistencias.py` | Diagnóstico: clientes con deuda sin facturas. **No forma parte del flujo principal.** |

### Datos y salidas (runtime, no “código”)

- `data/*.json` — dumps SAP.
- `mi_base_datos.db` — SQLite (en `.gitignore`).
- `cookies.json` — sesión SAP.
- `reports/` — PDFs de vendedores.
- `reports_clientes/` — PDFs de clientes (si se generan por el módulo ReportLab de cliente).

---

## 6. SAP: endpoints, filtros y campos

### Sesión

- POST a `URL` (login) con `CompanyDB`, `UserName`, `Password`.
- TLS `verify=False`.
- Header: `Prefer: odata.maxpagesize=10000`.
- 401 → se intenta `get_new_session()` una vez.

### Vendedores — `SalesPersons`

Campos: `SalesEmployeeCode`, `SalesEmployeeName`, `Telephone`, `Mobile`, `Email`.

### Clientes — `BusinessPartners`

Select: `CardCode`, `CardName`, `PayTermsGrpCode`, `PriceListNum`, `SalesPersonCode`, `Cellular`, `EmailAddress`, `CurrentAccountBalance`.

Filtro:

- `CardType eq 'cCustomer'`
- `CurrentAccountBalance gt 1000`
- `U_Empleado eq 'N'` (excluye socios marcados como empleado)

### Facturas — `QueryService_PostQuery`

`$crossjoin(Invoices,BusinessPartners)` expandiendo Invoices.

Filtro:

- Join por `CardCode`
- `BusinessPartners/U_Empleado eq 'N'`
- `Invoices/DocumentStatus eq 'O'` (abiertas)
- `BusinessPartners/CurrentAccountBalance gt 10`  ← umbral **distinto** al de clientes (> 1000)

Campos factura: `CardCode`, `CardName`, `DocTotal`, `PaidToDate`, `NumAtCard`, `DocDate`, `DocDueDate`.

Paginación: `$top=1000` / `$skip`.

**Implicación:** un cliente puede estar en `clientes_con_deuda` y no tener facturas en `facturas_abiertas` (umbrales distintos). `D_Inconsistencias.py` existe para eso.

La URL base de Service Layer está **hardcodeada** en los `A_*.py` (`https://177.85.33.53:50695/b1s/v1/`). El `.env` solo define el endpoint de Login.

---

## 7. Modelo de datos SQLite

Tres tablas. Cada update hace `DELETE` + `INSERT` (no hay histórico).

### `clientes_con_deuda`

`CardCode` PK, `CardName`, `PayTermsGrpCode`, `PriceListNum`, `SalesPersonCode`, `Cellular`, `EmailAddress`, `CurrentAccountBalance`.

### `vendedores`

`SalesEmployeeCode` PK, `SalesEmployeeName`, `Telephone`, `Mobile`, `Email`.

### `facturas_abiertas`

Sin PK. `CardCode`, `CardName`, `DocTotal`, `NumAtCard`, `DocDate`, `PaidToDate`, `DocDueDate`, `DiasDesdeCreacion`, `Clasificacion`, `SaldoPendiente`.

Cálculos en `C_load_db.py`:

- `SaldoPendiente = DocTotal - PaidToDate`
- `DiasDesdeCreacion` = hoy − `DocDate` (días de calendario)
- `Clasificacion` por antigüedad de **emisión** (no por `DocDueDate`):
  - `>= 30` → `Vencida`
  - `20–29` → `Proxima a Vencer`
  - `< 20` → `En Fecha`

---

## 8. Lógica de negocio en `models.py`

`obtener_datos()` devuelve:

1. **`clientes_con_info`**: cliente + vendedor + facturas + `saldos_por_categoria` + `porcentaje_vencido` + `has_overdue_due_date`.
2. **`vendedores`**: filas crudas (incluye `Email`).
3. **`vendedores_con_saldos`**: agregados; se filtran los de `total_saldo == 0`.

Hay **dos criterios de “vencido”** y no son equivalentes:

| Criterio | Dónde | Cómo |
|---|---|---|
| Clasificación por antigüedad | PDF vendedor, `saldos_por_categoria`, `% vencido` | Días desde `DocDate` (30/20/0) |
| Vencimiento real | Mails a clientes, `has_overdue_due_date` | Al menos 1 factura con `DocDueDate < hoy` y saldo > 0 |

No unificar sin decidir negocio: el PDF de vendedor usa el primero; el texto a clientes usa el segundo.

---

## 9. Correos

### SMTP

- Servidor/puerto/usuario/clave: `.env` (`MAIL_*`).
- `STARTTLS`, timeout 40 s.
- `MAIL_DELAY_SECONDS` (default 2.5) entre mails a **clientes** para evitar 450 “too much mail”.
- Clientes: reintentos con backoff (55 s → hasta 200 s, 5 intentos) y reconexión SMTP.
- Vendedores: un `send_email` por vendedor (abre/cierra SMTP cada vez). Sin el mismo retry de rate-limit.

### Vendedores (`generate_and_send_reports`)

- Un PDF por vendedor con clientes; orden: mayor saldo `Vencida` primero.
- Destino: `vendedor.Email` o fallback `superclinsys@gmail.com`.
- CC actuales: `romina.galdos@`, `cuentas@`, `braian.alonso@`, `carolina.kundler@`, `miguel.molachino@` (dominio `super-clin.com.ar`).
- Si un vendedor falla (PDF o SMTP), **se aborta el resto**.

### Clientes (`generate_and_send_client_reports`)

- 1 mail por cliente, **sin adjunto**.
- Se salta si no hay email o si `is_valid_client_email` lo rechaza (valores tipo `no@…`, `n/a`, etc.).
- Asunto:
  - Con vencido por `DocDueDate`: `Estado de cuenta – Documentos vencidos`
  - Sin vencido: `Estado de cuenta – Próximos vencimientos`
- Cuerpo: saldos + tabla texto (Doc, Vto, Total, Pagado, Saldo). Facturas vencidas primero.
- Nota en el mail: **no incluye NC ni pagos no conciliados**.
- Modo test: `limit` + `override_to` (asunto `[TEST CLIENTES]`, destinatario real en el cuerpo).

---

## 10. Configuración (`.env`)

No commitear. Variables:

```
# SAP
COMPANY_DB=
PASSWORD=
USERNAME_SAP=
URL=                    # endpoint Login Service Layer

# SMTP
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_SERVER=
MAIL_PORT=587
MAIL_DELAY_SECONDS=2.5  # opcional
```

`.gitignore` cubre `.env` y `mi_base_datos.db`. `cookies.json` y `data/*.json` **no** están ignorados: pueden contener datos operativos.

---

## 11. Convenciones y trampas

1. **Sin Flask.** No reintroducir `app.py` / `routes.py` / `controllers.py` salvo pedido explícito.
2. **PDF = ReportLab**, no HTML/xhtml2pdf. `templates/report_template.html` es leftover.
3. **Update destructivo:** cada corrida borra las 3 tablas. No hay incremental.
4. **Umbrales SAP distintos:** clientes > 1000 vs facturas con saldo BP > 10.
5. **URL SAP hardcodeada** en extractores; login sí usa `.env`.
6. **Locale** `es_AR.utf8` en `utils.py`: en Windows puede fallar si el locale no está instalado.
7. **Scheduler ≠ `run_all`:** el cron solo manda vendedores. Clientes son manuales (`run_clients` / `run_all`).
8. **`run_all` refresca SAP dos veces.**
9. **Validación de email** solo en clientes, no en vendedores.
10. **`D_Inconsistencias.py`** usa pandas y un import de cookies distinto; es herramienta aparte, no del pipeline.
11. Responder y documentar en **español**. Ejecutar en Windows con `py`.

---

## 12. Cómo extender (guía corta)

- **Cambiar filtros SAP:** `A_get_client_info.py` / `A_get_invoice.py`.
- **Cambiar clasificación de facturas:** `C_load_db.clasificar_factura` (PDF vendedor) y/o `has_overdue_due_date` en `models.py` (mails clientes).
- **Layout PDF vendedor:** `reportlab_report.py`.
- **Texto/asunto de mails clientes:** `_build_client_email` y el armado de `body` en `services.py`.
- **CC / fallback vendedores:** `generate_and_send_reports` en `services.py`.
- **Nuevo punto de entrada CLI:** copiar el patrón de `run_full.py` / `run_clients.py` (logging + `update_data` + `get_data` + return codes).

---

## 13. Estado actual (agosto 2026)

- Pipeline CLI estable: extracción SAP concurrente, SQLite, PDF ReportLab, SMTP.
- Flujo clientes en producción vía cuerpo de mail (PDF cliente existe pero no se adjunta).
- Web Flask desmontada.
- `run_all.py` es el atajo para vendedores + clientes.
- Documentación previa más detallada del pipeline: `FLUJO_DATOS_SIN_WEB.md` y `README.md`.
