import os
import pandas as pd
import pdfplumber
import re

# Ruta donde se guardarán los PDFs subidos
data_path = "data/pdfs"
output_csv = "data/mercadata.csv"

def categorize_item(item):
    """Función para categorizar los ítems"""
    # Normalizamos el nombre del ítem
    item = re.sub(r'[^a-zA-Z\s]', '', item).lower()
    
    # Diccionario de categorías por palabras clave
    categories = {
        "fruta": ["aguacate", "fresón", "nectarina", "paraguayo", "tomate", "pera rocha", "ciruela roja", "banana", "pera conferencia", "mezcla de frutos rojos"],
        "frutos secos": ["almendra", "anacardo", "nuez", "pasas sultanas"],
        "snacks": ["patatas", "chocolate", "chicles", "cereales rellenos", "patatas lisas", "patatas chili lima", "nachos"],
        "panadería": ["panecillo", "barra de pan", "barra rústica", "croqueta", "tortillas mexicanas", "chapata cristal", "pan m. 55% centeno", "pan viena redondo"],
        "lácteos": ["leche", "yogur griego", "mantequilla", "queso cheddar", "yogur natural x6", "griego ligero natural", "griego stracciatella p-6", "queso rallado pizza", "nata montar"],
        "bebidas y caldos": ["caldo de pollo", "salsa de soja"],
        "verduras y legumbres": ["garbanzo", "maíz", "ensalada", "cebolla", "pimiento tricolor", "champiñón pequeño", "calabacín verde", "zanahoria", "ajo seco", "tomate canario", "brotes tiernos"],
        "carne": ["jamoncitos de pollo", "burger vacuno cerdo", "chuleta aguja", "lomo trozo", "cuarto trasero congelado", "burger mixta cerdo", "albóndigas", "chuleta aguja", "lomo trozo"],
        "condimentos y salsas": ["ketchup", "azúcar", "sabor"],
        "despensa": ["arroz redondo", "macarrón", "mezcla de semillas", "harina", "pasta", "avena crunchy"],
        "conservas": ["atún", "tomate triturado", "aceitunas con anchoa", "pepinillo pequeño"],
        "platos preparados": ["hummus", "preparado andaluz", "ensaladilla rusa"],
        "otros": ["huevos frescos", "estropajo salvauñas"]
    }

    for category, keywords in categories.items():
        if any(keyword in item for keyword in keywords):
            return category
    return "otros"

non_food_items = [
    "TOTAL", "TARJETA", "MASTERCARD", "IVA", "G", "OP", "FACTURA", "BANCARIA", "AID", "ARC", 
    "IMPORT", "N.C", "AUT", "SE ADMITEN DEVOLUCIONES", "CUOTA", "BASE IMPONIBLE", "€", 
    "TELÉFONO", "AVDA.", "N.C:", "AUT:", "Importe:", "MASTERCARD", "****", "ARC:", "AID:", 
    "SE ADMITEN DEVOLUCIONES CON TICKET", "FACTURA SIMPLIFICADA:", "OP:","UDS", "€"
]

def is_non_food_item(item):
    """Función para verificar si un ítem es un non_food_item"""
    for non_food in non_food_items:
        if non_food in item:
            return True
    return False

# Paso 1: Función process_pdfs para procesar los archivos PDF subidos
def process_pdfs(uploaded_files):
    """Procesa los archivos PDF subidos y guarda los datos en CSV"""
    data = []

    # Guardar los archivos PDF subidos en la carpeta designada
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    for uploaded_file in uploaded_files:
        pdf_path = os.path.join(data_path, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Procesar cada archivo PDF
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            text = page.extract_text()

            if text:
                date_match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", text)
                fecha = date_match.group(0) if date_match else "Fecha no encontrada"

                ticket_match = re.search(r"FACTURA SIMPLIFICADA:\s+([0-9\-]+)", text)
                identificativo = ticket_match.group(1) if ticket_match else "Identificativo no encontrado"

                items = re.findall(r"\d\s+([A-Z\s]+)\s+(\d+,\d{2})", text)
                for item, precio in items:
                    item = item.strip()
                    if not is_non_food_item(item):
                        precio = float(precio.replace(",", "."))
                        categoria = categorize_item(item)
                        data.append([fecha, identificativo, item, categoria, precio])
            else:
                print(f"No se pudo extraer texto del archivo: {uploaded_file.name}")

    if data:
        df = pd.DataFrame(data, columns=["fecha", "identificativo de ticket", "item", "categoría", "precio"])
        df.to_csv(output_csv, index=False)
        print(f"Archivo CSV generado con éxito: {output_csv}")
    else:
        print("No se encontraron datos para escribir en el archivo CSV.")