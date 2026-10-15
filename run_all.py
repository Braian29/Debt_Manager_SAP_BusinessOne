import logging

import run_clients
import run_full
import run_managers


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    """
    Ejecuta en un solo comando:
    - Envío a vendedores (Excel por vendedor, adjunto).
    - Envío a gerentes (Excel con todos los vendedores por tramos de días).
    - Envío a clientes (estado de cuenta en el cuerpo del mail).
    """
    logging.info("Iniciando flujo completo: vendedores + gerentes + clientes...")

    rc_vendedores = run_full.main()
    if rc_vendedores != 0:
        logging.error("Fallo el flujo de vendedores (código=%s). Se aborta gerentes y clientes.", rc_vendedores)
        return rc_vendedores

    rc_gerentes = run_managers.main()
    if rc_gerentes != 0:
        logging.error("Fallo el flujo de gerentes (código=%s). Se aborta clientes.", rc_gerentes)
        return rc_gerentes

    rc_clientes = run_clients.main()
    if rc_clientes != 0:
        logging.error("Fallo el flujo de clientes (código=%s).", rc_clientes)
        return rc_clientes

    logging.info("Flujo completo finalizado (vendedores + gerentes + clientes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
