import os
import pandas as pd
import pdfplumber
import re
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Define paths and file names
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
    """Función para verificar si un ítem no es alimenticio."""
    return any(non_food in item for non_food in non_food_items)

def extract_location(text):
    """Función para extraer la ubicación de la tienda del ticket."""
    # Busca el texto entre "MERCADONA, S.A." y "TELÉFONO:"
    location_match = re.search(r"MERCADONA,\s+S\.A\.\s+[^\n]*\n(.*?)(?=TELÉFONO:)", text, re.DOTALL)
    return location_match.group(1).strip() if location_match else "Ubicación no encontrada"



def process_pdfs(uploaded_files):
    data = []

    # Asegurar que el directorio de datos exista
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
                # Extraer ubicación
                location = extract_location(text)

                # Extraer fecha e identificador del ticket
                date_match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", text)
                fecha = date_match.group(0) if date_match else "Fecha no encontrada"

                ticket_match = re.search(r"FACTURA SIMPLIFICADA:\s+([0-9\-]+)", text)
                identificativo = ticket_match.group(1) if ticket_match else "Identificativo no encontrado"

                # Extraer ítems y precios
                items = re.findall(r"\d\s+([A-Z\s]+)\s+(\d+,\d{2})", text)
                for item, precio in items:
                    item = item.strip()
                    if not is_non_food_item(item):
                        precio = float(precio.replace(",", "."))
                        categoria = categorize_item(item)
                        data.append([fecha, identificativo, location, item, categoria, precio])
            else:
                st.warning(f"No se pudo extraer texto del archivo: {uploaded_file.name}")

    if data:
        # Crear un DataFrame y guardarlo localmente como CSV
        df = pd.DataFrame(data, columns=["fecha", "identificativo de ticket", "ubicación", "item", "categoría", "precio"])
        df.to_csv(output_csv, index=False)
        st.success(f"Archivo CSV generado con éxito: {output_csv}")

        try:
            # Conectar y leer datos existentes de Google Sheets
            conn = st.connection("gsheets", type=GSheetsConnection)
            existing_data = conn.read(worksheet="Sheet1")  # Cambia "Sheet1" por el nombre de tu hoja

            # Verificar si hay nuevos datos para agregar
            new_data = pd.concat([existing_data, df]).drop_duplicates(keep=False)

            if not new_data.empty:
                # Actualizar la hoja de cálculo con nuevos datos
                conn.update(worksheet="Sheet1", data=new_data)  # Cambia "Sheet1" por el nombre de tu hoja
            else:
                st.info("No hay datos nuevos para actualizar")
        except Exception as e:
            st.error(f"Error al conectarse a Google Sheets: {e}")
    else:
        st.info("No se encontraron datos para escribir en el archivo CSV.")

def main():
    st.title("Procesador de Tickets PDF")

    # Permitir a los usuarios subir archivos PDF
    uploaded_files = st.file_uploader("Sube tus archivos PDF", accept_multiple_files=True, type="pdf")

    if uploaded_files:
        process_pdfs(uploaded_files)

if __name__ == "__main__":
    main()
