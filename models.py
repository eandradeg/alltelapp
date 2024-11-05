from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric
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

class TiemPro(Base):
    __tablename__ = 'tiem_pro'
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(50))
    provincia = Column(String(100))
    mes = Column(String(20))
    fecha_hora_registro = Column(DateTime)
    nombre_reclamante = Column(String(200))
    telefono_contacto = Column(String(20))
    tipo_conexion = Column(String(20))
    canal_reclamo = Column(String(50))
    tipo_reclamo = Column(String(100))
    fecha_hora_solucion = Column(DateTime)
    tiempo_resolucion_horas = Column(Numeric)
    descripcion_solucion = Column(Text)
    permisionario = Column(String(200))


class Localidad(Base):
    __tablename__ = "dpa"
    cod_provincia=Column(Integer, primary_key=True, index=True)          
    cod_canton=Column(Integer)   
    cod_parroquia=Column(Integer)             
    provincia = Column(String)
    canton = Column(String)
    parroquia = Column(String)
