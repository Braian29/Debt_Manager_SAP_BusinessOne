# app.py
from routes import app
from scheduler import scheduler 
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    logging.info("Iniciando el scheduler...")
    scheduler.start() 

    try:
        logging.info("Iniciando el servidor Flask...")
        app.run(debug=True, host='0.0.0.0', port=5010, use_reloader=False)  # use_reloader=False para evitar que el scheduler se ejecute dos veces
    except Exception as e:
        logging.error(f"Error al iniciar el servidor Flask: {e}")
    finally:
        logging.info("Deteniendo el scheduler")
        scheduler.shutdown()