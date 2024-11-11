import streamlit as st
import hashlib

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

