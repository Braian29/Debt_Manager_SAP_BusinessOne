import json
import os

def obtener_cardcodes(archivo_json):
    """
    Obtiene una lista de CardCode de un archivo JSON.
    Args:
        archivo_json (str): La ruta al archivo JSON que contiene los datos.
    Returns:
        list: Una lista de todos los CardCode encontrados en el archivo, o una lista vacía si el archivo no se encuentra o no contiene datos válidos.
    """
    cardcodes = []
    try:
        with open(archivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f) 

        if isinstance(data, list):
            for item_list in data:
                if isinstance(item_list, dict) and "value" in item_list and isinstance(item_list["value"], list):
                     for item in item_list["value"]:
                        if isinstance(item, dict) and "CardCode" in item:
                            cardcodes.append(item["CardCode"])
        else:
             print ("Formato inesperado en el JSON. El archivo principal debe ser una lista.")
    except FileNotFoundError:
        print(f"Error: El archivo '{archivo_json}' no se encontró.")
    except json.JSONDecodeError:
        print(f"Error: El archivo '{archivo_json}' no contiene un JSON válido.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
    
    return cardcodes

if __name__ == "__main__":
    archivo_json = 'data/clientes_con_deuda.json'
    cardcodes = obtener_cardcodes(archivo_json)

    if cardcodes:
        print("CardCodes encontrados:")
        for cardcode in cardcodes:
            print(cardcode)
        
        # Definir el directorio y el archivo de salida
        output_dir = 'data'
        output_file = 'CardCodes.json'
        output_path = os.path.join(output_dir, output_file)

        # Asegurarse que el directorio existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Guardar la lista en un nuevo archivo JSON
        with open(output_path, "w", encoding='utf-8') as outfile:
            json.dump(cardcodes, outfile, indent=4)

        print (f"\nLos CardCodes se han guardado en el archivo: {output_path}")
        
    else:
        print("No se encontraron CardCodes o hubo un error al procesar el archivo.")