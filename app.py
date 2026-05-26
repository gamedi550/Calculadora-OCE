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
            "Excedente_MXN": 0.0,
            "Tasa": f"{tasa_global_pct}%",
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
        * **Vía Aérea o Marítima:** $500 USD por persona todo el año.
        * **Vía Terrestre:** $300 USD por persona.
        * **Programa Héroes Paisanos:** Sube temporalmente a **$500 USD** por vía terrestre solo en los periodos vacacionales oficiales establecidos por el INM.
        
        👨‍👩‍👧‍👦 **Acumulación Familiar:** Las franquicias de una misma familia son **acumulables** si viajan juntos, llegan al mismo tiempo y en el mismo medio de transporte.
        """)
        
    with st.expander("⚠️ Lo que NO entra en la Franquicia", expanded=False):
        st.markdown("""
        Bajo ninguna circunstancia puedes incluir en tu franquicia los siguientes productos (deben pagar impuestos obligatorios):
        * Bebidas alcohólicas.
        * Tabacos labrados (cigarrillos o puros).
        * Combustible automotriz (gasolina o diésel) adicional al que se encuentra en el tanque de tu vehículo.
        """)
        
    st.divider()
    st.markdown("### 🔗 Enlaces Oficiales")
    st.markdown("[📜 Portal de Aduanas - SAT](https://www.sat.gob.mx/)")
    st.markdown("[🇲🇽 Instituto Nacional de Migración](https://www.gob.mx/inm)")

# ==========================================
# --- CONTENIDO PRINCIPAL DE LA APP ---
# ==========================================

# Selector de ciudad principal
st.subheader("📍 Ubicación de Ingreso")
ciudad_seleccionada = st.selectbox(
    "Selecciona la aduana donde te encuentras:", 
    list(CIUDADES_ADUANA.keys()),
    index=0
)

st.title(f"🧳 Aduana {ciudad_seleccionada}")
st.write("Calculadora de equipaje familiar con franquicia acumulada.")

# --- 1. CONFIGURACIÓN AVANZADA ---
with st.expander("⚙️ Configuración de Tasas e Impuestos", expanded=False):
    tasa_impuesto = st.number_input("Tasa Global de Impuesto (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
    
    tipo_cambio_del_dia = obtener_tipo_cambio_real()
    tipo_cambio = st.number_input("Tipo de cambio (MXN por USD)", min_value=1.0, step=0.05, value=tipo_cambio_del_dia)
    st.caption(f"💡 El tipo de cambio oficial se actualizó automáticamente hoy a: **${tipo_cambio_del_dia} MXN**")

st.divider()

# --- 2. CALCULADORA INTERACTIVA DE ARTÍCULOS ---
st.subheader("🔢 Calculadora de Artículos")

if "lista_articulos" not in st.session_state:
    st.session_state.lista_articulos = pd.DataFrame([
        {"Artículo": "Ropa", "Precio (USD)": 0.0},
        {"Artículo": "Electrodomésticos", "Precio (USD)": 0.0},
        {"Artículo": "Muebles", "Precio (USD)": 0.0},
        {"Artículo": "Herramientas", "Precio (USD)": 0.0},
        {"Artículo": "Productos alimenticios", "Precio (USD)": 0.0},
        {"Artículo": "Aparatos electrónicos portátiles", "Precio (USD)": 0.0}
    ], index=[1, 2, 3, 4, 5, 6])

df_articulos = st.data_editor(
    st.session_state.lista_articulos,
    num_rows="fixed",  
    use_container_width=True,
    key="editor_articulos",
    disabled=["Artículo"], 
    column_config={
        "Artículo": st.column_config.TextColumn("Descripción"),
        "Precio (USD)": st.column_config.NumberColumn("Valor ($ USD)", min_value=0.0, format="$%.2f", required=True)
    }
)

valor_total_usd = df_articulos["Precio (USD)"].sum() if not df_articulos.empty else 0.0
st.metric(label="Valor Total de tu Compra", value=f"${valor_total_usd:,.2f} USD")

st.divider()

# --- 3. DATOS DEL VIAJE Y PASAJEROS ---
st.subheader("📋 Datos del Viajero / Grupo")
nombre_usuario = st.text_input("Nombre del Pasajero / Familia", value="", placeholder="Ej. Familia Pérez")
num_pasajeros = st.number_input("Número de pasajeros viajando juntos", min_value=1, max_value=20, value=1, step=1)

via_defecto = ["Terrestre", "Aérea / Marítima"] if "AICM" not in ciudad_seleccionada and "Cancún" not in ciudad_seleccionada else ["Aérea / Marítima", "Terrestre"]
via = st.selectbox("¿Cómo ingresas al país?", via_defecto)
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
    
    articulos_con_valor = df_articulos[df_articulos["Precio (USD)"] > 0]
    
    html_filas_articulos = ""
    if not articulos_con_valor.empty:
        for idx, fila in articulos_con_valor.iterrows():
            html_filas_articulos += f"<tr><td style='padding: 4px 0;'>{idx}. {fila['Artículo']}</td><td style='text-align: right; padding: 4px 0;'>${fila['Precio (USD)']:,.2f} USD</td></tr>"
    else:
        html_filas_articulos = "<tr><td colspan='2' style='font-style: italic; color: #888;'>Sin artículos declarados</td></tr>"

    zona_horaria_objeto = pytz.timezone(CIUDADES_ADUANA[ciudad_seleccionada])
    fecha_actual = datetime.now(zona_horaria_objeto).strftime("%Y-%m-%d %H:%M")
    nombre_ticket = nombre_usuario.strip() if nombre_usuario.strip() else "No especificado"

    texto_para_qr = (
        f"ADUANA {ciudad_seleccionada.upper()}\n"
        f"Fecha: {fecha_actual}\n"
        f"Pasajero: {nombre_ticket}\n"
        f"Total Artículos: ${valor_total_usd:,.2f} USD\n"
        f"TOTAL A PAGAR: ${res['Impuesto_MXN']:,.2f} MXN"
    )
    qr_url_encoded = urllib.parse.quote(texto_para_qr)
    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={qr_url_encoded}"

    ticket_html = f"""<div id="seccion-ticket" style="font-family: Arial, sans-serif; max-width: 450px; margin: 15px auto; padding: 20px; border: 1px dashed #bbb; border-radius: 8px; background-color: #ffffff; color: #000000; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);">
<h3 style="text-align: center; margin: 0 0 5px 0; font-size: 16px; color: #000; font-weight: bold;">TICKET ADUANA {ciudad_seleccionada.upper()}</h3>
<p style="text-align: center; margin: 0 0 15px 0; font-size: 11px; color: #666;">{fecha_actual}</p>
<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Pasajero/Familia:</b> {nombre_ticket}</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Pasajeros en Grupo:</b> {num_pasajeros}</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Vía de Entrada:</b> {via}</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Tipo de Cambio:</b> ${tipo_cambio:.2f} MXN</p>
<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
<h4 style="margin: 0 0 5px 0; font-size: 13px; color: #000; font-weight: bold;">DESGLOSE DE MERCANCÍA:</h4>
<table style="width: 100%; font-size: 13px; border-collapse: collapse; color: #000;">
{html_filas_articulos}
</table>
<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
<table style="width: 100%; font-size: 13px; line-height: 1.6; color: #000;">
<tr><td>Suma Total Artículos:</td><td style="text-align: right;">${valor_total_usd:,.2f} USD</td></tr>
<tr><td>Franquicia Individual:</td><td style="text-align: right;">${res['Franquicia_Individual']:.2f} USD</td></tr>
<tr><td><b>Franquicia Total ({num_pasajeros} pasajeros):</b></td><td style="text-align: right;"><b>-${res['Franquicia_Total']:.2f} USD</b></td></tr>
<tr><td>Excedente Gravable:</td><td style="text-align: right;">${res['Excedente_USD']:,.2f} USD</td></tr>
<tr><td>Tasa de Impuesto:</td><td style="text-align: right;">{res['Tasa']}</td></tr>
<tr style="font-size: 16px; font-weight: bold; border-top: 1px solid #000;">
<td style="padding-top: 8px; color: #000;">TOTAL A PAGAR:</td>
<td style="text-align: right; padding-top: 8px; color: #000;">${res['Impuesto_MXN']:,.2f} MXN</td>
</tr>
</table>
<div style="text-align: center; margin: 20px 0 10px 0;">
<img src="{qr_image_url}" alt="Código QR de Validación" style="border: 1px solid #ddd; padding: 5px; background-color: #fff; width: 130px; height: 130px;" />
<p style="margin: 5px 0 0 0; font-size: 10px; color: #444; font-style: italic;">Escanea para validar el desglose</p>
</div>
<div style="border-top: 1px dashed #000; margin: 10px 0 5px 0;"></div>
<p style="font-size: 11px; text-align: center; margin: 0; font-style: italic; color: #222;">{res['Mensaje']}</p>
</div>"""
    
    st.markdown(ticket_html, unsafe_allow_html=True)
    
    # --- PROCESAMIENTO MÓVIL ---
    html_impresion_completo = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Imprimir Ticket - Aduana</title>
    <style>
        body {{ background-color: #f3f4f6; margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
        .btn-imprimir {{
            display: block; width: 100%; max-width: 450px; margin: 10px auto;
            padding: 12px; background-color: #4CAF50; color: white; border: none;
            border-radius: 6px; font-weight: bold; font-size: 16px; text-align: center; cursor: pointer;
        }}
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ background-color: white; padding: 0; margin: 0; }}
            #seccion-ticket {{ border: none !important; box-shadow: none !important; margin: 0 !important; padding: 0 !important; }}
        }}
    </style>
</head>
<body>
    <button class="btn-imprimir no-print" onclick="window.print()">📥 CLIC AQUÍ PARA IMPRIMIR O GUARDAR PDF</button>
    {ticket_html}
    <script>
        window.onload = function() {{
            setTimeout(function() {{ window.print(); }}, 500);
        }};
    </script>
</body>
</html>"""

    b64_html = base64.b64encode(html_impresion_completo.encode('utf-8')).decode('utf-8')

    # Texto plano alternativo (.txt)
    texto_ticket_txt = (
        f"========================================\n"
        f"     TICKET ADUANA {ciudad_seleccionada.upper()}\n"
        f"========================================\n"
        f"Fecha local: {fecha_actual}\n"
        f"Pasajero/Familia: {nombre_ticket}\n"
        f"Total de Pasajeros: {num_pasajeros}\n"
        f"Vía de Entrada: {via}\n"
        f"Tipo de Cambio: ${tipo_cambio:.2f} MXN\n"
        f"----------------------------------------\n"
        f"ARTÍCULOS DETALLADOS:\n"
    )
    if not articulos_con_valor.empty:
        for idx, fila in articulos_con_valor.iterrows():
            texto_ticket_txt += f"{idx}. {fila['Artículo']}: ${fila['Precio (USD)']:,.2f} USD\n"
    else:
        texto_ticket_txt += "Sin artículos declarados\n"
        
    texto_ticket_txt += (
        f"----------------------------------------\n"
        f"Suma Total Artículos: ${valor_total_usd:,.2f} USD\n"
        f"Franquicia Total ({num_pasajeros} pasajeros): ${res['Franquicia_Total']:.2f} USD\n"
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
            label="📥 Descargar (.txt)",
            data=texto_ticket_txt,
            file_name=f"Desglose_{ciudad_seleccionada.replace(' ', '_')}_{nombre_archivo}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
    with col2:
        components.html(f"""
            <script>
                function abrirTicketMovil() {{
                    var b64Data = "{b64_html}";
                    var strData = atob(b64Data);
                    var charCodeArray = new Uint8Array(strData.length);
                    for (var i = 0; i < strData.length; i++) {{
                        charCodeArray[i] = strData.charCodeAt(i);
                    }}
                    var htmlDecodificado = new TextDecoder("utf-8").decode(charCodeArray);
                    
                    var ventanaImpresion = window.open('', '_blank');
                    if(ventanaImpresion) {{
                        ventanaImpresion.document.write(htmlDecodificado);
                        ventanaImpresion.document.close();
                    }} else {{
                        alert("Por favor, permite las ventanas emergentes (pop-ups) en tu navegador para ver el ticket.");
                    }}
                }}
            </script>
            <button onclick="abrirTicketMovil()" style="
                width: 100%; 
                height: 38px; 
                background-color: #4CAF50; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                font-weight: bold; 
                font-size: 14px;
                cursor: pointer;">
                🖨️ Imprimir / Guardar PDF
            </button>
        """, height=45)
