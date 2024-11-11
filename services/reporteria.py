import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from database import get_db
from models import TiemPro

       
def reporteria(permisionario):
    st.header("Reportería")
    
    # Obtener datos de incidencias
    db = next(get_db())
    incidencias = db.query(TiemPro).filter(TiemPro.permisionario == permisionario).all()
    
    if not incidencias:
        st.warning("No hay incidencias registradas para mostrar.")
        return
    
    # Crear DataFrame con todas las incidencias
    df_incidencias = pd.DataFrame([{
        "ITEM": inc.item,
        "PROVINCIA": inc.provincia,
        "MES": inc.mes,
        "FECHA Y HORA DEL REGISTRO DEL RECLAMO": inc.fecha_hora_registro.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_registro else None,
        "NOMBRE DE LA PERSONA QUE REALIZA EL RECLAMO": inc.nombre_reclamante,
        "NÚMERO TELEFÓNICO DE CONTACTO DEL USUARIO": inc.telefono_contacto,
        "TIPO DE CONEXIÓN": inc.tipo_conexion,
        "CANAL DE RECLAMO": inc.canal_reclamo,
        "TIPO DE RECLAMO": inc.tipo_reclamo,
        "FECHA Y HORA DE SOLUCIÓN DEL RECLAMO": inc.fecha_hora_solucion.strftime("%d/%m/%Y %H:%M") if inc.fecha_hora_solucion else None,
        "TIEMPO DE RESOLUCIÓN DEL RECLAMO (HORAS)": inc.tiempo_resolucion_horas,
        "DESCRIPCIÓN DE LA SOLUCIÓN": inc.descripcion_solucion,
        "PERMISIONARIO": inc.permisionario,
        "CATEGORÍA": "Reclamos Generales" if "Reclamo" in str(inc.tipo_reclamo).upper() else 
                     "Reparación de Averías" if "AVERÍA" in str(inc.tipo_reclamo).upper() else 
                     "Otros"
    } for inc in incidencias])
    
    # Selector de tipo de reporte
    tipo_reporte = st.selectbox("Seleccione el tipo de reporte", [
        "Todos", 
        "Reclamos Generales", 
        "Reparación de Averías", 
        "Otros"
    ])
    
    # Filtro basado en el tipo de reclamo
    opciones_incidencias = {
        "Reparación de Averías": [
            "INDISPONIBILIDAD DEL SERVICIO",
            "INTERRUPCIÓN DEL SERVICIO",
            "DESCONEXIÓN O SUSPENSIÓN ERRÓNEA DEL SERVICIO",
            "DEGRADACIÓN DEL SERVICIO",
            "LIMITACIONES Y RESTRICCIONES DE USO DE APLICACIONES O DEL SERVICIO EN GENERAL SIN CONSENTIMIENTO DEL CLIENTE"
        ],
        
        "Reclamos Generales": [
            "ACTIVACIÓN DEL SERVICIO EN TÉRMINOS DISTINTOS A LO FIJADO EN EL CONTRATO DE PRESTACIÓN DEL SERVICIO",
            "REACTIVACIÓN DEL SERVICIO EN PLAZOS DISTINTOS A LOS FIJADOS EN EL CONTRATO DE PRESTACIÓN DEL SERVICIO",
            "INCUMPLIMIENTO DE LAS CLÁUSULAS CONTRACTUALES PACTADAS",
            "SUSPENSIÓN DEL SERVICIO SIN FUNDAMENTO LEGAL O CONTRACTUAL",
            "NO TRAMITACIÓN DE SOLICITUD DE TERMINACIÓN DEL SERVICIO"
        ],
        
        "Otros": [
            "CAPACIDAD DE CANAL",
            "NO PROCEDENTES"
        ]
    }
    
    # Filtrar por tipo de reclamo según las categorías
    if tipo_reporte != "Todos":
        categorias_validas = opciones_incidencias[tipo_reporte]
        df_filtrado = df_incidencias[df_incidencias["TIPO DE RECLAMO"].isin(categorias_validas)]
    else:
        df_filtrado = df_incidencias
    
    # Mostrar DataFrame
    st.dataframe(df_filtrado)
    
    # Función para generar Excel con múltiples hojas
    def generar_excel_multihojas(df_principal):
        # Crear un escritor de Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja principal con todos los datos
            df_principal.to_excel(writer, sheet_name='Reporte Completo', index=False)
            
            # Hoja de resumen
            resumen = pd.DataFrame({
                'Métrica': [
                    'Total de Incidencias', 
                    'Tiempo Promedio de Resolución', 
                    'Incidencia con Mayor Tiempo de Resolución',
                    'Incidencia con Menor Tiempo de Resolución'
                ],
                'Valor': [
                    len(df_principal),
                    df_principal['TIEMPO DE RESOLUCIÓN DEL RECLAMO (HORAS)'].mean(),
                    df_principal['TIEMPO DE RESOLUCIÓN DEL RECLAMO (HORAS)'].max(),
                    df_principal['TIEMPO DE RESOLUCIÓN DEL RECLAMO (HORAS)'].min()
                ]
            })
            resumen.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja de distribución por provincia
            distribucion_provincia = df_principal.groupby('PROVINCIA').size().reset_index(name='CANTIDAD')
            distribucion_provincia.to_excel(writer, sheet_name='Distribución por Provincia', index=False)
        
        # Mover el puntero al inicio del BytesIO
        output.seek(0)
        return output
    
    # Botón de descarga de Excel
    if not df_filtrado.empty:
        excel_file = generar_excel_multihojas(df_filtrado)
        st.download_button(
            label="📥 Descargar Reporte en Excel",
            data=excel_file,
            file_name=f'Reporte_Incidencias_{tipo_reporte}_{permisionario}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    # Gráficos y análisis
    st.subheader("Análisis de Reportes")
    
    # Distribución por tipo de reclamo
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Distribución por Tipo de Reclamo")
        fig_tipo = px.pie(
            df_filtrado, 
            names="TIPO DE RECLAMO", 
            title="Distribución de Reclamos"
        )
        st.plotly_chart(fig_tipo)
    
    with col2:
        st.write("Tiempo Promedio de Resolución")
        tiempo_promedio = df_filtrado['TIEMPO DE RESOLUCIÓN DEL RECLAMO (HORAS)'].mean()
        st.metric("Tiempo Promedio de Resolución", f"{tiempo_promedio:.2f} horas")
    
    # Distribución por provincia
    st.write("Distribución de Incidencias por Provincia")
    fig_provincia = px.bar(
        df_filtrado.groupby("PROVINCIA").size().reset_index(name='Cantidad'),
        x="PROVINCIA",
        y="Cantidad",
        title="Incidencias por Provincia"
    )
    st.plotly_chart(fig_provincia)

    db.close()