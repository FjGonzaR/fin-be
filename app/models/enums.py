import enum


class BankEnum(str, enum.Enum):
    BANCOLOMBIA = "BANCOLOMBIA"
    RAPPI = "RAPPI"
    FALABELLA = "FALABELLA"
    NEQUI = "NEQUI"



class AccountTypeEnum(str, enum.Enum):
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"
    AHORROS = "AHORROS"


class CategoryMethod(str, enum.Enum):
    RULES = "RULES"
    LLM = "LLM"
    USER = "USER"
