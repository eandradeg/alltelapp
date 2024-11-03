from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    permisionario = Column(String)
    codigo = Column(String)
    nombres = Column(String)
    apellidos = Column(String)
    cliente = Column(String)
    cedula_ruc = Column(String)
    servicio_contratado = Column(String)
    plan_contratado = Column(String)
    provincia = Column(String)
    ciudad = Column(String)
    direccion = Column(String)
    telefono = Column(String)
    correo = Column(String, unique=True, index=True)
    fecha_de_inscripcion = Column(String)
    estado = Column(String)


class Localidad(Base):
    __tablename__ = "dpa"
    cod_provincia=Column(Integer, primary_key=True, index=True)          
    cod_canton=Column(Integer)   
    cod_parroquia=Column(Integer)             
    provincia = Column(String)
    canton = Column(String)
    parroquia = Column(String)
