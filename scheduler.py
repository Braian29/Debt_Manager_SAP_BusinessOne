from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import logging
from get_Data_SAP.Z_run_scripts import run_scripts
from services import generate_and_send_reports, get_data
from utils import format_number
from routes import app  # Importar la instancia de Flask app

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scheduled_task():
    """
    Ejecuta los scripts de actualización de datos y genera/envía reportes.
    """
    logging.info("Iniciando tarea programada...")

    with app.app_context(): # Crear un contexto de aplicacion dentro de la tarea
        try:
            logging.info("Ejecutando scripts de actualización de datos...")
            if run_scripts():
                logging.info("Scripts de actualización de datos completados exitosamente.")
            else:
                logging.error("Los scripts de actualización de datos fallaron.")
                return  # Detener si la actualización falla

            logging.info("Obteniendo datos para la generación de reportes...")
            clientes_con_info, vendedores, _ = get_data()  # Obtener los datos necesarios

            logging.info("Generando y enviando reportes...")
            report_result = generate_and_send_reports(vendedores, clientes_con_info, format_number) # Pasamos el filtro

            if "Error" in report_result:
                logging.error(f"La generación de reportes falló: {report_result}")
            else:
                logging.info("Reportes generados y enviados exitosamente.")

        except Exception as e:
            logging.error(f"Ocurrió un error inesperado: {e}")
        
    logging.info("Tarea programada finalizada.")


# Configurar el scheduler
scheduler = BackgroundScheduler(daemon=True) #daemon=True
# Programar la tarea para que se ejecute los lunes y jueves a las 8:00 AM
trigger = CronTrigger(day_of_week='mon,thu', hour=17, minute=18)
scheduler.add_job(scheduled_task, trigger=trigger)

logging.info("Scheduler iniciado. Esperando tareas programadas...")
# Iniciar el scheduler
# No se inicia aquí, se hace desde app.py
# Mantener el script corriendo, ya no es necesario
# try:
#     while True:
#         time.sleep(1)  # Mantener el script ejecutándose (verificar cada segundo)
# except (KeyboardInterrupt, SystemExit):
#     # Detener el scheduler al salir
#     scheduler.shutdown()
#     logging.info("Scheduler detenido.")