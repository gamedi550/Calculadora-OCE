import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime

def calcular_impuestos_equipaje(valor_total_usd, via_entrada, tipo_de_cambio, tasa_global_pct, es_periodo_paisano=False):
    if via_entrada == "Aérea / Marítima":
        franquicia_usd = 500.0
    else:
        franquicia_usd = 500.0 if es_periodo_paisano else 300.0
    
    if valor_total_usd <= franquicia_usd:
        return {
            "Estatus": "Libre de impuestos",
            "Franquicia": franquicia_usd,
            "Excedente_USD": 0.0,
            "Impuesto_MXN": 0.0,
            "Mensaje": "✅ Tu mercancía entra dentro de la franquicia permitida."
        }
    
    excedente_usd = valor_total_usd - franquicia_usd
    limite_maximo = 3000.0
    alerta_limite = excedente_usd > limite_maximo
    
    tasa_global = tasa_global_pct / 100.0
    impuesto_usd = excedente_usd * tasa_global
    
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

# --- 1. CONFIGURACIÓN AVANZADA ---
with st.expander("⚙️ Configuración de Tasas e Impuestos", expanded=False):
    tasa_impuesto = st.number_input("Tasa Global de Impuesto (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
    tipo_cambio = st.number_input("Tipo de cambio (MXN por USD)", min_value=1.0, step=0.05, value=18.50)

st.divider()

# --- 2. CALCULADORA INTERACTIVA DE ARTÍCULOS ---
st.subheader("🔢 Calculadora de Artículos")

if "lista_articulos" not in st.session_state:
    st.session_state.lista_articulos = pd.DataFrame([{"Artículo": "Ejemplo: Tenis / Ropa", "Precio (USD)": 120.0}])

df_articulos = st.data_editor(
    st.session_state.lista_articulos,
    num_rows="dynamic",  
    use_container_width=True,
    column_config={
        "Artículo": st.column_config.TextColumn("Descripción", required=True),
        "Precio (USD)": st.column_config.NumberColumn("Valor ($ USD)", min_value=0.0, format="$%d", required=True)
    }
)
st.session_state.lista_articulos = df_articulos
valor_total_usd = df_articulos["Precio (USD)"].sum()

st.metric(label="Valor Total de tu Compra", value=f"${valor_total_usd:,.2f} USD")

st.divider()

# --- 3. DATOS DEL VIAJE ---
st.subheader("📋 Datos del Viajero")
nombre_usuario = st.text_input("Nombre del Pasajero", value="", placeholder="Ej. Juan Pérez")
via = st.selectbox("¿Cómo ingresas al país?", ["Terrestre", "Aérea / Marítima"])
paisano = st.toggle("¿Aplica Programa Paisano?") if via == "Terrestre" else False

st.divider()

# --- 4. CONTROL DE EJECUCIÓN (SESSION STATE) ---
if "mostrar_resultados" not in st.session_state:
    st.session_state.mostrar_resultados = False

if st.button("Calcular Impuestos Totales", type="primary", use_container_width=True):
    st.session_state.mostrar_resultados = True

# --- 5. RESULTADOS E IMPRESIÓN ---
if st.session_state.mostrar_resultados:
    res = calcular_impuestos_equipaje(valor_total_usd, via, tipo_cambio, tasa_impuesto, paisano)
    
    if nombre_usuario.strip():
        st.subheader(f"👤 Pasajero: {nombre_usuario}")

    if res["Estatus"] == "Libre de impuestos":
        st.success(res["Mensaje"])
        st.metric(label="Impuesto a Pagar", value="$0.00 MXN")
    else:
        if res["Estatus"] == "Excede Límite":
            st.warning(res["Mensaje"])
        else:
            st.info(res["Mensaje"])
            
        st.metric(label="TOTAL A PAGAR EN ADUANA", value=f"${res['Impuesto_MXN']:,.2f} MXN")
        
        with st.expander("Ver desglose matemático en pantalla", expanded=True):
            st.write(f"**Suma de tus artículos:** ${valor_total_usd:,.2f} USD")
            st.write(f"**Franquicia restada:** ${res['Franquicia']} USD")
            st.write(f"**Excedente cobrado:** ${res['Excedente_USD']:,.2f} USD")
            st.write(f"**Tasa impositiva aplicada:** {res['Tasa']}")
            st.write(f"**Equivalente en pesos:** ${res['Excedente_MXN']:,.2f} MXN")

        st.subheader("🖨️ Exportar o Imprimir")
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_ticket = nombre_usuario.strip() if nombre_usuario.strip() else "No especificado"
        
        texto_ticket = (
            f"========================================\n"
            f"          TICKET DE ADUANA PRO          \n"
            f"========================================\n"
            f"Fecha: {fecha_actual}\n"
            f"Pasajero: {nombre_ticket}\n"
            f"Vía de Entrada: {via}\n"
            f"Tipo de Cambio: ${tipo_cambio:.2f} MXN\n"
            f"----------------------------------------\n"
            f"ARTÍCULOS DETALLADOS:\n"
        )
        for _, fila in df_articulos.iterrows():
            texto_ticket += f"- {fila['Artículo']}: ${fila['Precio (USD)']:,.2f} USD\n"
            
        texto_ticket += (
            f"----------------------------------------\n"
            f"Suma Total:         ${valor_total_usd:,.2f} USD\n"
            f"Franquicia Aplicada: ${res['Franquicia']:.2f} USD\n"
            f"Excedente Gravable:  ${res['Excedente_USD']:,.2f} USD\n"
            f"Tasa Aplicada:       {res['Tasa']}\n"
            f"----------------------------------------\n"
            f"TOTAL A PAGAR:       ${res['Impuesto_MXN']:,.2f} MXN\n"
            f"========================================\n"
            f"Nota: {res['Mensaje']}\n"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            nombre_archivo = nombre_usuario.replace(" ", "_") if nombre_usuario.strip() else "Pasajero"
            st.download_button(
                label="📥 Descargar Ticket (.txt)",
                data=texto_ticket,
                file_name=f"Desglose_{nombre_archivo}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col2:
            components.html("""
                <script>
                    function imprimirPantalla() {
                        window.parent.print();
                    }
                </script>
                <button onclick="imprimirPantalla()" style="
                    width: 100%; 
                    height: 38px; 
                    background-color: #4CAF50; 
                    color: white; 
                    border: none; 
                    border-radius: 4px; 
                    font-weight: bold; 
                    font-size: 14px;
                    cursor: pointer;">
                    🖨️ Imprimir / PDF
                </button>
            """, height=45)
