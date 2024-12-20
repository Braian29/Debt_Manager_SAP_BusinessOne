import concurrent.futures
from A_get_salesperson_info import get_salesperson_data
from A_get_client_info import get_client_data
from A_get_invoice import get_invoice_data

def run_get_allinfo():
    """
    Ejecuta las funciones de obtención de datos de SAP de forma concurrente.
    """
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(get_salesperson_data),
            executor.submit(get_client_data),
            executor.submit(get_invoice_data)
        ]

        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                print(f"Una función generó una excepción: {exc}")
                results.append(False) #Marcamos el resultado como fallo.

        if all(results):
             print("Todas las funciones finalizaron correctamente")
             return True
        else:
            print("Al menos una función falló durante la ejecución.")
            return False

if __name__ == "__main__":
    run_get_allinfo()