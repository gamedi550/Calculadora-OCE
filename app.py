import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse
import requests

# ====================================================
# 0. CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO)
# ====================================================
st.set_page_config(page_title="Control Aduanal México", page_icon="🧳", layout="centered")

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

# --- FUNCIÓN LÓGICA DE CÁLCULO ---
def calcular_impuestos_equipaje(valor_total_usd, df_extras, tipo_de_cambio, tasa_global_pct, num_pasajeros):
    franquicia_individual = 500.0
    franquicia_total_usd = franquicia_individual * num_pasajeros
    
    excedente_usd = max(0.0, valor_total_usd - franquicia_total_usd)
    limite_maximo = 3000.0
    alerta_limite = excedente_usd > limite_maximo
    
    tasa_global = tasa_global_pct / 100.0
    impuesto_general_usd = excedente_usd * tasa_global
    impuesto_general_mxn = impuesto_general_usd * tipo_de_cambio
    excedente_mxn = excedente_usd * tipo_de_cambio
    
    impuesto_extras_mxn = 0.0
    valor_extras_usd = 0.0
    
    if df_extras is not None and not df_extras.empty:
        valor_extras_usd = df_extras["Precio (USD)"].sum()
        df_calc_extras = df_extras.copy()
        df_calc_extras["Impuesto_USD"] = df_calc_extras["Precio (USD)"] * (df_calc_extras["Tasa (%)"] / 100.0)
        impuesto_extras_mxn = df_calc_extras["Impuesto_USD"].sum() * tipo_de_cambio

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

# ====================================================
# --- GUÍA DE CONSULTA ADUANAL (BARRA LATERAL) ---
# ====================================================
with st.sidebar:
    st.header("📖 Guía Oficial del Viajero")
    st.write("
