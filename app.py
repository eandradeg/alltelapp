import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_db
from models import Client, Localidad, TiemPro
from sqlalchemy import distinct
from services.estadisticas import estadisticas
from services.reporteria import reporteria
from services.auth import login_form, logout
from services.incidencias import incidencias, mostrar_opciones_incidencia
from services.relacion_cliente import enviar_encuesta

# Configuración de la página (debe ser la primera instrucción de Streamlit)
st.set_page_config(page_title="Sistema de Gestión de Clientes", layout="wide")

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
                "Cliente": client.cliente,
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
                # Crear una clave única para el estado del cliente actual
                client_key = f'client_state_{client.id}'
                
                # Inicializar el estado del cliente si no existe
                if client_key not in st.session_state:
                    st.session_state[client_key] = {
                        'show_edit': False,
                        'show_incidencia': False
                    }

                # Mostrar información básica del cliente
                st.write("---")
                if not st.session_state[client_key]['show_edit'] and not st.session_state[client_key]['show_incidencia']:
                    st.write(f"**Cliente:** {client.cliente}")
                    st.write(f"**Email:** {client.correo}")
                    st.write(f"**Teléfono:** {client.telefono}")
                    st.write(f"**Estado actual:** {client.estado}")

                    # Columnas para botones de acción
                    col1, col2, col3 = st.columns([1, 1, 1])

                    with col1:
                        # Botón para editar el cliente
                        if st.button("Editar", key=f"edit_{client.id}"):
                            st.session_state[client_key]['show_edit'] = True
                            st.session_state[client_key]['show_incidencia'] = False
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
                            st.session_state[client_key]['show_incidencia'] = True
                            st.session_state[client_key]['show_edit'] = False
                            st.rerun()
                
                # Mostrar formulario de edición si está activado
                if st.session_state[client_key]['show_edit']:
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
                            ),
                            "ip": st.text_input("Ip", value=client.ip)
                        }

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Guardar Cambios"):
                                if update_client(client.id, edited_data):
                                    st.success("Cliente actualizado exitosamente!")
                                    st.session_state[client_key]['show_edit'] = False
                                    st.rerun()
                        with col2:
                            if st.form_submit_button("Cancelar"):
                                st.session_state[client_key]['show_edit'] = False
                                st.rerun()

                # Mostrar formulario de incidencias si está activado
                if st.session_state[client_key]['show_incidencia']:
                    st.write("### Registro de Incidencia")
                    mostrar_opciones_incidencia(client.id)
                    if st.button("Cancelar Incidencia", key=f"cancel_incidencia_{client.id}"):
                        st.session_state[client_key]['show_incidencia'] = False
                        st.rerun()
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

# Función principal
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_form()
    else:
        permisionario = st.session_state.get('permisionario')
        
        st.sidebar.title("Menú")
        menu = st.sidebar.selectbox("Menú", ["Servicio al Cliente", "Gestión de Clientes", "Soporte", "Enviar Encuestas", "Reporteria", "Estadisticas"])
        
        if st.sidebar.button("Cerrar Sesión"):
            logout()
                    
        if menu == "Servicio al Cliente":
            dashboard(permisionario)
        elif menu == "Gestión de Clientes":
            client_management()
        elif menu == "Soporte":
            incidencias(permisionario)
        elif menu == "Enviar Encuestas":
            enviar_encuesta()
        elif menu ==menu == "Reporteria":
            reporteria(permisionario)
        elif menu ==menu == "Estadisticas":
            estadisticas(permisionario)

if __name__ == "__main__":
    main()