import streamlit as st
import pandas as pd

def calcular_impuestos_equipaje(valor_total_usd, via_entrada, tipo_de_cambio, tasa_global_pct, es_periodo_paisano=False):
    # 1. Determinar la Franquicia según la vía
    if via_entrada == "Aérea / Marítima":
        franquicia_usd = 500.0
    else: # Terrestre
        franquicia_usd = 500.0 if es_periodo_paisano else 300.0
    
    # 2. Validar si está libre de impuestos
    if valor_total_usd <= franquicia_usd:
        return {
            "Estatus": "Libre de impuestos",
            "Franquicia": franquicia_usd,
            "Excedente_USD": 0.0,
            "Impuesto_MXN": 0.0,
            "Mensaje": "✅ Tu mercancía entra dentro de la franquicia permitida."
        }
    
    # 3. Calcular excedente y validar límite legal
    excedente_usd = valor_total_usd - franquicia_usd
    limite_maximo = 3000.0
    alerta_limite = excedente_usd > limite_maximo
    
    # 4. Calcular Impuesto usando la tasa modificada por el usuario
    tasa_global = tasa_global_pct / 100.0
    impuesto_usd = excedente_usd * tasa_global
    
    # Conversiones a Moneda Nacional
    impuesto_mxn = impuesto_usd * tipo_de_cambio
    excedente_mxn = excedente_usd * tipo_de_cambio
    
    mensaje = "👍 Cálculo listo para pagar en la caja de la aduana."
    if alerta_limite:
        mensaje = "⚠️ ¡Atención! El excedente supera los $3,000 USD. La aduana podría exigirte un Agente Aduanal."

    return {
        "Estatus": "Requiere Pago" if not alerta_limite else "Excede Límite",
        "Franquicia": franquicia_usd,
        "Excedente_USD": excedente_usd,
        "Excedente_MXN": excedente_mxn,
        "Tasa": f"{tasa_global_pct}%",
        "Impuesto_MXN": impuesto_mxn,
        "Mensaje": mensaje
    }

# --- CONFIGURACIÓN DE LA INTERFAZ MÓVIL ---
st.set_page_config(page_title="Aduana Pro", page_icon="🧳", layout="centered")

st.title("🧳 Aduana Pro")
st.write("Calculadora personal de equipaje con desglose de artículos.")

# --- 1. CONFIGURACIÓN AVANZADA (MODIFICAR IMPUESTO GLOBAL Y TC) ---
with st.expander("⚙️ Configuración de Tasas e Impuestos", expanded=False):
    tasa_impuesto = st.number_input("Tasa Global de Impuesto (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
    tipo_cambio = st.number_input("Tipo de cambio (MXN por USD)", min_value=1.0, step=0.05, value=18.50)

st.divider()

# --- 2. CALCULADORA INTERACTIVA DE ARTÍCULOS ---
st.subheader("🔢 Calculadora de Artículos")
st.write("Añade las filas que necesites directamente desde la tabla:")

# Inicializar una fila de ejemplo si la app arranca de cero
if "lista_articulos" not in st.session_state:
    st.session_state.lista_articulos = pd.DataFrame(
        [
            {"Artículo": "Ejemplo: Tenis / Ropa", "Precio (USD)": 120.0},
        ]
    )

# El componente data_editor ya corregido sin el parámetro 'placeholder'
df_articulos = st.data_editor(
    st.session_state.lista_articulos,
    num_rows="dynamic",  
    use_container_width=True,
    column_config={
        "Artículo": st.column_config.TextColumn("Descripción", required=True),
        "Precio (USD)": st.column_config.NumberColumn("Valor ($ USD)", min_value=0.0, format="$%d", required=True)
    }
)
# Guardar el estado actual
st.session_state.lista_articulos = df_articulos

# Sumar automáticamente la columna de precios
valor_total_usd = df_articulos["Precio (USD)"].sum()

# Mostrar el total acumulado de la calculadora
st.metric(label="Valor Total de tu Compra", value=f"${valor_total_usd:,.2f} USD")

st.divider()

# --- 3. DATOS DEL VIAJE ---
via = st.selectbox("¿Cómo ingresas al país?", ["Terrestre", "Aérea / Marítima"])

paisano = False
if via == "Terrestre":
    paisano = st.toggle("¿Aplica Programa Paisano?")

st.divider()

# --- 4. EJECUCIÓN Y RESULTADOS ---
if st.button("Calcular Impuestos Totales", type="primary", use_container_width=True):
    res = calcular_impuestos_equipaje(valor_total_usd, via, tipo_cambio, tasa_impuesto, paisano)
    
    if res["Estatus"] == "Libre de impuestos":
        st.success(res["Mensaje"])
        st.metric(label="Impuesto a Pagar", value="$0.00 MXN")
    else:
        if res["Estatus"] == "Excede Límite":
            st.warning(res["Mensaje"])
        else:
            st.info(res["Mensaje"])
            
        # Bloque de impacto visual para el pago total
        st.metric(label="TOTAL A PAGAR EN ADUANA", value=f"${res['Impuesto_MXN']:,.2f} MXN")
        
        # Desglose matemático
        with st.expander("Ver desglose matemático"):
            st.write(f"**Suma de tus artículos:** ${valor_total_usd:,.2f} USD")
            st.write(f"**Franquicia restada:** ${res['Franquicia']} USD")
            st.write(f"**Excedente cobrado:** ${res['Excedente_USD']:,.2f} USD")
            st.write(f"**Tasa impositiva aplicada:** {res['Tasa']}")
            st.write(f"**Equivalente en pesos del excedente:** ${res['Excedente_MXN']:,.2f} MXN")
