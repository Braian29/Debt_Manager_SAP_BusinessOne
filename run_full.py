import logging

from services import generate_and_send_reports, get_data, update_data
from utils import format_number


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Flujo completo:
    1) Actualiza datos (SAP → JSON → SQLite)
    2) Genera PDFs por vendedor
    3) Envía emails a vendedores (con CC según configuración)
    """
    logging.info("Iniciando flujo completo (SAP → PDFs → envío a vendedores)...")

    if not update_data():
        logging.error("Falló la actualización de datos. No se generan/envían reportes.")
        return 1

    clientes_con_info, vendedores, _ = get_data()
    result = generate_and_send_reports(vendedores, clientes_con_info, format_number)

    if "Error" in result:
        logging.error(result)
        return 2

    logging.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

