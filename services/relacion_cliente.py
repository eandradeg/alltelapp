import streamlit as st
import pywhatkit as pwk
import time
from models import Client
from database import get_db


# Función para obtener y formatear la lista de contactos
def get_and_format_contacts():
    db = next(get_db())
    try:
        contacts = db.query(Client.telefono).all()
        formatted_contacts = []
        for contact in contacts:
            # Asegúrate de que el número no esté vacío y tenga 10 dígitos
            number = contact.telefono.strip()
            if number and len(number) == 10 and number.startswith('0'):
                # Eliminar el cero inicial y agregar el prefijo +593
                formatted_number = '+593' + number[1:]
                formatted_contacts.append(formatted_number)
        return formatted_contacts
    finally:
        db.close()

# Función para enviar mensajes a través de WhatsApp
def send_message(contact, message):
    try:
        pwk.sendwhatmsg_instantly(contact, message, wait_time=10, tab_close=True, close_time=3)
        time.sleep(2)  # Pausa entre envíos
        return f"Mensaje enviado a {contact}"
    except Exception as e:
        return f"Error al enviar mensaje a {contact}: {e}"



# Interfaz en Streamlit
def enviar_encuesta():
    st.title("Envío de encuesta por WhatsApp")

    # Obtener y mostrar los contactos formateados
    contacts = get_and_format_contacts()
    st.write("Contactos formateados:")

    selected_contacts = []
    
    # Crear checkboxes para cada contacto con un key único
    for i, contact in enumerate(contacts):
        if st.checkbox(f"Enviar a {contact}", key=f"checkbox_{i}"):  # Usar un key único
            selected_contacts.append(contact)

    # Campo para el enlace de Google Forms
    google_form_link = "https://docs.google.com/forms/d/1Bj0ALE6lgDo0jK9GGgfvcuvNz9Egw9CB6k62Tgx6NnQ/prefill"

    if google_form_link:
        message = f"¡Hola! Te invitamos a llenar nuestra encuesta en el siguiente enlace: {google_form_link}"

        # Botón para enviar los mensajes con un icono de WhatsApp
        if st.button("Enviar mensajes 📲"):
            results = []
            for contact in selected_contacts:
                result = send_message(contact, message)
                results.append(result)
            
            # Mostrar resultados
            st.write("Resultados del envío:")
            for res in results:
                st.write(res)
    else:
        st.warning("Por favor, proporciona el enlace de Google Forms.")
