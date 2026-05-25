import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime

def calcular_impuestos_equipaje(valor_total_usd, via_entrada, tipo_de_cambio, tasa_global_pct, num_pasajeros, es_periodo_paisano=False):
    if via_entrada == "Aérea / Marítima":
        franquicia_individual = 500.0
    else:
        franquicia_individual = 500.0 if es_periodo_paisano else 300.0
    
    franquicia_total_usd = franquicia_individual * num_pasajeros
    
    if valor_total_usd <= franquicia_total_usd:
        return {
            "Estatus": "Libre de impuestos",
            "Franquicia_Individual": franquicia_individual,
            "Franquicia_Total": franquicia_total_usd,
            "Excedente_USD": 0.0,
            "Impuesto_MXN": 0.0,
            "Mensaje": "✅ ¡Excelente! La mercancía entra dentro de la franquicia acumulada de tu grupo."
        }
    
    excedente_usd = valor_total_usd - franquicia_total_usd
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
        "Franquicia_Individual": franquicia_individual,
        "Franquicia_Total": franquicia_total_usd,
        "Excedente_USD": excedente_usd,
        "Excedente_MXN": excedente_mxn,
        "Tasa": f"{tasa_global_pct}%",
        "Impuesto_MXN": impuesto_mxn,
        "Mensaje": mensaje
    }

# --- CONFIGURACIÓN DE LA INTERFAZ MÓVIL ---
st.set_page_config(page_title="Aduana Pro", page_icon="🧳", layout="centered")

# TRUCO CSS: Oculta todo al imprimir excepto el contenedor con id="seccion-ticket"
st.markdown("""
    <style>
    @media print {
        html, body, div[data-testid="stAppViewContainer"], div[data-testid="stHeader"] {
            background-color: white !important;
        }
        /* Oculta absolutamente todo de manera visual */
        div[data-testid="stAppViewContainer"] * {
            visibility: hidden;
        }
        /* Hace visible únicamente el ticket y lo que esté adentro de él */
        div#seccion-ticket, div#seccion-ticket * {
            visibility: visible;
        }
        /* Posiciona el ticket en la esquina superior izquierda de la hoja limpia */
        div#seccion-ticket {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            max-width: 100% !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧳 Aduana Pro")
st.write("Calculadora de equipaje familiar con franquicia acumulada.")

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

# --- 3. DATOS DEL VIAJE Y PASAJEROS ---
st.subheader("📋 Datos del Viajero / Grupo")
nombre_usuario = st.text_input("Nombre del Pasajero / Familia", value="", placeholder="Ej. Familia Pérez")
num_pasajeros = st.number_input("Número de pasajeros viajando juntos", min_value=1, max_value=20, value=1, step=1)
via = st.selectbox("¿Cómo ingresas al país?", ["Terrestre", "Aérea / Marítima"])
paisano = st.toggle("¿Aplica Programa Paisano?") if via == "Terrestre" else False

st.divider()

# --- 4. CONTROL DE EJECUCIÓN ---
if "mostrar_resultados" not in st.session_state:
    st.session_state.mostrar_resultados = False

if st.button("Calcular Impuestos Totales", type="primary", use_container_width=True):
    st.session_state.mostrar_resultados = True

# --- 5. RESULTADOS E IMPRESIÓN ---
if st.session_state.mostrar_resultados:
    res = calcular_impuestos_equipaje(valor_total_usd, via, tipo_cambio, tasa_impuesto, num_pasajeros, paisano)
    
    st.subheader("📋 Resultado del Cálculo")
    
    # Generar filas dinámicas de artículos para la vista de ticket HTML
    html_filas_articulos = ""
    for _, fila in df_articulos.iterrows():
        html_filas_articulos += f"<tr><td style='padding: 4px 0;'>• {fila['Artículo']}</td><td style='text-align: right; padding: 4px 0;'>${fila['Precio (USD)']:,.2f} USD</td></tr>"

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    nombre_ticket = nombre_usuario.strip() if nombre_usuario.strip() else "No especificado"

    # --- TICKET VISUAL EN PANTALLA (Y EXCLUSIVO DE IMPRESIÓN) ---
    ticket_html = f"""
    <div id="seccion-ticket" style="
        font-family: Arial, sans-serif; 
        max-width: 450px; 
        margin: 15px auto; 
        padding: 20px; 
        border: 1px dashed #bbb; 
        border-radius: 8px; 
        background-color: #ffffff; 
        color: #000000;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);">
        
        <h3 style="text-align: center; margin: 0 0 5px 0; font-size: 18px; color: #000;">TICKET DE ADUANA PRO</h3>
        <p style="text-align: center; margin: 0 0 15px 0; font-size: 11px; color: #666;">{fecha_actual}</p>
        
        <div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
        
        <p style="margin: 5px 0; font-size: 13px;"><b>Pasajero/Familia:</b> {nombre_ticket}</p>
        <p style="margin: 5px 0; font-size: 13px;"><b>Pasajeros en Grupo:</b> {num_pasajeros}</p>
        <p style="margin: 5px 0; font-size: 13px;"><b>Vía de Entrada:</b> {via}</p>
        <p style="margin: 5px 0; font-size: 13px;"><b>Tipo de Cambio:</b> ${tipo_cambio:.2f} MXN</p>
        
        <div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
        <h4 style="margin: 0 0 5px 0; font-size: 13px;">DESGLOSE DE MERCANCÍA:</h4>
        
        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
            {html_filas_articulos}
        </table>
        
        <div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
        
        <table style="width: 100%; font-size: 13px; line-height: 1.6;">
            <tr><td>Suma Total Artículos:</td><td style="text-align: right;">${valor_total_usd:,.2f} USD</td></tr>
            <tr><td>Franquicia Individual:</td><td style="text-align: right;">${res['Franquicia_Individual']:.2f} USD</td></tr>
            <tr><td><b>Franquicia Total ({num_pasajeros} pax):</b></td><td style="text-align: right;"><b>-${res['Franquicia_Total']:.2f} USD</b></td></tr>
            <tr><td>Excedente Gravable:</td><td style="text-align: right;">${res['Excedente_USD']:,.2f} USD</td></tr>
            <tr><td>Tasa de Impuesto:</td><td style="text-align: right;">{res['Tasa']}</td></tr>
            <tr style="font-size: 16px; font-weight: bold; border-top: 1px solid #000;">
                <td style="padding-top: 8px; color: #000;">TOTAL A PAGAR:</td>
                <td style="text-align: right; padding-top: 8px; color: #000;">${res['Impuesto_MXN']:,.2f} MXN</td>
            </tr>
        </table>
        
        <div style="border-top: 1px dashed #000; margin: 15px 0 5px 0;"></div>
        <p style="font-size: 11px; text-align: center; margin: 0; font-style: italic; color: #444;">{res['Mensaje']}</p>
    </div>
    """
    
    # Mostrar el ticket directamente renderizado en la interfaz de Streamlit
    st.markdown(ticket_html, unsafe_allow_html=True)
    
    # Generar el bloque de texto plano para la descarga alternativa (.txt)
    texto_ticket_txt = (
        f"========================================\n"
        f"          TICKET DE ADUANA PRO          \n"
        f"========================================\n"
        f"Fecha: {fecha_actual}\n"
        f"Pasajero/Familia: {nombre_ticket}\n"
        f"Total de Pasajeros: {num_pasajeros}\n"
        f"Vía de Entrada: {via}\n"
        f"Tipo de Cambio: ${tipo_cambio:.2f} MXN\n"
        f"----------------------------------------\n"
        f"ARTÍCULOS DETALLADOS:\n"
    )
    for _, fila in df_articulos.iterrows():
        texto_ticket_txt += f"- {fila['Artículo']}: ${fila['Precio (USD)']:,.2f} USD\n"
        
    texto_ticket_txt += (
        f"----------------------------------------\n"
        f"Suma Total Artículos: ${valor_total_usd:,.2f} USD\n"
        f"Franquicia Total ({num_pasajeros} pax): ${res['Franquicia_Total']:.2f} USD\n"
        f"Excedente Gravable:    ${res['Excedente_USD']:,.2f} USD\n"
        f"Tasa Aplicada:         {res['Tasa']}\n"
        f"----------------------------------------\n"
        f"TOTAL A PAGAR:         ${res['Impuesto_MXN']:,.2f} MXN\n"
        f"========================================\n"
        f"Nota: {res['Mensaje']}\n"
    )
    
    st.subheader("🖨️ Exportar o Imprimir")
    col1, col2 = st.columns(2)
    
    with col1:
        nombre_archivo = nombre_usuario.replace(" ", "_") if nombre_usuario.strip() else "Pasajero"
        st.download_button(
            label="📥 Descargar Ticket (.txt)",
            data=texto_ticket_txt,
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
                🖨️ Imprimir Ticket / PDF
            </button>
        """, height=45)
