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
        "frutos secos": ["almendra", "anacardo", "nuez", "pasas sultanas", "cacahuete"],
        "snacks": ["patatas", "chocolate", "chicles", "cereales rellenos", "patatas lisas", "patatas chili lima", "nachos", "varitas frambuesa"],
        "panadería": ["panecillo", "barra de pan", "barra rústica", "croqueta", "tortillas mexicanas", "chapata cristal", "pan m. 55% centeno", "pan viena redondo"],
        "lácteos": ["leche", "yogur", "mantequilla", "queso", "cremoso", "stracciatella", "griego", "nata"],
        "bebidas y caldos": ["caldo de pollo", "salsa de soja", "agua mineral", "soja calcio brick"],
        "verduras y legumbres": ["garbanzo", "maíz", "ensalada", "cebolla", "pimiento", "champiñón", "calabacín", "zanahoria", "ajo", "brotes tiernos"],
        "carne": ["jamoncitos", "burger", "chuleta", "lomo", "cuarto trasero", "pavo", "albóndigas", "longaniza", "gallina", "tacos", "paleta", "loncha"],
        "condimentos y salsas": ["ketchup", "azúcar", "harina", "sabor", "para freir"],
        "despensa": ["arroz", "macarrón", "mezcla de semillas", "harina", "pasta", "avena crunchy", "arroz largo"],
        "conservas": ["atún", "tomate triturado", "aceitunas", "pepinillo"],
        "platos preparados": ["hummus", "preparado andaluz", "ensaladilla rusa"],
        "otros": ["huevos frescos", "estropajo", "toall.bebe", "dermo", "gamuza atrapapolvo", "rollo hogar doble", "lavavajillas", "colg. triple", "gel crema"]
    }

    for category, keywords in categories.items():
        if any(keyword in item for keyword in keywords):
            return category
    return "otros"

def extract_location(text):
    """Función para extraer la ubicación de la tienda del ticket."""
    location_match = re.search(r"MERCADONA,\s+S\.A\.\s+[^\n]*\n(.*?)(?=TELÉFONO:)", text, re.DOTALL)
    return location_match.group(1).strip() if location_match else "Ubicación no encontrada"

def process_pdfs(uploaded_files):
    data = []

    # Asegurar que el directorio de datos exista
    data_path = "data"
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
                print("Texto extraído del PDF:")
                print(text)

                # Extraer ubicación
                location = extract_location(text)

                # Extraer fecha e identificador del ticket
                date_match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", text)
                fecha = date_match.group(0) if date_match else "Fecha no encontrada"

                ticket_match = re.search(r"FACTURA SIMPLIFICADA:\s+([0-9\-]+)", text)
                identificativo = ticket_match.group(1) if ticket_match else "Identificativo no encontrado"

                # Extraer ítems y precios utilizando un patrón más flexible
                # Patrón mejorado para capturar ítems con múltiples palabras y precios
                item_pattern = r"([A-Z0-9\s/]+)\s+(\d+,\d{2})"

                # Filtrar líneas no relacionadas con productos
                patron_no_producto = re.compile(r"(TARJETA BANCARIA|TOTAL|SUBTOTAL|CREDITO)", re.IGNORECASE)
                
                # Filtrar líneas no relacionadas con productos
                filtered_lines = [line for line in text.splitlines() if not patron_no_producto.search(line)]

                # Extraer ítems de las líneas filtradas
                items = re.findall(item_pattern, '\n'.join(filtered_lines))

                for item, precio in items:
                    item = item.strip()
                    precio = round(float(precio.replace(",", ".")), 2)
                    categoria = categorize_item(item)
                    data.append([fecha, identificativo, location, item, categoria, precio])
            else:
                print(f"No se pudo extraer texto del archivo: {uploaded_file.name}")

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

def get_global_data():
    """Función para obtener y procesar los datos globales desde Google Sheets."""
    try:
        # Conectar y leer datos existentes de Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1")  # Cambia "Sheet1" por el nombre de tu hoja

        if existing_data.empty:
            st.warning("La hoja de cálculo está vacía.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0, 0

        # Asegúrate de que las columnas necesarias están presentes
        required_columns = ['fecha', 'precio', 'categoría', 'ubicación', 'item', 'identificativo de ticket']
        for column in required_columns:
            if column not in existing_data.columns:
                st.error(f"Columna '{column}' no encontrada en los datos.")
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0, 0

        # Convertir la columna 'fecha' al formato de fecha
        existing_data['fecha'] = pd.to_datetime(existing_data['fecha'], errors='coerce')

        # Calcular el gasto total por mes
        existing_data['mes'] = existing_data['fecha'].dt.to_period('M').astype(str)
        gasto_total_por_mes = existing_data.groupby('mes')['precio'].sum().reset_index()
        gasto_total_por_mes.columns = ['mes', 'precio']

        # Contar el número de items vendidos por categoría
        items_por_categoria = existing_data['categoría'].value_counts().reset_index()
        items_por_categoria.columns = ['categoría', 'cantidad']

        # Contar el número de ventas por ubicación
        ventas_por_ubicacion = existing_data['ubicación'].value_counts().reset_index()
        ventas_por_ubicacion.columns = ['ubicación', 'cantidad']

        # Obtener el ítem más vendido
        item_mas_vendido = existing_data.groupby('item')['precio'].sum().reset_index().sort_values(by='precio', ascending=False).head(1)

        # Calcular valor del ticket medio y el ticket más alto
        tickets = existing_data.groupby('identificativo de ticket')['precio'].sum().reset_index()
        ticket_medio = tickets['precio'].mean()
        ticket_mas_alto = tickets['precio'].max()

        return gasto_total_por_mes, items_por_categoria, ventas_por_ubicacion, item_mas_vendido, ticket_medio, ticket_mas_alto

    except Exception as e:
        st.error(f"Error al obtener o procesar los datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0, 0


if __name__ == "__main__":
    main()
