import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime
import pytz
import urllib.parse
import base64
import requests

# --- FUNCIÓN PARA OBTENER EL TIPO DE CAMBIO AUTOMÁTICO ---
@st.cache_data(ttl="1d")
def obtener_tipo_cambio_real():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        tipo_cambio = float(data["rates"]["MXN"])
        return round(tipo_cambio, 2)
    except Exception as e:
        return 20.00

def calcular_impuestos_equipaje(valor_total_usd, df_extras, tipo_de_cambio, tasa_global_pct, num_pasajeros):
    # 1. CÁLCULO DE MERCANCÍA GENERAL (APLICA FRANQUICIA)
    franquicia_individual = 500.0
    franquicia_total_usd = franquicia_individual * num_pasajeros
    
    excedente_usd = max(0.0, valor_total_usd - franquicia_total_usd)
    limite_maximo = 3000.0
    alerta_limite = excedente_usd > limite_maximo
    
    tasa_global = tasa_global_pct / 100.0
    impuesto_general_usd = excedente_usd * tasa_global
    impuesto_general_mxn = impuesto_general_usd * tipo_de_cambio
    excedente_mxn = excedente_usd * tipo_de_cambio
    
    # 2. CÁLCULO DE EXTRAS (NO APLICA FRANQUICIA - TASA DIRECTA)
    impuesto_extras_mxn = 0.0
    valor_extras_usd = 0.0
    
    if df_extras is not None and not df_extras.empty:
        valor_extras_usd = df_extras["Precio (USD)"].sum()
        # Copia local para evitar alertas de asignación en Pandas
        df_calc_extras = df_extras.copy()
        df_calc_extras["Impuesto_USD"] = df_calc_extras["Precio (USD)"] * (df_calc_extras["Tasa (%)"] / 100.0)
        impuesto_extras_mxn = df_calc_extras["Impuesto_USD"].sum() * tipo_de_cambio

    # 3. CONSOLIDACIÓN TOTAL
    total_impuesto_mxn = impuesto_general_mxn + impuesto_extras_mxn
    
    estatus = "Libre de impuestos"
    if total_impuesto_mxn > 0:
        estatus = "Requiere Pago" if not alerta_limite else "Excede Límite"

    mensaje = "✅ ¡Excelente! La mercancía entra dentro de la franquicia acumulada de tu grupo." if total_impuesto_mxn == 0 else "👍 Cálculo listo para pagar en la caja de la aduana."
    if alerta_limite:
        mensaje = "⚠️ ¡Atención! El excedente general supera los $3,000 USD. La aduana podría exigirte un Agente Aduanal."

    return {
        "Estatus": estatus,
        "Franquicia_Individual": franquicia_individual,
        "Franquicia_Total": franquicia_total_usd,
        "Excedente_USD": excedente_usd,
        "Excedente_MXN": excedente_mxn,
        "Tasa_General": f"{tasa_global_pct}%",
        "Impuesto_General_MXN": impuesto_general_mxn,
        "Valor_Extras_USD": valor_extras_usd,
        "Impuesto_Extras_MXN": impuesto_extras_mxn,
        "Impuesto_Total_MXN": total_impuesto_mxn,
        "Mensaje": mensaje
    }

# --- CONFIGURACIÓN DE ZONAS HORARIAS POR CIUDAD ---
CIUDADES_ADUANA = {
    "Ciudad Juárez": "America/Ciudad_Juarez",
    "Tijuana": "America/Tijuana",
    "Nuevo Laredo": "America/Matamoros",
    "Ciudad de México (AICM)": "America/Mexico_City",
    "Cancún": "America/Cancun"
}

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Control Aduanal México", page_icon="🧳", layout="centered")

# ====================================================
# --- GUÍA DE CONSULTA ADUANAL (BARRA LATERAL) ---
# ====================================================
with st.sidebar:
    st.header("📖 Guía Oficial del Viajero")
    st.write("Consulta qué artículos se consideran **Equipaje Personal** (entran gratis) y cómo funcionan las **Franquicias** según la ANAM y el SAT.")
    
    with st.expander("🧳 Equipaje Personal (Libre de Impuesto)", expanded=True):
        st.markdown("""
        Los siguientes artículos **NO se deben sumar a la calculadora** porque se consideran de uso personal:
        * **Ropa, calzado y productos de aseo** personal en cantidades acordes a la duración del viaje.
        * **2 teléfonos celulares** o de radiolocalización.
        * **1 Laptop** (computadora portátil).
        * **1 Tablet** (agenda electrónica).
        * **2 cámaras** fotográficas o de videograbación y sus accesorios.
        * **1 consola de videojuegos** y hasta **5 videojuegos**.
        * **Libros, revistas** y documentos impresos de uso personal.
        * **Medicamentos** de uso personal (con receta médica si contienen sustancias psicotrópicos).
        * **Maletas, baúles** o bolsas necesarios para el traslado del equipaje.
        * **Otros:** 2 instrumentos musicales portátiles, equipo deportivo personal, artículos de bebé (carriola, cuna portátil) y herramientas manuales básicas.
        * **Mascotas:** Hasta 3 perros o gatos con su documentación sanitaria.
        """)
        
    with st.expander("💵 Reglas de Franquicia", expanded=False):
        st.markdown("""
        La franquicia aplica para mercancías nuevas adicionales a tu equipaje personal:
        * **Franquicia General:** $500 USD por persona de forma fija durante todo el año, sin importar la vía de ingreso (Aérea, Marítima o Terrestre).
        
        👨‍👩‍👧‍👦 **Acumulación Familiar:** Las franquicias de una misma familia son **acumulables** si viajan juntos, llegan al mismo tiempo y en el mismo medio de transporte.
        """)
        
    with st.expander("⚠️ Límites de Alcohol, Tabaco y Restricciones", expanded=False):
        st.markdown("""
        Los pasajeros **mayores de 18 años** pueden ingresar libre de impuestos únicamente las siguientes cantidades:
        * **Alcohol (licores y bebidas alcohólicas):** Hasta 3 litros.
        *
