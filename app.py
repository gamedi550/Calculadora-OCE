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

# --- FUNCIÓN LOGICA DE CÁLCULO ---
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

# ====================================================
# --- GUÍA DE CONSULTA ADUANAL (BARRA LATERAL) ---
# ====================================================
with st.sidebar:
    st.header("📖 Guía Oficial del Viajero")
    st.write("Consulta qué artículos se consideran **Equipaje Personal** (entran gratis) y cómo funcionan las **Franquicias**.")
    
    with st.expander("🧳 Equipaje Personal (Libre de Impuesto)", expanded=True):
        st.markdown("""
        Los siguientes artículos **NO se deben sumar a la calculadora**:
        * **Ropa, calzado y productos de aseo** personal.
        * **2 teléfonos celulares** o de radiolocalización.
        * **1 Laptop** y **1 Tablet**.
        * **2 cámaras** fotográficas o de videograbación.
        * **1 consola de videojuegos** y hasta **5 videojuegos**.
        * **Libros, revistas** y documentos impresos.
        * **Medicamentos** de uso personal (con receta si aplica).
        * **Maletas, baúles** o bolsas necesarios para el traslado.
        * **Otros:** 2 instrumentos musicales portátiles, equipo deportivo personal, artículos de bebé (carriola, cuna) y herramientas manuales básicas.
        * **Mascotas:** Hasta 3 perros o gatos con su documentación sanitaria.
        """)
        
    with st.expander("💵 Reglas de Franquicia", expanded=False):
        st.markdown("""
        La franquicia aplica para mercancías nuevas adicionales a tu equipaje personal:
        * **Franquicia General:** $500 USD por persona todo el año, sin importar la vía de ingreso (Aérea, Marítima o Terrestre).
        
        👨‍👩‍👧‍👦 **Acumulación Familiar:** Las franquicias son **acumulables** si viajan juntos en el mismo medio de transporte.
        """)
        
    with st.expander("⚠️ Límites de Alcohol, Tabaco y Restricciones", expanded=False):
        st.markdown("""
        Los pasajeros **mayores de 18 años** pueden ingresar libre de impuestos únicamente:
        * **Alcohol (licores):** Hasta 3 litros.
        * **Vino:** Hasta 6 litros.
        * **Tabaco (elegir solo una opción):**
          * **20 cajetillas** de cigarros.
          * **25 puros**.
          * **200 gramos** de tabaco.
        
        ⛔ **IMPORTANTE:** Si excedes estas cantidades, el excedente paga impuestos comerciales fijos y directos en la sección de Extras.
        """)
        
    st.divider()
    st.markdown("### 🔗 Enlaces Oficiales")
    st.markdown("[📜 Portal de Aduanas - SAT](https://www.sat.gob.mx/)")

# ==========================================
# --- CONTENIDO PRINCIPAL DE LA APP ---
# ==========================================

st.subheader("📍 Ubicación de Ingreso")
ciudad_seleccionada = st.selectbox(
    "Selecciona la aduana donde te encuentras:", 
    list(CIUDADES_ADUANA.keys()),
    index=0
)

st.title(f"🧳 Aduana {ciudad_seleccionada}")
st.write("Calculadora de equipaje familiar con franquicia acumulada y sección especial de licores/tabacos.")

# --- 1. CONFIGURACIÓN AVANZADA ---
with st.expander("⚙️ Configuración de Tasas e Impuestos", expanded=False):
    tasa_impuesto = st.number_input("Tasa Global de Impuesto General (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
    tipo_cambio_del_dia = obtener_tipo_cambio_real()
    tipo_cambio = st.number_input("Tipo de cambio (MXN por USD)", min_value=1.0, step=0.05, value=tipo_cambio_del_dia)
    st.caption(f"💡 Tipo de cambio oficial sincronizado hoy: **${tipo_cambio_del_dia} MXN**")

st.divider()

# --- 2. CALCULADORA INTERACTIVA DE ARTÍCULOS GENERALES ---
st.subheader("🔢 1. Artículos Generales (Afectan Franquicia)")

if "lista_articulos" not in st.session_state:
    st.session_state.lista_articulos = pd.DataFrame([
        {"Artículo": "Ropa y Calzado excedente", "Precio (USD)": 0.0},
        {"Artículo": "Electrodomésticos", "Precio (USD)": 0.0},
        {"Artículo": "Muebles y Hogar", "Precio (USD)": 0.0},
        {"Artículo": "Herramientas", "Precio (USD)": 0.0},
        {"Artículo": "Productos alimenticios", "Precio (USD)": 0.0},
        {"Artículo": "Aparatos electrónicos", "Precio (USD)": 0.0}
    ], index=[1, 2, 3, 4, 5, 6])

df_articulos_editado = st.data_editor(
    st.session_state.lista_articulos,
    num_rows="fixed",  
    use_container_width=True,
    key="editor_articulos",
    disabled=["Artículo"], 
    column_config={
        "Artículo": st.column_config.TextColumn("Descripción General"),
        "Precio (USD)": st.column_config.NumberColumn("Valor ($ USD)", min_value=0.0, format="$%.2f", required=True)
    }
)
valor_total_usd = df_articulos_editado["Precio (USD)"].sum()

# --- 3. CALCULADORA INTERACTIVA DE EXTRAS (TASAS INDIVIDUALES) ---
st.subheader("🍾 2. Excedentes de Alcohol, Vino y Tabaco (Tasa Fija Directa)")
st.caption("Nota: Estos artículos pagan impuesto directo desde el primer dólar excedente según la normatividad fiscal.")

if "lista_extras" not in st.session_state:
    st.session_state.lista_extras = pd.DataFrame([
        {"Categoría": "Bebidas Alcohólicas / Licores (>20°)", "Precio (USD)": 0.0, "Tasa (%)": 90.0},
        {"Categoría": "Vino / Cerveza (<14°)", "Precio (USD)": 0.0, "Tasa (%)": 75.0},
        {"Categoría": "Tabacos / Cigarros / Puros", "Precio (USD)": 0.0, "Tasa (%)": 350.0}
    ], index=[1, 2, 3])

df_extras_editado = st.data_editor(
    st.session_
