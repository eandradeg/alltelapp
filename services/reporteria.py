import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from database import get_db
from models import TiemPro
from datetime import datetime

def reporteria(permisionario):
    st.header("Reportería - Reclamos y Averías")
    
    # Obtener datos de incidencias de TiemPro
    db = next(get_db())
    incidencias = db.query(TiemPro).filter(TiemPro.permisionario == permisionario).all()
    
    if not incidencias:
        st.warning("No hay incidencias registradas para mostrar.")
        return
    
    # Lista de meses en español en orden secuencial
    meses_espanol = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    # Crear un diccionario de mapeo de mes en español a su número
    meses_numeros = {mes: idx + 1 for idx, mes in enumerate(meses_espanol)}
    
    # Obtener los años disponibles en las incidencias
    años = {inc.fecha_hora_registro.year for inc in incidencias if inc.fecha_hora_registro}
    
    # Selectores de mes y año
    mes_seleccionado = st.selectbox("Seleccione el mes", meses_espanol)
    año_seleccionado = st.selectbox("Seleccione el año", sorted(años, reverse=True))
    
    # Filtrar incidencias por mes y año
    incidencias_filtradas = [
        inc for inc in incidencias 
        if inc.fecha_hora_registro and 
           inc.fecha_hora_registro.month == meses_numeros[mes_seleccionado] and 
           inc.fecha_hora_registro.year == año_seleccionado
    ]
    
    if not incidencias_filtradas:
        st.warning("No hay incidencias para el mes y año seleccionados.")
        return
    
    # Definir tipos de reclamos y averías
    reclamos_generales = [
        "ACTIVACIÓN DEL SERVICIO EN TÉRMINOS DISTINTOS A LO FIJADO EN EL CONTRATO DE PRESTACIÓN DEL SERVICIO",
        "REACTIVACIÓN DEL SERVICIO EN PLAZOS DISTINTOS A LOS FIJADOS EN EL CONTRATO DE PRESTACIÓN DEL SERVICIO",
        "INCUMPLIMIENTO DE LAS CLÁUSULAS CONTRACTUALES PACTADAS",
        "SUSPENSIÓN DEL SERVICIO SIN FUNDAMENTO LEGAL O CONTRACTUAL",
        "NO TRAMITACIÓN DE SOLICITUD DE TERMINACIÓN DEL SERVICIO"
    ]

    averias = [
        "INDISPONIBILIDAD DEL SERVICIO",
        "INTERRUPCIÓN DEL SERVICIO",
        "DESCONEXIÓN O SUSPENSIÓN ERRÓNEA DEL SERVICIO",
        "DEGRADACIÓN DEL SERVICIO",
        "LIMITACIONES Y RESTRICCIONES DE USO DE APLICACIONES O DEL SERVICIO EN GENERAL SIN CONSENTIMIENTO DEL CLIENTE"
    ]
    
    # Selector de tipo de reporte
    tipo_reporte = st.selectbox("Seleccione el tipo de reporte", ["Reclamos Generales", "Reparación de Averías"])
    
    # Filtrar incidencias según el tipo de reporte
    if tipo_reporte == "Reclamos Generales":
        df_filtrado = pd.DataFrame([{
            "ITEM": inc.item,
            "PROVINCIA": inc.provincia,
            "MES": inc.mes,
            "FECHA Y HORA DEL REGISTRO DEL RECLAMO (dd/mm/aaaa hh:mm)": inc.fecha_hora_registro.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_registro else None,
            "NOMBRE DE LA PERSONA QUE REALIZA EL RECLAMO": inc.nombre_reclamante,
            "NÚMERO TELEFÓNICO DE CONTACTO DEL USUARIO": inc.telefono_contacto,
            "TIPO DE CONEXIÓN (CONMUTADA O NO CONMUTADA)": inc.tipo_conexion,
            "CANAL DE RECLAMO (PERSONALIZADO, TELEFÓNICO, CORREO ELECTRÓNICO, OFICIO, PÁGINA WEB)": inc.canal_reclamo,
            "TIPO DE RECLAMO": inc.tipo_reclamo,
            "FECHA Y HORA DE SOLUCIÓN DEL RECLAMO (dd/mm/aaaa hh:mm)": inc.fecha_hora_solucion.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_solucion else None,
            "TIEMPO DE RESOLUCIÓN DEL RECLAMO (calculo en HORAS) ( Campo No obligatorio)": (
                round((inc.fecha_hora_solucion - inc.fecha_hora_registro).total_seconds() / 3600, 2) if inc.fecha_hora_solucion and inc.fecha_hora_registro else None
            ),
            "DESCRIPCIÓN DE LA SOLUCIÓN": inc.descripcion_solucion
        } for inc in incidencias_filtradas if inc.tipo_reclamo in reclamos_generales])
        nombre_hoja = "ProcenRecGen"
        
    elif tipo_reporte == "Reparación de Averías":
        df_filtrado = pd.DataFrame([{
            "ITEM": inc.item,
            "PROVINCIA": inc.provincia,
            "NOMBRE DE LA PERSONA QUE REALIZA EL REQUERIMIENTO": inc.nombre_reclamante,
            "NÚMERO TELEFÓNICO DE CONTACTO DEL USUARIO": inc.telefono_contacto,
            "TIPO DE CONEXIÓN (CONMUTADA O NO CONMUTADA)": inc.tipo_conexion,
            "CANAL DE REQUERIMIENTO (PERSONALIZADO, TELEFÓNICO, OFICIO, CORREO ELECTRÓNICO, PÁGINA WEB)": inc.canal_reclamo,
            "TIPO DE AVERÍA": inc.tipo_reclamo,
            "FECHA Y HORA DE REPORTE DE LA AVERÍA (dd/mm/aaaa hh:mm)": inc.fecha_hora_registro.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_registro else None,
            "FECHA Y HORA DE REPARACIÓN DE LA AVERÍA (dd/mm/aaaa hh:mm)": inc.fecha_hora_solucion.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_solucion else None,
            "TIEMPO DE REPARACIÓN DE LA AVERÍA (calculo en HORAS) ( Campo No obligatorio)": (
                round((inc.fecha_hora_solucion - inc.fecha_hora_registro).total_seconds() / 3600, 2) if inc.fecha_hora_solucion and inc.fecha_hora_registro else None
            ),
            "DESCRIPCIÓN DE LA SOLUCIÓN": inc.descripcion_solucion
        } for inc in incidencias_filtradas if inc.tipo_reclamo in averias])
        nombre_hoja = "TiemPromRep"
    
    # Mostrar DataFrame
    st.dataframe(df_filtrado)
    
    # Función para generar Excel con la hoja adecuada
    def generar_excel(df, nombre_hoja):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
        output.seek(0)
        return output
    
    # Botón de descarga de Excel
    if not df_filtrado.empty:
        excel_file = generar_excel(df_filtrado, nombre_hoja)
        st.download_button(
            label=f"📥 Descargar Reporte de {tipo_reporte} en Excel",
            data=excel_file,
            file_name=f'Reporte_{tipo_reporte.replace(" ", "_")}_{permisionario}_{mes_seleccionado}_{año_seleccionado}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    # Gráficos y análisis
    st.subheader(f"Análisis de {tipo_reporte}")
    
    fig_provincia = px.bar(
        df_filtrado.groupby("PROVINCIA").size().reset_index(name='Cantidad'),
        x="PROVINCIA",
        y="Cantidad",
        title=f"{tipo_reporte} por Provincia"
    )
    st.plotly_chart(fig_provincia)

    db.close()
