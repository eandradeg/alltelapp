from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

# Construir la URL de conexión usando los valores de `secrets`
postgresql_info = st.secrets["connections"]["postgresql"]
DATABASE_URL = f"{postgresql_info['dialect']}://{postgresql_info['username']}:{postgresql_info['password']}@{postgresql_info['host']}:{postgresql_info['port']}/{postgresql_info['database']}"

# Crear el motor de la base de datos
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para la creación de modelos
Base = declarative_base()

# Dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
