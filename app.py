import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
from io import BytesIO
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

def update_client(client_id, client_data):
    db = next(get_db())
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            for key, value in client_data.items():
                setattr(client, key, value)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        st.error(f"Error al actualizar cliente: {str(e)}")
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
                    "fecha_hora_registro": datetime.now(),
                    "nombre_reclamante": f"{client.nombres} {client.apellidos}",
                    "telefono_contacto": client.telefono,
                    "tipo_conexion": "NO CONMUTADA",
                    "tipo_reclamo": incidencia_seleccionada.split(": ")[1],
                    "permisionario": client.permisionario,
                    "estado_incidencia": "Pendiente"
                }
                
                # Mostrar campos automáticos
                st.write("### Información automática")
                for key, value in data_tiempro.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                
                # Campos editables
                st.write("### Información requerida")
                
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
    st.header("Servicio al Cliente")
    
    # Campo de búsqueda para cliente o cédula
    search_term = st.text_input("Buscar por cliente o cédula")
    
    # Obtener todos los clientes asociados al permisionario
    clients = get_clients(permisionario)

    # Filtrar clientes según el término de búsqueda
    filtered_clients = []
    if search_term:
        filtered_clients = [c for c in clients if search_term.lower() in c.cliente.lower() or search_term.lower() in c.cedula_ruc.lower()]

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
                "Cliente" : client.cliente,
                "Cédula/RUC": client.cedula_ruc,
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
                st.write(f"**Cliente:** {client.cliente}")
                st.write(f"**Email:** {client.correo}")
                st.write(f"**Teléfono:** {client.telefono}")
                st.write(f"**Estado actual:** {client.estado}")

                # Columnas para botones de acción
                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    # Botón para editar el cliente
                    if st.button("Editar", key=f"edit_{client.id}"):
                        st.session_state[f'edit_mode_{client.id}'] = True
                        st.session_state[f'incidencia_state_{client.id}'] = None  # Resetear estado de incidencia
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
                
                # Mostrar formulario de edición si está en modo edición
                if st.session_state.get(f'edit_mode_{client.id}', False):
                    st.write("### Editar Cliente")
                    with st.form(key=f'edit_form_{client.id}'):
                        # Obtener la sesión de la base de datos
                        db = next(get_db())
                        
                        # Obtener la lista de provincias
                        provincias = get_provincias(db)
                        
                        # Selector de provincia
                        provincia_seleccionada = st.selectbox(
                            "Provincia", 
                            options=provincias,
                            index=provincias.index(client.provincia) if client.provincia in provincias else 0,
                            key=f"provincia_select_{client.id}"
                        )
                        
                        # Obtener cantones para la provincia seleccionada
                        cantones = get_cantones(db, provincia_seleccionada)
                        canton_seleccionado = st.selectbox(
                            "Ciudad",
                            options=cantones,
                            index=cantones.index(client.ciudad) if client.ciudad in cantones else 0,
                            key=f"canton_select_{client.id}"
                        )

                        # Datos editables del cliente
                        edited_data = {
                            "permisionario": st.text_input("Permisionario", value=client.permisionario, disabled=True),
                            "codigo": st.text_input("Código", value=client.codigo),
                            "nombres": st.text_input("Nombres", value=client.nombres),
                            "apellidos": st.text_input("Apellidos", value=client.apellidos),
                            "cliente": st.text_input("Cliente", value=client.cliente),
                            "cedula_ruc": st.text_input("Cédula/RUC", value=client.cedula_ruc),
                            "servicio_contratado": st.selectbox(
                                "Servicio Contratado",
                                ["INTERNET", "TV", "INTERNET+TV"],
                                index=["INTERNET", "TV", "INTERNET+TV"].index(client.servicio_contratado)
                            ),
                            "plan_contratado": st.text_input("Plan Contratado", value=client.plan_contratado),
                            "provincia": provincia_seleccionada,
                            "ciudad": canton_seleccionado,
                            "direccion": st.text_input("Dirección", value=client.direccion),
                            "telefono": st.text_input("Teléfono", value=client.telefono),
                            "correo": st.text_input("Correo", value=client.correo),
                            "fecha_de_inscripcion": st.date_input(
                                "Fecha de Inscripción",
                                value=datetime.strptime(client.fecha_de_inscripcion, '%Y-%m-%d')
                            ).strftime("%Y-%m-%d"),
                            "estado": st.selectbox(
                                "Estado",
                                ["ACTIVO", "INACTIVO"],
                                index=["ACTIVO", "INACTIVO"].index(client.estado)
                            )
                        }

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Guardar Cambios"):
                                if update_client(client.id, edited_data):
                                    st.success("Cliente actualizado exitosamente!")
                                    del st.session_state[f'edit_mode_{client.id}']
                                    st.rerun()
                        with col2:
                            if st.form_submit_button("Cancelar"):
                                del st.session_state[f'edit_mode_{client.id}']
                                st.rerun()

                if (st.session_state.get(f'incidencia_state_{client.id}', {}).get('mostrar_formulario', False) and 
                    not st.session_state.get(f'edit_mode_{client.id}', False)):
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

def obtener_ultimo_codigo(db, permisionario):
    ultimo_cliente = db.query(Client).filter(Client.permisionario == permisionario).order_by(Client.codigo.desc()).first()
    if ultimo_cliente and ultimo_cliente.codigo:  # Verifica que ultimo_cliente no sea None y que codigo no esté vacío
        # Extraer el número del código y convertir a entero
        ultimo_numero = int(ultimo_cliente.codigo[-1])  # Tomar solo el último carácter
        return ultimo_numero + 1  # Incrementar
    return 1  # Si no hay clientes, empezar desde 1

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

         # Obtener el nuevo código
        nuevo_codigo_numero = obtener_ultimo_codigo(db, permisionario)
        print(nuevo_codigo_numero)
        nuevo_codigo = f"{nuevo_codigo_numero:04d}"  # Formato 0000X
        print(nuevo_codigo)
        # Campo para el nombre del cliente
        cliente = st.text_input("Cliente", key="cliente_input")

        # Verificar si el campo "Cliente" está lleno
        if cliente:
            # Si el cliente está ingresado, deshabilitar los campos de nombres y apellidos
            nombres = st.text_input("Nombres", disabled=True, key="nombres_input")
            apellidos = st.text_input("Apellidos", disabled=True, key="apellidos_input")
        else:
            # Si el cliente no está ingresado, permitir la edición de nombres y apellidos
            nombres = st.text_input("Nombres", key="nombres_input_edit")
            apellidos = st.text_input("Apellidos", key="apellidos_input_edit")

        # Combinar nombres y apellidos para el campo "Cliente" si están vacíos
        if not cliente:
            cliente = f"{nombres} {apellidos}".strip()  # Combina nombres y apellidos

        # Otros datos del cliente
        client_data = {
            "permisionario": permisionario,
            "codigo": nuevo_codigo,
            "nombres": nombres,
            "apellidos": apellidos,
            "cliente": cliente,  # Asignar el cliente combinado
            "cedula_ruc": st.text_input("Cédula/RUC"),
            "servicio_contratado": st.selectbox("Servicio Contratado", ["INTERNET", "TV", "INTERNET+TV"]),
            "plan_contratado": st.text_input("Plan Contratado"),
            "provincia": provincia_seleccionada,
            "ciudad": canton_seleccionado,
            "direccion": st.text_input("Dirección"),
            "telefono": st.text_input("Teléfono"),
            "correo": st.text_input("Correo"),
            "fecha_de_inscripcion": st.date_input("Fecha de Inscripción").strftime("%Y-%m-%d"),
            "estado": st.selectbox("Estado", ["ACTIVO", "INACTIVO"]),
            "ip": st.text_input("Ip")
        }
        
        # Campo "Cliente" que se llena automáticamente y se deshabilita
        st.text_input("Cliente", value=cliente, disabled=True)  # Muestra el cliente combinado como solo lectura
        
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
                "Descripción Solución": inc.descripcion_solucion,
                "Estado": inc.estado_incidencia,
                "Ip": inc.estado_incidencia
            } for inc in incidencias
        ])

                # Aplicar filtro de búsqueda si se proporciona un término
        if search_term:
            # Filtra por nombre de reclamante o por número de incidencia (item)
            df_completo = df_completo[
                ((df_completo["Nombre Reclamante"].str.contains(search_term, case=False, na=False)) |
                (df_completo["Item"].astype(str) == search_term)) &
                (df_completo["Estado"] == "Pendiente")
            ]

        # Selección de incidencia y formulario de solución
        if not df_completo.empty:
            item_seleccionado = st.selectbox("Selecciona una incidencia por número de Item para actualizar:", df_completo["Item"].unique())

            if item_seleccionado:
                # Mostrar detalles de la incidencia seleccionada
                incidencia_seleccionada = df_completo[df_completo["Item"] == item_seleccionado].iloc[0]
                st.write("### Detalles de la Incidencia")
                st.write(f"**Cliente:** {incidencia_seleccionada['Nombre Reclamante']}")
                st.write(f"**Tipo de Reclamo:** {incidencia_seleccionada['Tipo Reclamo']}")
                st.write(f"**Fecha de Registro:** {incidencia_seleccionada['Fecha Registro']}")

                # Formulario para la solución
                with st.form(key=f'solucion_form_{item_seleccionado}'):
                    descripcion_solucion = st.text_area("Descripción de la Solución", 
                                                      value=incidencia_seleccionada['Descripción Solución'] if pd.notna(incidencia_seleccionada['Descripción Solución']) else "",
                                                      height=100)
                    col1, col2 = st.columns(2)
                    with col1:
                        submit_solucion = st.form_submit_button("Guardar Solución")
                    with col2:
                        submit_finalizar = st.form_submit_button("Finalizar Incidencia")

                    if submit_solucion or submit_finalizar:
                        # Buscar la incidencia en la base de datos
                        incidencia = db.query(TiemPro).filter(TiemPro.item == item_seleccionado).first()

                        if incidencia:
                            # Actualizar la descripción de la solución
                            incidencia.descripcion_solucion = descripcion_solucion
                            
                            if submit_finalizar:
                                # Actualizar estado y calcular tiempo de resolución
                                incidencia.estado_incidencia = "Finalizado"
                                incidencia.fecha_hora_solucion = datetime.now()
                                tiempo_resolucion = (datetime.now() - incidencia.fecha_hora_registro).total_seconds() / 3600
                                incidencia.tiempo_resolucion_horas = round(tiempo_resolucion, 2)
                                mensaje = "Incidencia finalizada y solución guardada con éxito"
                            else:
                                mensaje = "Solución guardada con éxito"

                            try:
                                db.commit()
                                st.success(mensaje)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar la incidencia: {str(e)}")
                        else:
                            st.error("No se pudo encontrar la incidencia seleccionada")
    
        
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

def reporteria(permisionario):
    st.header("Reportería")
    
    # Obtener datos de incidencias
    db = next(get_db())
    incidencias = db.query(TiemPro).filter(TiemPro.permisionario == permisionario).all()
    
    if not incidencias:
        st.warning("No hay incidencias registradas para mostrar.")
        return
    
    # Crear DataFrame con todas las incidencias
    df_incidencias = pd.DataFrame([
        {
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
        } for inc in incidencias
    ])
    
    # Selector de tipo de reporte
    tipo_reporte = st.selectbox("Seleccione el tipo de reporte", [
        "Todos", 
        "Reclamos Generales", 
        "Reparación de Averías", 
        "Otros"
    ])
    
    # Filtrar por tipo de reporte
    if tipo_reporte != "Todos":
        df_filtrado = df_incidencias[df_incidencias["CATEGORÍA"] == tipo_reporte]
    else:
        df_filtrado = df_incidencias
    
    # Mostrar DataFrame
    st.dataframe(df_filtrado)
    
    # Función para generar Excel con múltiples hojas
    def generar_excel_multihojas(df_principal):
        # Crear un escritor de Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
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


# Función principal
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_form()
    else:
        permisionario = st.session_state.get('permisionario')
        st.sidebar.title("Menú")
        menu = st.sidebar.selectbox("Menú", ["Servicio al Cliente", "Gestión de Clientes", "Soporte", "Reporteria"])
        
        if st.sidebar.button("Cerrar Sesión"):
            logout()
                    
        if menu == "Servicio al Cliente":
            dashboard(permisionario)
        elif menu == "Gestión de Clientes":
            client_management()
        elif menu == "Soporte":
            incidencias(permisionario)
        elif menu ==menu == "Reporteria":
            reporteria(permisionario)

if __name__ == "__main__":
    main()