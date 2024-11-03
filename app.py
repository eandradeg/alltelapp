import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
from database import get_db
from models import Client, Localidad
from sqlalchemy import distinct


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
                st.experimental_rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

# Función de logout
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()

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

# Función del dashboard
def dashboard(permisionario):
    st.header("Dashboard")
    clients = get_clients(permisionario)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Clientes", len(clients))
    with col2:
        activos = len([c for c in clients if c.estado == "ACTIVO"])
        st.metric("Clientes Activos", activos)
    with col3:
        inactivos = len([c for c in clients if c.estado == "INACTIVO"])
        st.metric("Clientes Inactivos", inactivos)
    if clients:
        df = pd.DataFrame([{ 
            "ID": c.id, 
            "Nombres": c.nombres, 
            "Apellidos": c.apellidos, 
            "Email": c.correo, 
            "Teléfono": c.telefono, 
            "Estado": c.estado 
        } for c in clients])
        st.dataframe(df)

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
            st.experimental_rerun()

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
                            st.experimental_rerun()
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
        menu = st.sidebar.selectbox("Menú", ["Dashboard", "Gestión de Clientes", "Buscar Clientes"])
        
        if st.sidebar.button("Cerrar Sesión"):
            logout()
                    
        if menu == "Dashboard":
            dashboard(permisionario)
        elif menu == "Gestión de Clientes":
            client_management()
        elif menu == "Buscar Clientes":
            search_clients(permisionario)

if __name__ == "__main__":
    main()