import logging

from services import generate_reports_only, get_data, update_data
from utils import format_number


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Ejecuta el flujo completo sin web:
    1) Actualiza datos (SAP → JSON → SQLite)
    2) Genera PDFs por vendedor
    3) (No envía correos)
    """
    logging.info("Iniciando flujo headless (sin web)...")

    if not update_data():
        logging.error("Falló la actualización de datos. Se aborta el envío de reportes.")
        return 1

    clientes_con_info, vendedores, _ = get_data()
    result = generate_reports_only(vendedores, clientes_con_info, format_number)

    if "Error" in result:
        logging.error(result)
        return 2

    logging.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

