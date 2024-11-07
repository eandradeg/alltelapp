import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime
from database import get_db
from models import Client, Localidad, TiemPro
from sqlalchemy import distinct, func


# Configuración de la página (debe ser la primera instrucción de Streamlit)
st.set_page_config(page_title="Sistema de Gestión de Clientes", layout="wide")


def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Función para verificar el usuario
def check_user(username, password):
    users = {
        "admin": {"password": make_hash("admin123"), "permisionario": "per 1"},
        "user": {"password": make_hash("user123"), "permisionario": "per 2"}
    }
    if username in users and users[username]["password"] == make_hash(password):
        st.session_state['permisionario'] = users[username]["permisionario"]
        return True
    return False

# Función para crear el formulario de login
def login_form():
    with st.form("login_form"):
        st.markdown("### Inicio de Sesión")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")
        if submit:
            if check_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

# Función de logout
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Función para crear un cliente
def create_client(client_data):
    db = next(get_db())
    try:
        db_client = Client(**client_data)
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Error al crear cliente: {str(e)}")
        return False
    finally:
        db.close()

# Función para obtener clientes por permisionario
def get_clients(permisionario):
    db = next(get_db())
    return db.query(Client).filter(Client.permisionario == permisionario).all()

# Función para eliminar un cliente
def delete_client(client_id):
    db = next(get_db())
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            db.delete(client)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        st.error(f"Error al eliminar cliente: {str(e)}")
        return False

def update_client_status(client_id, nuevo_estado):
    db = next(get_db())
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            client.estado = nuevo_estado
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        st.error(f"Error al cambiar el estado: {str(e)}")
        return False
    finally:
        db.close()
        
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
    ultimo_item = db.query(func.max(TiemPro.item)).filter(TiemPro.permisionario == permisionario).scalar()
    if ultimo_item:
        # Si existe un último ítem, convertir a entero y sumar 1
        try:
            return str(int(ultimo_item) + 1)
        except ValueError:
            return "1"
    return "1"

def mostrar_opciones_incidencia(client_id):
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
                
                fecha_hora_registro = datetime.now()
                # Campos que se rellenan automáticamente
                data_tiempro = {
                    "provincia": client.provincia,
                    "mes": meses_espanol[fecha_hora_registro.strftime("%B")],
                    "fecha_hora_registro": fecha_hora_registro.strftime("%d/%m/%Y %H:%M"),
                    "nombre_reclamante": f"{client.nombres} {client.apellidos}",
                    "telefono_contacto": client.telefono,
                    "tipo_conexion": "NO CONMUTADA",
                    "tipo_reclamo": incidencia_seleccionada.split(": ")[1],
                    "permisionario": client.permisionario
                }
                
                # Mostrar campos automáticos
                st.write("### Información automática")
                for key, value in data_tiempro.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                # Campos editables
                st.write("### Información requerida")
                item = st.text_input("Item", key=f"item_{client_id}")
                canal_reclamo = st.selectbox(
                    "Canal de Reclamo", 
                    ["PERSONALIZADO", "TELEFÓNICO", "OFICIO", "CORREO ELECTRÓNICO", "PÁGINA WEB"],
                    key=f"canal_reclamo_{client_id}"
                )
                fecha_hora_solucion = st.date_input("Fecha Hora Solución", key=f"fecha_solucion_{client_id}")
                tiempo_resolucion_horas = st.number_input(
                    "Tiempo de Resolución en Horas", 
                    min_value=0.0, 
                    format="%.2f",
                    key=f"tiempo_resolucion_{client_id}"
                )
                descripcion_solucion = st.text_area("Descripción de la Solución", key=f"descripcion_{client_id}")

                # Actualizar data_tiempro con los campos editables
                data_tiempro.update({
                    "canal_reclamo": canal_reclamo,
                    "fecha_hora_solucion": fecha_hora_solucion,
                    "tiempo_resolucion_horas": tiempo_resolucion_horas,
                    "descripcion_solucion": descripcion_solucion
                })

                # Botón de envío del formulario
                submitted = st.form_submit_button("Registrar Incidencia")
                if submitted:
                    # Obtener el siguiente número de ítem
                    db = next(get_db())
                    nuevo_item = obtener_ultimo_item(db, client.permisionario)
                    
                    # Actualizar data_tiempro con todos los campos
                    data_tiempro.update({
                        "item": nuevo_item,
                        "canal_reclamo": canal_reclamo,
                        "fecha_hora_solucion": fecha_hora_solucion,
                        "tiempo_resolucion_horas": tiempo_resolucion_horas,
                        "descripcion_solucion": descripcion_solucion
                    })

                    if registrar_tiempro(data_tiempro):
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
                        
                    else:
                        st.error("Error al registrar la incidencia.")
                    
                    db.close()

            return incidencia_seleccionada


# Función del dashboard
def dashboard(permisionario):
    st.header("Dashboard")
    
    # Campo de búsqueda para cliente o cédula
    search_term = st.text_input("Buscar por cliente o cédula")
    
    # Obtener todos los clientes asociados al permisionario
    clients = get_clients(permisionario)

    # Filtrar clientes según el término de búsqueda
    filtered_clients = []
    if search_term:
        filtered_clients = [c for c in clients if search_term.lower() in c.nombres.lower() or search_term.lower() in c.cedula_ruc.lower()]

    # Mostrar métricas generales si no hay búsqueda activa
    if not search_term:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Clientes", len(clients))
        with col2:
            activos = len([c for c in clients if c.estado == "ACTIVO"])
            st.metric("Clientes Activos", activos)
        with col3:
            inactivos = len([c for c in clients if c.estado == "INACTIVO"])
            st.metric("Clientes Inactivos", inactivos)
        
        # Preparar datos para el DataFrame
        data = []
        for client in clients:
            data.append({
                "ID": client.id,
                "Nombres": client.nombres,
                "Apellidos": client.apellidos,
                "Email": client.correo,
                "Teléfono": client.telefono,
                "Estado": client.estado
            })
        
        # Crear DataFrame y mostrarlo
        df = pd.DataFrame(data)
        st.dataframe(df)
        
    else:
        # Mostrar detalles del cliente con acciones solo si se realiza una búsqueda
        if filtered_clients:
            for client in filtered_clients:
                st.write("---")
                st.write(f"**Cliente:** {client.nombres} {client.apellidos}")
                st.write(f"**Email:** {client.correo}")
                st.write(f"**Teléfono:** {client.telefono}")
                st.write(f"**Estado actual:** {client.estado}")

                # Columnas para botones de acción
                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    # Botón para editar el cliente
                    if st.button("Editar", key=f"edit_{client.id}"):
                        st.session_state['cliente_a_editar'] = client.id  # Guardar el ID del cliente en la sesión
                        st.session_state['navegar_a_gestion'] = True  # Indicador para navegar a Gestión de Clientes
                        st.rerun()

                with col2:
                    # Botón para cambiar el estado
                    nuevo_estado = "INACTIVO" if client.estado == "ACTIVO" else "ACTIVO"
                    if st.button(f"Cambiar a {nuevo_estado}", key=f"change_state_{client.id}"):
                        if update_client_status(client.id, nuevo_estado):
                            st.success(f"Estado cambiado a {nuevo_estado} exitosamente!")
                            st.rerun()

                with col3:
                    if st.button("Incidencia", key=f"incidencia_{client.id}"):
                        # Inicializar o resetear el estado cuando se presiona el botón
                        st.session_state[f'incidencia_state_{client.id}'] = {
                            'incidencia_seleccionada': "Selecciona una incidencia",
                            'mostrar_formulario': True
                        }
                        st.rerun()

                # Mostrar el formulario de incidencia si está activo
                if st.session_state.get(f'incidencia_state_{client.id}', {}).get('mostrar_formulario', False):
                    mostrar_opciones_incidencia(client.id)
        else:
            st.info("No se encontraron clientes con el criterio de búsqueda")

#Funciones para seleccion de provincia
def get_provincias(db):
    db = next(get_db())
    return [p[0] for p in db.query(distinct(Localidad.provincia)).order_by(Localidad.provincia).all()]

def get_cantones(db, provincia):
    db = next(get_db())
    return [c[0] for c in db.query(distinct(Localidad.canton)).filter(Localidad.provincia == provincia).order_by(Localidad.canton).all()]



# Función para la gestión de clientes
def client_management():
    st.header("Gestión de Clientes")
    
    # Obtener la sesión de la base de datos
    db = next(get_db())
    
    # Obtener la lista de provincias
    provincias = get_provincias(db)
    
    # Mantener la provincia seleccionada en session_state para detectar cambios
    if "provincia_seleccionada" not in st.session_state:
        st.session_state.provincia_seleccionada = provincias[0]  # Valor inicial
    
    # Selector de provincia con callback para actualizar cantones
    provincia_seleccionada = st.selectbox("Provincia", options=provincias, key="provincia_select")
    
    # Detectar si la provincia ha cambiado
    if provincia_seleccionada != st.session_state.provincia_seleccionada:
        st.session_state.provincia_seleccionada = provincia_seleccionada
        # Actualizar la lista de cantones cuando cambie la provincia
        st.session_state.cantones = get_cantones(db, provincia_seleccionada)
    
    # Cargar cantones de la provincia seleccionada en session_state si no existen
    if "cantones" not in st.session_state:
        st.session_state.cantones = get_cantones(db, provincia_seleccionada)
    
    with st.form("nuevo_cliente"):
        # Mostrar permisionario
        permisionario = st.session_state.get('permisionario', 'Sin permisionario')
        st.text_input("Permisionario", value=permisionario, disabled=True)
        
        # Mostrar la provincia seleccionada (solo lectura en el formulario)
        st.text_input("Provincia", value=provincia_seleccionada, disabled=True)

        # Selección de cantón usando la lista en session_state
        canton_seleccionado = st.selectbox("Ciudad", options=st.session_state.cantones, key="canton")

        # Otros datos del cliente
        client_data = {
            "permisionario": permisionario,
            "codigo": st.text_input("Código"),
            "nombres": st.text_input("Nombres"),
            "apellidos": st.text_input("Apellidos"),
            "cliente": st.text_input("Cliente"),
            "cedula_ruc": st.text_input("Cédula/RUC"),
            "servicio_contratado": st.selectbox("Servicio Contratado", ["INTERNET", "TV", "INTERNET+TV"]),
            "plan_contratado": st.text_input("Plan Contratado"),
            "provincia": provincia_seleccionada,
            "ciudad": canton_seleccionado,
            "direccion": st.text_input("Dirección"),
            "telefono": st.text_input("Teléfono"),
            "correo": st.text_input("Correo"),
            "fecha_de_inscripcion": st.date_input("Fecha de Inscripción").strftime("%Y-%m-%d"),
            "estado": st.selectbox("Estado", ["ACTIVO", "INACTIVO"])
        }
        
        # Botón para guardar el cliente y feedback
        submitted = st.form_submit_button("Guardar Cliente")
        if submitted and create_client(client_data):
            st.success("Cliente creado exitosamente!")
            st.rerun()

def search_clients(permisionario):
    st.header("Buscar Clientes")
    search_term = st.text_input("Buscar por nombre o correo")
    if search_term:
        db = next(get_db())  # Use next() to get the session from the generator
        try:
            results = db.query(Client).filter(
                (Client.permisionario == permisionario) &
                ((Client.nombres.ilike(f"%{search_term}%")) |
                 (Client.correo.ilike(f"%{search_term}%")))
            ).all()
            if results:
                for client in results:
                    with st.expander(f"{client.nombres} {client.apellidos}"):
                        st.write(f"**Email:** {client.correo}")
                        st.write(f"**Teléfono:** {client.telefono}")
                        st.write(f"**Estado:** {client.estado}")
                        if st.button("Eliminar", key=f"del_{client.id}") and delete_client(client.id):
                            st.success("Cliente eliminado exitosamente!")
                            st.rerun()
            else:
                st.info("No se encontraron resultados")
        finally:
            db.close()

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

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Incidencias", total_incidencias)
        with col2:
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
                "Descripción Solución": inc.descripcion_solucion,
                "Estado": "Resuelto" if inc.fecha_hora_solucion else "Pendiente"
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

        # Mostrar DataFrame filtrado
        st.subheader("Registro de Incidencias")
        st.dataframe(df_filtrado)

        # Opción para descargar los datos
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar datos como CSV",
            data=csv,
            file_name=f'incidencias_{permisionario}.csv',
            mime='text/csv',
        )

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



# Función principal
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_form()
    else:
        permisionario = st.session_state.get('permisionario')
        st.sidebar.title("Menú")
        menu = st.sidebar.selectbox("Menú", ["Dashboard", "Gestión de Clientes", "Incidencias"])
        
        if st.sidebar.button("Cerrar Sesión"):
            logout()
                    
        if menu == "Dashboard":
            dashboard(permisionario)
        elif menu == "Gestión de Clientes":
            client_management()
        elif menu == "Incidencias":
            incidencias(permisionario)

if __name__ == "__main__":
    main()