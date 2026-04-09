# models.py
import sqlite3
from collections import defaultdict
from datetime import datetime, date

def obtener_conexion(db_path):
   conn = sqlite3.connect(db_path)
   conn.row_factory = sqlite3.Row
   return conn


def _parse_date(d):
    if not d:
        return None
    s = str(d)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None

def obtener_datos(db_path):
    conn = obtener_conexion(db_path)
    cursor = conn.cursor()

    # Obtener clientes
    cursor.execute("SELECT * FROM clientes_con_deuda")
    clientes = [dict(row) for row in cursor.fetchall()]
    
    # Obtener vendedores
    cursor.execute("SELECT * FROM vendedores")
    vendedores = [dict(row) for row in cursor.fetchall()]

    # Obtener facturas
    cursor.execute("SELECT * FROM facturas_abiertas")
    invoices = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    vendedores_map = {v['SalesEmployeeCode']: v for v in vendedores}

    facturas_por_cliente = defaultdict(list)
    for invoice in invoices:
        card_code = invoice.get('CardCode')
        try:
           invoice['PaidToDate'] = float(invoice.get('PaidToDate', 0))
        except (ValueError, TypeError):
          invoice['PaidToDate'] = 0
        # Normalizar fechas para uso posterior (criterio por vencimiento)
        invoice['_DocDueDate'] = _parse_date(invoice.get('DocDueDate'))
        invoice['_DocDate'] = _parse_date(invoice.get('DocDate'))
        facturas_por_cliente[card_code].append(invoice)
    clientes_con_info = []
    for cliente in clientes:
        vendedor_code = cliente.get('SalesPersonCode')
        vendedor = vendedores_map.get(vendedor_code)
        
        saldos_por_categoria = {
            'En Fecha': 0,
            'Proxima a Vencer': 0,
            'Vencida': 0
        }
         
        total_saldo = 0
        for factura in facturas_por_cliente.get(cliente.get('CardCode'), []):
            saldo_pendiente = factura.get('SaldoPendiente',0)
            clasificacion = factura.get('Clasificacion')
            total_saldo += saldo_pendiente
            if clasificacion in saldos_por_categoria:
               saldos_por_categoria[clasificacion] += saldo_pendiente

        saldo_vencido = saldos_por_categoria['Vencida']
        porcentaje_vencido = (saldo_vencido / total_saldo) * 100 if total_saldo else 0

        # Criterio pedido: "vencido si hay al menos 1 factura con DocDueDate < hoy"
        today = date.today()
        facturas_cliente = facturas_por_cliente.get(cliente.get('CardCode'), [])
        has_overdue_due_date = any(
            (f.get('_DocDueDate') is not None)
            and (f.get('_DocDueDate') < today)
            and float(f.get('SaldoPendiente') or 0) > 0
            for f in facturas_cliente
        )
       
        cliente_info = {
            'CardCode': cliente.get('CardCode'),
            'CardName': cliente.get('CardName'),
            'CurrentAccountBalance': cliente.get('CurrentAccountBalance'),
            'EmailAddress': cliente.get('EmailAddress'),
            'vendedor': vendedor.get('SalesEmployeeName') if vendedor else "Sin Vendedor Asignado",
            'vendedor_code': vendedor_code if vendedor else None,
            'facturas': facturas_cliente,
            'saldos_por_categoria': saldos_por_categoria,
            'porcentaje_vencido': porcentaje_vencido,
            'has_overdue_due_date': has_overdue_due_date,
        }
        clientes_con_info.append(cliente_info)

        
        
    # Agrupar información por vendedor
    vendedores_con_saldos = []
    for vendedor in vendedores:
        vendedor_code = vendedor.get('SalesEmployeeCode')
        
        saldos_por_categoria_vendedor = {
             'En Fecha': 0,
             'Proxima a Vencer': 0,
            'Vencida': 0
         }
        total_saldo_vendedor = 0
        clientes_del_vendedor = [c for c in clientes_con_info if c.get('vendedor_code') == vendedor_code]
        for cliente in clientes_del_vendedor:
              for categoria,saldo in cliente.get('saldos_por_categoria').items():
                  saldos_por_categoria_vendedor[categoria] += saldo
              total_saldo_vendedor += cliente.get('CurrentAccountBalance',0)
          
        saldo_vencido_vendedor = saldos_por_categoria_vendedor['Vencida']
        porcentaje_vencido_vendedor = (saldo_vencido_vendedor / total_saldo_vendedor) * 100 if total_saldo_vendedor else 0

        vendedor_info = {
           'SalesEmployeeCode': vendedor.get('SalesEmployeeCode'),
           'SalesEmployeeName': vendedor.get('SalesEmployeeName'),
           'saldos_por_categoria': saldos_por_categoria_vendedor,
           'total_saldo':total_saldo_vendedor,
           'porcentaje_vencido':porcentaje_vencido_vendedor
        }
        vendedores_con_saldos.append(vendedor_info)
    vendedores_con_saldos = [vendedor for vendedor in vendedores_con_saldos if vendedor['total_saldo'] > 0]


    return clientes_con_info, vendedores, vendedores_con_saldos