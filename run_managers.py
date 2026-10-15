import logging

from services import generate_and_send_manager_report, get_data, update_data


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Flujo para gerentes:
    1) Actualiza datos (SAP → JSON → SQLite)
    2) Genera el Excel con la deuda de todos los vendedores por tramos de días
    3) Lo envía a los gerentes
    """
    logging.info("Iniciando reporte de gerentes (SAP → Excel → envío a gerentes)...")

    if not update_data():
        logging.error("Falló la actualización de datos. No se genera/envía el reporte de gerentes.")
        return 1

    clientes_con_info, _, _ = get_data()
    result = generate_and_send_manager_report(clientes_con_info)

    if "Error" in result:
        logging.error(result)
        return 2

    logging.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
