import enum


class Category(str, enum.Enum):
    HOGAR = "HOGAR"
    DOMICILIOS = "DOMICILIOS"
    CARRO = "CARRO"
    TRANSPORTE = "TRANSPORTE"
    OCIO = "OCIO"
    RESTAURANTES = "RESTAURANTES"
    ROPA = "ROPA"
    SALUD = "SALUD"
    PRESTACIONES = "PRESTACIONES"
    REGALOS = "REGALOS"
    EDUCACION = "EDUCACION"
    TRABAJO = "TRABAJO"
    COBRO_BANCARIO = "COBRO_BANCARIO"
    PAGO = "PAGO"
    OTROS = "OTROS"


class CategoryMethod(str, enum.Enum):
    RULES = "RULES"
    LLM = "LLM"
    USER = "USER"
