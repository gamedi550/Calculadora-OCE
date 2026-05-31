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
    st.write("""Consulta qué artículos se consideran **Equipaje Personal** (entran gratis) y cómo funcionan las **Franquicias**.""")
    
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
st.write("""Calculadora de equipaje familiar con franquicia acumulada y sección especial de licores/tabacos.""")

# --- 1. CONFIGURACIÓN AVANZADA ---
with st.expander("⚙️ Configuración de Tasas e Impuestos", expanded=False):
    tasa_impuesto = st.number_input("Tasa Global de Impuesto General (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
    tipo_cambio_del_dia = obtener_tipo_cambio_real()
    tipo_cambio = st.number_input("Tipo de cambio (MXN por USD)", min_value=1.0, step=0.05, value=tipo_cambio_del_dia)
    st.caption(f"""💡 Tipo de cambio oficial sincronizado hoy: **${tipo_cambio_del_dia} MXN**""")

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
st.caption("""Nota: Estos artículos pagan impuesto directo desde el primer dólar excedente según la normatividad fiscal.""")

if "lista_extras" not in st.session_state:
    st.session_state.lista_extras = pd.DataFrame([
        {"Categoría": "Bebidas Alcohólicas / Licores (>20°)", "Precio (USD)": 0.0, "Tasa (%)": 90.0},
        {"Categoría": "Vino / Cerveza (<14°)", "Precio (USD)": 0.0, "Tasa (%)": 75.0},
        {"Categoría": "Tabacos / Cigarros / Puros", "Precio (USD)": 0.0, "Tasa (%)": 350.0}
    ], index=[1, 2, 3])

df_extras_editado = st.data_editor(
    st.session_state.lista_extras,
    num_rows="fixed",
    use_container_width=True,
    key="editor_extras",
    disabled=["Categoría"],
    column_config={
        "Categoría": st.column_config.TextColumn("Tipo de Producto"),
        "Precio (USD)": st.column_config.NumberColumn("Valor Excedente ($ USD)", min_value=0.0, format="$%.2f", required=True),
        "Tasa (%)": st.column_config.NumberColumn("Tasa Impuesto SAT", format="%d%%")
    }
)
valor_extras_usd = df_extras_editado["Precio (USD)"].sum()

# Métricas combinadas
col_m1, col_m2 = st.columns(2)
with col_m1:
    st.metric(label="Total Mercancía General", value=f"${valor_total_usd:,.2f} USD")
with col_m2:
    st.metric(label="Total Bebidas y Tabaco", value=f"${valor_extras_usd:,.2f} USD")

st.divider()

# --- 4. DATOS DEL VIAJE Y PASAJEROS ---
st.subheader("📋 Datos del Viajero / Grupo")
nombre_usuario = st.text_input("Nombre del Pasajero / Familia", value="", placeholder="Ej. Familia Pérez")
num_pasajeros = st.number_input("Número de pasajeros viajando juntos", min_value=1, max_value=20, value=1, step=1)

via_defecto = ["Terrestre", "Aérea / Marítima"] if "AICM" not in ciudad_seleccionada and "Cancún" not in ciudad_seleccionada else ["Aérea / Marítima", "Terrestre"]
via = st.selectbox("¿Cómo ingresas al país?", via_defecto)

st.divider()

# --- 5. CONTROL DE EJECUCIÓN ---
if "mostrar_resultados" not in st.session_state:
    st.session_state.mostrar_resultados = False

if st.button("Calcular Impuestos Totales", type="primary", use_container_width=True):
    st.session_state.mostrar_resultados = True

# --- 6. RESULTADOS E IMPRESIÓN ---
if st.session_state.mostrar_resultados:
    res = calcular_impuestos_equipaje(
        valor_total_usd=valor_total_usd, 
        df_extras=df_extras_editado, 
        tipo_de_cambio=tipo_cambio, 
        tasa_global_pct=tasa_impuesto, 
        num_pasajeros=num_pasajeros
    )
    
    st.subheader("📋 Resultado del Cálculo")
    
    # Desglose: Mercancía General
    articulos_con_valor = df_articulos_editado[df_articulos_editado["Precio (USD)"] > 0]
    html_filas_articulos = ""
    if not articulos_con_valor.empty:
        for idx, fila in articulos_con_valor.iterrows():
            html_filas_articulos += f"<tr><td style='padding: 4px 0;'>• {fila['Artículo']}</td><td style='text-align: right; padding: 4px 0;'>${fila['Precio (USD)']:,.2f} USD</td></tr>"
    else:
        html_filas_articulos = "<tr><td colspan='2' style='font-style: italic; color: #888;'>Sin artículos declarados</td></tr>"

    # Desglose: Alcoholes y Tabacos
    extras_con_valor = df_extras_editado[df_extras_editado["Precio (USD)"] > 0]
    html_filas_extras = ""
    if not extras_con_valor.empty:
        for idx, fila in extras_con_valor.iterrows():
            html_filas_extras += f"<tr><td style='padding: 4px 0;'>🍾 {fila['Categoría']} (<small>{fila['Tasa (%)']}%</small>)</td><td style='text-align: right; padding: 4px 0;'>${fila['Precio (USD)']:,.2f} USD</td></tr>"
    else:
        html_filas_extras = "<tr><td colspan='2' style='font-style: italic; color: #888;'>Sin excedentes de alcohol/tabaco</td></tr>"

    zona_horaria_objeto = pytz.timezone(CIUDADES_ADUANA[ciudad_seleccionada])
    fecha_actual = datetime.now(zona_horaria_objeto).strftime("%Y-%m-%d %H:%M")
    nombre_ticket = nombre_usuario.strip() if nombre_usuario.strip() else "No especificado"

    # Código QR dinámico
    texto_para_qr = (
        f"ADUANA {ciudad_seleccionada.upper()}\n"
        f"Pasajero: {nombre_ticket}\n"
        f"Merca: ${valor_total_usd:,.2f} USD\n"
        f"Extras: ${res['Valor_Extras_USD']:,.2f} USD\n"
        f"TOTAL: ${res['Impuesto_Total_MXN']:,.2f} MXN"
    )
    qr_url_encoded = urllib.parse.quote(texto_para_qr)
    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={qr_url_encoded}"

    # Plantilla Base del Ticket
    plantilla_ticket_html = """<div id="seccion-ticket" style="font-family: Arial, sans-serif; max-width: 450px; margin: 15px auto; padding: 20px; border: 1px dashed #bbb; border-radius: 8px; background-color: #ffffff; color: #000000; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);">
<h3 style="text-align: center; margin: 0 0 5px 0; font-size: 16px; color: #000; font-weight: bold;">TICKET ADUANA __CIUDAD__</h3>
<p style="text-align: center; margin: 0 0 15px 0; font-size: 11px; color: #666;">__FECHA__</p>
<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Pasajero/Familia:</b> __PASAJERO__</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Pasajeros en Grupo:</b> __NUM_PASAJEROS__</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Vía de Entrada:</b> __VIA__</p>
<p style="margin: 5px 0; font-size: 13px; color: #000;"><b>Tipo de Cambio:</b> $__TC__ MXN</p>
<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>

<h4 style="margin: 0 0 5px 0; font-size: 13px; color: #000; font-weight: bold;">MERCANCÍA GENERAL:</h4>
<table style="width: 100%; font-size: 12px; border-collapse: collapse; color: #000; margin-bottom: 5px;">
__FILAS_ARTICULOS__
</table>

<h4 style="margin: 10px 0 5px 0; font-size: 13px; color: #000; font-weight: bold;">EXCEDENTES ALCOHOL / TABACO:</h4>
<table style="width: 100%; font-size: 12px; border-collapse: collapse; color: #000;">
__FILAS_EXTRAS__
</table>

<div style="border-top: 1px dashed #000; margin: 10px 0;"></div>
<table style="width: 100%; font-size: 13px; line-height: 1.6; color: #000;">
<tr><td>Suma Mercancía General:</td><td style="text-align: right;">$__SUMA_GRAL__ USD</td></tr>
<tr><td>Franquicia Individual:</td><td style="text-align: right;">$__FRANQ_IND__ USD</td></tr>
<tr><td><b>Franquicia Total:</b></td><td style="text-align: right;"><b>-$__FRANQ_TOTAL__ USD</b></td></tr>
<tr><td>Excedente General Gravable:</td><td style="text-align: right;">$__EXCEDENTE_USD__ USD</td></tr>
<tr><td>Impuesto General (__TASA__):</td><td style="text-align: right; color: #444;">$__IMP_GRAL__ MXN</td></tr>
<tr style="border-bottom: 1px dotted #ccc; padding-bottom: 4px;"><td>Impuesto Especial Extras:</td><td style="text-align: right; color: #444;">$__IMP_EXTRAS__ MXN</td></tr>
<tr style="font-size: 16px; font-weight: bold; border-top: 1px solid #000;">
<td style="padding-top: 8px; color: #000;">TOTAL A PAGAR:</td>
<td style="text-align: right; padding-top: 8px; color: #000;">$__TOTAL_PAGAR__ MXN</td>
</tr>
</table>
<div style="text-align: center; margin: 20px 0 10px 0;">
<img src="__QR_URL__" alt="Código QR" style="border: 1px solid #ddd; padding: 5px; background-color: #fff; width: 130px; height: 130px;" />
</div>
<div style="border-top: 1px dashed #000; margin: 10px 0 5px 0;"></div>
<p style="font-size: 11px; text-align: center; margin: 0; font-style: italic; color: #222;">__MENSAJE__</p>
</div>"""

    # Inyección de valores segura mediante encadenamiento con paréntesis
    ticket_html = (plantilla_ticket_html
        .replace("__CIUDAD__", ciudad_seleccionada.upper())
        .replace("__FECHA__", fecha_actual)
        .replace("__PASAJERO__", nombre_ticket)
        .replace("__NUM_PASAJEROS__", str(num_pasajeros))
        .replace("__VIA__", via)
        .replace("__TC__", f"{tipo_cambio:.2f}")
        .replace("__FILAS_ARTICULOS__", html_filas_articulos)
        .replace("__FILAS_EXTRAS__", html_filas_extras)
        .replace("__SUMA_GRAL__", f"{valor_total_usd:,.2f}")
        .replace("__FRANQ_IND__", f"{res['Franquicia_Individual']:.2f}")
        .replace("__FRANQ_TOTAL__", f"{res['Franquicia_Total']:.2f}")
        .replace("__EXCEDENTE_USD__", f"{res['Excedente_USD']:,.2f}")
        .replace("__TASA__", res['Tasa_General'])
        .replace("__IMP_GRAL__", f"{res['Impuesto_General_MXN']:,.2f}")
        .replace("__IMP_EXTRAS__", f"{res['Impuesto_Extras_MXN']:,.2f}")
        .replace("__TOTAL_PAGAR__", f"{res['Impuesto_Total_MXN']:,.2f}")
        .replace("__QR_URL__", qr_image_url)
        .replace("__MENSAJE__", res['Mensaje'])
    )

    st.markdown(ticket_html, unsafe_allow_html=True)
    
    # Estructura limpia para impresión externa organizada en bloques multilínea legítimos
    html_impresion_completo = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Imprimir Ticket</title>
    <style>
        body { background-color: #f3f4f6; margin: 0; padding: 10px; font-family: Arial, sans-serif; }
        .btn-imprimir { display: block; width: 100%; max-width: 450px; margin: 10px auto; padding: 12px; background-color: #4CAF50; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 16px; text-align: center; cursor: pointer; }
        @media print { 
            .no-print { display: none !important; } 
            body { background-color: white; padding: 0; margin: 0; } 
            #seccion-ticket { border: none !important; box-shadow: none !important; margin: 0 !important; padding: 0 !important; } 
        }
    </style>
</head>
<body>
    <button class="btn-imprimir no-print" onclick="window.print()">📥 CLIC AQUÍ PARA IMPRIMIR O GUARDAR PDF</button>
    __TICKET__
</body>
</html>"""
    
    html_impresion_completo = html_impresion_completo.replace("__TICKET__", ticket_html)

    # Texto plano (.txt)
    texto_ticket_txt = (
        f"========================================\n"
        f"     TICKET ADUANA {ciudad_seleccionada.upper()}\n"
        f"========================================\n"
        f"Fecha local: {fecha_actual}\n"
        f"Pasajero: {nombre_ticket}\n"
        f"Total Pasajeros: {num_pasajeros}\n"
        f"Tipo de Cambio: ${tipo_cambio:.2f} MXN\n"
        f"----------------------------------------\n"
        f"Total Mercancía:      ${valor_total_usd:,.2f} USD\n"
        f"Franquicia Aplicada:  -${res['Franquicia_Total']:.2f} USD\n"
        f"Impuesto Gral:        ${res['Impuesto_General_MXN']:,.2f} MXN\n"
        f"Impuesto Extras:      ${res['Impuesto_Extras_MXN']:,.2f} MXN\n"
        f"----------------------------------------\n"
        f"TOTAL A PAGAR:        ${res['Impuesto_Total_MXN']:,.2f} MXN\n"
        f"========================================\n"
    )
    
    st.subheader("🖨️ Exportar o Imprimir")
    col1, col2 = st.columns(2)
    with col1:
        nombre_archivo = nombre_usuario.replace(" ", "_") if nombre_usuario.strip() else "Pasajero"
        st.download_button(label="📥 Descargar (.txt)", data=texto_ticket_txt, file_name=f"Desglose_{nombre_archivo}.txt", mime="text/plain", use_container_width=True)
    with col2:
        st.download_button(label="🖨️ Guardar Ticket HTML", data=html_impresion_completo, file_name=f"Ticket_Aduana_{nombre_archivo}.html", mime="text/html", use_container_width=True)
