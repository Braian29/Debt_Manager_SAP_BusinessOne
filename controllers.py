# controllers.py
from flask import Blueprint, render_template, request
from services import get_data, update_data_service, generate_and_send_reports
from utils import format_number
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

routes_blueprint = Blueprint('routes', __name__)

@routes_blueprint.route('/')
def index():
    clientes = get_data()[0]
    return render_template('index.html', clientes=clientes)

@routes_blueprint.route('/cliente/<string:card_code>')
def cliente_detail(card_code):
    clientes = get_data()[0]
    cliente = next((c for c in clientes if c['CardCode'] == card_code), None)
    if cliente:
        return render_template('cliente_detail.html', cliente=cliente)
    else:
        return "Cliente no encontrado", 404

@routes_blueprint.route('/vendedores')
def vendedores_list():
    vendedores = get_data()[1]
    return render_template('vendedores.html', vendedores=vendedores)

@routes_blueprint.route('/vendedores_con_saldos')
def vendedores_con_saldos_list():
    vendedores_con_saldos = get_data()[2]
    return render_template('vendedores_con_saldos.html', vendedores=vendedores_con_saldos)
   
@routes_blueprint.route('/dashboard')
def dashboard():
    clientes_con_info, _, vendedores_con_saldos = get_data()
    total_deuda = sum(cliente.get('CurrentAccountBalance', 0) or 0 for cliente in clientes_con_info)

    saldos_por_categoria_clientes = {
      'En Fecha':0,
      'Proxima a Vencer':0,
      'Vencida':0,
    }
    for cliente in clientes_con_info:
       for categoria,saldo in cliente.get('saldos_por_categoria').items():
          saldos_por_categoria_clientes[categoria] += saldo

    labels_vendedores = [vendedor.get('SalesEmployeeName') for vendedor in vendedores_con_saldos]
    deudas_vendedores = [vendedor.get('total_saldo',0) for vendedor in vendedores_con_saldos]
  
    return render_template('dashboard.html', 
                           total_deuda=total_deuda, 
                           saldos_por_categoria_clientes=saldos_por_categoria_clientes,
                           labels_vendedores = labels_vendedores,
                           deudas_vendedores = deudas_vendedores
                           )

@routes_blueprint.route('/update_data', methods=['POST'])
def update_data():
    try:
       message, message_type = update_data_service()
       return render_template('update_result.html', message=message, message_type=message_type), 200
    except Exception as e:
        logging.error(f"Error updating data: {e}")
        return render_template('update_result.html', message="Error al actualizar los datos.", message_type="error"), 500

@routes_blueprint.route('/generate_reports', methods=['POST'])
def generate_reports():
  try:
      clientes_con_info, vendedores,_ = get_data()
      result = generate_and_send_reports(vendedores, clientes_con_info, format_number)
      if "Error" in result:
         return render_template('report_result.html', message=result, message_type="error"), 500
      return render_template('report_result.html', message=result, message_type="success")
  except Exception as e:
        logging.error(f"Error generating reports: {e}")
        return render_template('report_result.html', message="Error al generar reportes.", message_type="error"), 500