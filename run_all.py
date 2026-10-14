import logging

import run_clients
import run_full


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Ejecuta en un solo comando:
    - Envío a vendedores (PDF por vendedor, adjunto).
    - Envío a clientes (estado de cuenta en el cuerpo del mail).
    """
    logging.info("Iniciando flujo completo: vendedores + clientes...")

    rc_vendedores = run_full.main()
    if rc_vendedores != 0:
        logging.error("Fallo el flujo de vendedores (código=%s). Se aborta clientes.", rc_vendedores)
        return rc_vendedores

    rc_clientes = run_clients.main()
    if rc_clientes != 0:
        logging.error("Fallo el flujo de clientes (código=%s).", rc_clientes)
        return rc_clientes

    logging.info("Flujo completo finalizado (vendedores + clientes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

