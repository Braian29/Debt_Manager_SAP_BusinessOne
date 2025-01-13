# app.py
from routes import app
from scheduler import scheduler
import logging
from asgiref.wsgi import WsgiToAsgi #Importante

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    logging.info("Iniciando el scheduler...")
    scheduler.start()

    try:
        logging.info("Servidor Flask iniciado por Uvicorn...")
    except Exception as e:
        logging.error(f"Error al iniciar el servidor Flask: {e}")
    finally:
        logging.info("Deteniendo el scheduler")
        scheduler.shutdown()

asgi_app = WsgiToAsgi(app) 


#### Se corre con :
# 
# 
# uvicorn app:asgi_app --host 0.0.0.0 --port 5010 --workers 4