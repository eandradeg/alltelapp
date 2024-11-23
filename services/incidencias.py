import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
from database import get_db
from models import TiemPro, Client
from sqlalchemy import func


def registrar_tiempro(data_tiempro):
    db = next(get_db())
    try:
        new_entry = TiemPro(**data_tiempro)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Error al registrar incidencia en TiemPro: {str(e)}")
        return False
    finally:
        db.close()
        
# Diccionario para traducir los nombres de los meses al español
meses_espanol = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }         

def obtener_ultimo_item(db, permisionario):
        try:
            # Expira todas las entidades para obtener los datos más recientes desde la base de datos
            db.expire_all()
            
            # Obtener el valor máximo de `item` actual para el permisionario
            ultimo_item = db.query(func.max(TiemPro.item)).filter(TiemPro.permisionario == permisionario).execution_options(populate_existing=True).scalar()
            
            # Si no hay ningún ítem, el siguiente debe ser 1
            if ultimo_item is None:
                return 1
            
            # Si hay un valor máximo, incrementarlo en 1 para el siguiente `item`
            siguiente_item = int(ultimo_item) + 1
            print(f"Siguiente ítem para permisionario '{permisionario}': {siguiente_item}")
            
            return siguiente_item

        except Exception as e:
            print(f"Error al obtener el último ítem: {e}")
            return 1   


def mostrar_opciones_incidencia(client_id):
        
        # Initialize the session state for this client if it doesn't exist
        if f'incidencia_state_{client_id}' not in st.session_state:
            st.session_state[f'incidencia_state_{client_id}'] = {
                'incidencia_seleccionada': "Selecciona una incidencia"
            }
        
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
    # Lista completa de opciones para el selectbox
        opciones_lista = ["Selecciona una incidencia"] + [
            f"{categoria}: {incidencia}"
            for categoria, incidencias in opciones_incidencias.items()
            for incidencia in incidencias
        ]

        # Selector de incidencia
        incidencia_seleccionada = st.selectbox(
            "Tipo de Incidencia",
            opciones_lista,
            key=f"incidencia_selector_{client_id}",
            index=opciones_lista.index(st.session_state[f'incidencia_state_{client_id}']['incidencia_seleccionada'])
        )
        print(incidencia_seleccionada)

    # Actualizar el estado cuando cambie la selección
        if incidencia_seleccionada != st.session_state[f'incidencia_state_{client_id}']['incidencia_seleccionada']:
            st.session_state[f'incidencia_state_{client_id}']['incidencia_seleccionada'] = incidencia_seleccionada
            st.rerun()


        # Si se selecciona una incidencia válida
        if incidencia_seleccionada != "Selecciona una incidencia":
            # Obtener información del cliente
            db = next(get_db())
            client = db.query(Client).filter(Client.id == client_id).first()
            db.close()

            if client:
                st.write("---")
                st.write("**Registrar detalles de la incidencia**")
                
                with st.form(key=f'tiempro_form_{client_id}'):
                    
                    zona_horaria = pytz.timezone('America/Guayaquil')
                    fecha_hora_registro = datetime.now(zona_horaria).replace(tzinfo=None)
                    
                                       
                    # Campos que se rellenan automáticamente
                    data_tiempro = {
                        "provincia": client.provincia,
                        "mes": meses_espanol[fecha_hora_registro.strftime("%B")],
                        "fecha_hora_registro": fecha_hora_registro,
                        "nombre_reclamante": f"{client.cliente}",
                        "telefono_contacto": client.telefono,
                        "tipo_conexion": "NO CONMUTADA",
                        "tipo_reclamo": incidencia_seleccionada.split(": ")[1],
                        "permisionario": client.permisionario,
                        "estado_incidencia": "Pendiente"
                    }
                    
         
                    # Mostrar campos automáticos
                    st.write("### Información del cliente")
                    for key, value in data_tiempro.items():
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    
                    # Campos editables
                    st.write("### Información requerida")
                    
                    canal_reclamo = st.selectbox(
                        "Canal de Reclamo", 
                        ["PERSONALIZADO", "TELEFÓNICO", "OFICIO", "CORREO ELECTRÓNICO", "PÁGINA WEB"],
                        key=f"canal_reclamo_{client_id}"
                    )
                    descripcion_incidencia = st.text_area("Descripción de la Incidencia", key=f"descripcion_{client_id}")
                    fecha_hora_solucion = st.date_input("Fecha Hora Solución", key=f"fecha_solucion_{client_id}")
                    tiempo_resolucion_horas = st.number_input(
                        "Tiempo de Resolución en Horas", 
                        min_value=0.0, 
                        format="%.2f",
                        key=f"tiempo_resolucion_{client_id}"
                    )
                    
                    # Botón de envío del formulario
                    submitted = st.form_submit_button("Registrar Incidencia")
                    if submitted:
                        # Obtener el siguiente número de `item`
                        db = next(get_db())
                        
                        # Llamar a la función para obtener el último `item` sin usar caché
                        nuevo_item = obtener_ultimo_item(db, client.permisionario)
                        print(f"Siguiente número de ítem generado: {nuevo_item}")
                        
                        # Actualizar el diccionario `data_tiempro` con los datos del nuevo `item`
                        data_tiempro.update({
                            "item": nuevo_item,
                            "canal_reclamo": canal_reclamo,
                            "descripcion_incidencia": descripcion_incidencia,
                            "fecha_hora_solucion": fecha_hora_solucion,
                            "tiempo_resolucion_horas": tiempo_resolucion_horas
                        })
                        
                        # Registrar el nuevo `item` en la base de datos
                        if registrar_tiempro(data_tiempro):
                            try:
                                # Confirmar los cambios en la base de datos
                                db.commit()
                                
                                # Crear una ventana emergente con el número de ítem
                                st.markdown(
                                    f"""
                                    <style>
                                        .stAlert {{
                                            background-color: #0f5132;
                                            color: white;
                                            padding: 20px;
                                            border-radius: 10px;
                                            text-align: center;
                                            margin: 10px 0;
                                        }}
                                    </style>
                                    """,
                                    unsafe_allow_html=True
                                )
                                
                                # Mostrar el mensaje de éxito con el número de ítem
                                st.success(f"""
                                    ✅ Incidencia registrada exitosamente
                                    
                                    Número de Incidencia: {nuevo_item}
                                    
                                    """)
                                
                                # Limpiar el estado
                                st.session_state[f'incidencia_state_{client_id}']['incidencia_seleccionada'] = "Selecciona una incidencia"
                            
                            except Exception as e:
                                # Si ocurre un error, hacer rollback de la transacción
                                db.rollback()
                                st.error(f"Error al registrar la incidencia: {e}")
                            
                        else:
                            st.error("Error al registrar la incidencia.")
                        
                        # Cerrar la sesión de la base de datos
                        db.close()

                return incidencia_seleccionada


def incidencias(permisionario):
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

        search_term = st.text_input("Buscar por Cliente o Número de Incidencia")

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
                "Descripcion Incidencia": inc.descripcion_incidencia,
                "Descripción Solución": inc.descripcion_solucion,
                "Estado": inc.estado_incidencia,
            } for inc in incidencias
        ])

        # Aplicar filtro de búsqueda solo si se proporciona un término
        if search_term:
            df_completo = df_completo[
                ((df_completo["Nombre Reclamante"].str.contains(search_term, case=False, na=False)) |
                (df_completo["Item"].astype(str) == search_term)) &
                (df_completo["Estado"] == "Pendiente")
            ]

        # Mostrar el selector de incidencia solo si hay resultados tras la búsqueda
        if not df_completo.empty:
            item_seleccionado = st.selectbox(
                "Selecciona una incidencia por número de Item para actualizar:",
                options=[""] + list(df_completo["Item"].unique()),
                index=0,
                format_func=lambda x: "Selecciona una incidencia" if x == "" else x
            )

            if item_seleccionado:
                incidencia_seleccionada = df_completo[df_completo["Item"] == item_seleccionado].iloc[0]
                st.write("### Detalles de la Incidencia")
                st.write(f"**Cliente:** {incidencia_seleccionada['Nombre Reclamante']}")
                st.write(f"**Tipo de Reclamo:** {incidencia_seleccionada['Tipo Reclamo']}")
                st.write(f"**Fecha de Registro:** {incidencia_seleccionada['Fecha Registro']}")

                # Formulario para la solución
                with st.form(key=f'solucion_form_{item_seleccionado}'):
                    descripcion_solucion = st.text_area(
                        "Descripción de la Solución",
                        value=incidencia_seleccionada['Descripción Solución'] if pd.notna(incidencia_seleccionada['Descripción Solución']) else "",
                        height=100
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        submit_solucion = st.form_submit_button("Guardar Solución")
                    with col2:
                        submit_finalizar = st.form_submit_button("Finalizar Incidencia")

                    if submit_solucion or submit_finalizar:
                        incidencia = db.query(TiemPro).filter(TiemPro.item == int(item_seleccionado)).first()
                        if incidencia:
                            incidencia.descripcion_solucion = descripcion_solucion
                        
                        if submit_finalizar:
                            incidencia.estado_incidencia = "Finalizado"
                            
                            zona_horaria = pytz.timezone('America/Guayaquil')
                            fecha_hora_solucion = datetime.now(zona_horaria).replace(tzinfo=None)
                            # Obtener la fecha y hora actual para la solución
                            incidencia.fecha_hora_solucion = fecha_hora_solucion  # Guardar la fecha y hora de solución
                            
                            if incidencia.fecha_hora_registro.tzinfo is None:
                                fecha_hora_registro = zona_horaria.localize(incidencia.fecha_hora_registro)
                            
                            tiempo_resolucion = (datetime.now(zona_horaria) - fecha_hora_registro).total_seconds() / 3600
                            incidencia.tiempo_resolucion_horas = round(tiempo_resolucion, 2)


                            # Guardar en la base de datos
                            try:
                                db.commit()  # Asegúrate de que se guarden los cambios
                                st.success("Incidencia finalizada y solución guardada con éxito.")
                            except Exception as e:
                                db.rollback()
                                st.error(f"Error al finalizar la incidencia: {str(e)}")    
                            
                        else:
                            st.error("No se pudo encontrar la incidencia seleccionada")

            # Aplicar filtros
            df_filtrado = df_completo.copy()
            
            # Mostrar DataFrame filtrado
            st.subheader("Registro de Incidencias")
            st.dataframe(df_filtrado)   

    