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

# --- 4. CONTROL DE EJECUCIÓN ---
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
        
        # 1. Generar filas de la tabla en HTML para el diseño del ticket
        html_filas_articulos = ""
        for _, fila in df_articulos.iterrows():
            html_filas_articulos += f"<tr><td style='padding: 5px 0;'>{fila['Artículo']}</td><td style='text-align: right; padding: 5px 0;'>${fila['Precio (USD)']:,.2f} USD</td></tr>"
            
        # 2. Plantilla HTML Estructurada para Diseñar el Recibo impreso en Noto Sans
        ticket_html_diseño = f"""
        <div style='width: 100%; max-width: 360px; margin: 0 auto; padding: 10px; color: #000;'>
            <h2 style='text-align: center; margin-bottom: 3px; font-size: 20px;'>TICKET DE ADUANA PRO</h2>
            <p style='text-align: center; margin-top: 0; font-size: 11px; color: #555;'>{fecha_actual}</p>
            <div style='border-top: 1px dashed #000; margin: 10px 0;'></div>
            <p style='margin: 4px 0; font-size: 13px;'><b>Pasajero:</b> {nombre_ticket}</p>
            <p style='margin: 4px 0; font-size: 13px;'><b>Vía de Entrada:</b> {via}</p>
            <p style='margin: 4px 0; font-size: 13px;'><b>Tipo de Cambio:</b> ${tipo_cambio:.2f} MXN</p>
            <div style='border-top: 1px dashed #000; margin: 10px 0;'></div>
            <table style='width: 100%; font-size: 13px; border-collapse: collapse;'>
                <thead>
                    <tr style='border-bottom: 1px solid #000;'><th style='text-align: left; padding-bottom: 5px;'>Descripción</th><th style='text-align: right; padding-bottom: 5px;'>Valor</th></tr>
                </thead>
                <tbody>
                    {html_filas_articulos}
                </tbody>
            </table>
            <div style='border-top: 1px dashed #000; margin: 10px 0;'></div>
            <table style='width: 100%; font-size: 13px;'>
                <tr><td style='padding: 2px 0;'>Suma Total:</td><td style='text-align: right;'>${valor_total_usd:,.2f} USD</td></tr>
                <tr><td style='padding: 2px 0;'>Franquicia:</td><td style='text-align: right;'>-${res['Franquicia']:.2f} USD</td></tr>
                <tr><td style='padding: 2px 0;'>Excedente:</td><td style='text-align: right;'>${res['Excedente_USD']:,.2f} USD</td></tr>
                <tr><td style='padding: 2px 0;'>Tasa Aplicada:</td><td style='text-align: right;'>{res['Tasa']}</td></tr>
                <tr style='font-weight: bold; font-size: 15px;'><td style='padding-top: 8px;'>TOTAL A PAGAR:</td><td style='text-align: right; padding-top: 8px;'>${res['Impuesto_MXN']:,.2f} MXN</td></tr>
            </table>
            <div style='border-top: 1px dashed #000; margin: 12px 0;'></div>
            <p style='font-size: 11px; text-align: center; font-style: italic;'>{res['Mensaje']}</p>
        </div>
        """

        col1, col2 = st.columns(2)
        
        with col1:
            # Mantener la descarga de respaldo en texto plano
            texto_plano_backup = f"Pasajero: {nombre_ticket}\nTotal: ${res['Impuesto_MXN']:,.2f} MXN"
            nombre_archivo = nombre_usuario.replace(" ", "_") if nombre_usuario.strip() else "Pasajero"
            st.download_button(
                label="📥 Descargar Resumen (.txt)",
                data=texto_plano_backup,
                file_name=f"Resumen_{nombre_archivo}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col2:
            # Inyección de código JavaScript para abrir ventana limpia con Noto Sans e imprimir de forma inmediata
            js_print_script = f"""
            <script>
                function lanzarImpresion() {{
                    var win = window.open('', '_blank');
                    win.document.write('<html><head><title>Ticket de Aduana</title>');
                    win.document.write('<link rel="preconnect" href="https://fonts.googleapis.com">');
                    win.document.write('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>');
                    win.document.write('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&display=swap" rel="stylesheet">');
                    win.document.write('<style>body {{ font-family: "Noto Sans", sans-serif; margin: 10px; padding: 0; }} @media print {{ body {{ margin: 0; }} }}</style>');
                    win.document.write('</head><body>');
                    win.document.write(`{ticket_html_diseño}`);
                    win.document.write('<script>window.onload = function() {{ window.print(); setTimeout(function() {{ window.close(); }}, 100); }}</s' + 'cript>');
                    win.document.write('</body></html>');
                    win.document.close();
                }}
            </script>
            <button onclick="lanzarImpresion()" style="
                width: 100%; 
                height: 38px; 
                background-color: #4CAF50; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                font-weight: bold; 
                font-size: 14px;
                cursor: pointer;">
                🖨️ Imprimir Ticket (Noto Sans)
            </button>
            """
            components.html(js_print_script, height=45)
