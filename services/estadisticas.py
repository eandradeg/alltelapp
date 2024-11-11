import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db
from models import TiemPro


def estadisticas(permisionario):
        st.header("Estadísticas de Incidencias")

        # Obtener datos de incidencias
        db = next(get_db())
        incidencias = db.query(TiemPro).filter(TiemPro.permisionario == permisionario).all()

        if not incidencias:
            st.warning("No hay incidencias registradas para mostrar.")
            return
        
        # Métricas generales
        total_incidencias = len(incidencias)
        tiempo_promedio = sum(inc.tiempo_resolucion_horas for inc in incidencias) / total_incidencias if total_incidencias > 0 else 0
        pendientes = sum(1 for inc in incidencias if inc.estado_incidencia == "Pendiente")
        finalizadas = sum(1 for inc in incidencias if inc.estado_incidencia == "Finalizado")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Incidencias", total_incidencias)
        with col2:
            st.metric("Incidencias Finalizadas", finalizadas)
        with col3:
            st.metric("Incidencias Pendientes", pendientes)
        with col4:
            st.metric("Tiempo Promedio de Resolución (horas)", f"{tiempo_promedio:.2f}")


         # Crear DataFrame completo con todos los datos
        df_completo = pd.DataFrame([
            {
                "Item": inc.item,
                "Provincia": inc.provincia,
                "Mes": inc.mes,
                "Fecha Registro": inc.fecha_hora_registro,
                "Nombre Reclamante": inc.nombre_reclamante,
                "Teléfono": inc.telefono_contacto,
                "Tipo Conexión": inc.tipo_conexion,
                "Tipo Reclamo": inc.tipo_reclamo,
                "Canal Reclamo": inc.canal_reclamo,
                "Fecha Solución": inc.fecha_hora_solucion,
                "Tiempo Resolución (horas)": inc.tiempo_resolucion_horas,
                "Descripcion Incidencia":inc.descripcion_incidencia,
                "Descripción Solución": inc.descripcion_solucion,
                "Estado": inc.estado_incidencia,
                
            } for inc in incidencias
        ])

              
        # Agregar filtros
        st.subheader("Filtros")
        col1, col2 = st.columns(2)
        with col1:
            # Filtro por mes
            meses_disponibles = ["Todos"] + sorted(list(df_completo["Mes"].unique()))
            mes_seleccionado = st.selectbox("Filtrar por Mes", meses_disponibles)
        
        with col2:
            # Filtro por tipo de reclamo
            tipos_reclamo = ["Todos"] + sorted(list(df_completo["Tipo Reclamo"].unique()))
            tipo_seleccionado = st.selectbox("Filtrar por Tipo de Reclamo", tipos_reclamo)

        # Aplicar filtros
        df_filtrado = df_completo.copy()
        if mes_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Mes"] == mes_seleccionado]
        if tipo_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo Reclamo"] == tipo_seleccionado]

        # Gráficos
        st.subheader("Análisis Visual")
        tab1, tab2, tab3 = st.tabs(["Incidencias por Tipo", "Incidencias por Mes", "Estado de Incidencias"])
        
        with tab1:
            if not df_filtrado.empty:
                tipo_incidencias = df_filtrado['Tipo Reclamo'].value_counts()
                fig_tipo = px.pie(
                    values=tipo_incidencias.values,
                    names=tipo_incidencias.index,
                    title="Distribución de Incidencias por Tipo"
                )
                st.plotly_chart(fig_tipo)
            else:
                st.warning("No hay datos para mostrar en el gráfico de incidencias por tipo.")

        with tab2:
            if not df_filtrado.empty:
                incidencias_mes = df_filtrado.groupby("Mes").size().reset_index(name='Cantidad')
                fig_mes = px.bar(
                    incidencias_mes,
                    x="Mes",
                    y="Cantidad",
                    title="Incidencias por Mes"
                )
                st.plotly_chart(fig_mes)
            else:
                st.warning("No hay datos para mostrar en el gráfico de incidencias por mes.")

        with tab3:
            if not df_filtrado.empty:
                estado_incidencias = df_filtrado['Estado'].value_counts()
                fig_estado = px.pie(
                    values=estado_incidencias.values,
                    names=estado_incidencias.index,
                    title="Estado de las Incidencias"
                )
                st.plotly_chart(fig_estado)
            else:
                st.warning("No hay datos para mostrar en el gráfico de estados.")

        # Estadísticas adicionales
        st.subheader("Estadísticas Detalladas")
        if not df_filtrado.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                tiempo_max = df_filtrado['Tiempo Resolución (horas)'].max()
                st.metric(
                    "Tiempo Máximo de Resolución",
                    f"{tiempo_max:.2f} horas"
                )
            
            with col2:
                tiempo_min = df_filtrado['Tiempo Resolución (horas)'].min()
                st.metric(
                    "Tiempo Mínimo de Resolución",
                    f"{tiempo_min:.2f} horas"
                )
            
            with col3:
                resueltos = len(df_filtrado[df_filtrado["Estado"] == "Resuelto"])
                total = len(df_filtrado)
                tasa_resolucion = (resueltos/total*100) if total > 0 else 0
                st.metric(
                    "Tasa de Resolución",
                    f"{tasa_resolucion:.1f}%"
                )

            # Tabla de resumen por tipo de reclamo
            st.subheader("Resumen por Tipo de Reclamo")
            resumen_tipo = df_filtrado.groupby("Tipo Reclamo").agg({
                'Tiempo Resolución (horas)': ['count', 'mean', 'min', 'max']
            }).round(2)
            resumen_tipo.columns = ['Cantidad', 'Tiempo Promedio', 'Tiempo Mínimo', 'Tiempo Máximo']
            st.dataframe(resumen_tipo)

        else:
            st.warning("No hay datos disponibles para mostrar estadísticas detalladas.")

        db.close()