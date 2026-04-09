import logging

from services import generate_and_send_client_reports, get_data, update_data
from utils import format_number


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Flujo completo para clientes:
    1) Actualiza datos (SAP → JSON → SQLite)
    2) Arma el cuerpo del correo con facturas abiertas (tabla en texto)
    3) Envía un email por cliente según vencimientos (DocDueDate < hoy)
    """
    logging.info("Iniciando envíos a clientes (SAP → texto en correo)...")

    if not update_data():
        logging.error("Falló la actualización de datos. No se generan/envían reportes a clientes.")
        return 1

    clientes_con_info, _, _ = get_data()
    result = generate_and_send_client_reports(clientes_con_info, format_number)

    if "Error" in result:
        logging.error(result)
        return 2

    logging.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

