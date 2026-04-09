import logging

from services import generate_and_send_client_reports, get_data, update_data
from utils import format_number


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


TEST_TO = "braian.alonso@super-clin.com.ar"
LIMIT = 5


def main() -> int:
    """
    Prueba controlada:
    - Actualiza datos (SAP → DB)
    - Toma 5 clientes (mayor vencido primero)
    - Envía el mismo cuerpo de estado de cuenta a TEST_TO (no a los clientes reales)
    """
    logging.info("Iniciando PRUEBA de envíos a clientes (5 clientes → %s)...", TEST_TO)

    if not update_data():
        logging.error("Falló la actualización de datos. No se envían pruebas.")
        return 1

    clientes_con_info, _, _ = get_data()
    result = generate_and_send_client_reports(
        clientes_con_info,
        format_number,
        limit=LIMIT,
        override_to=TEST_TO,
    )

    if "Error" in result:
        logging.error(result)
        return 2

    logging.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

