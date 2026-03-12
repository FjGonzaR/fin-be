from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Decimal que se serializa como número JSON (float) en lugar de string.
DecimalAsFloat = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

# date que se serializa como "YYYY-MM-DDT00:00:00" (sin timezone) para evitar
# que JavaScript lo interprete como UTC midnight y muestre el día anterior.
DateAsLocalISO = Annotated[date, PlainSerializer(lambda d: d.strftime("%Y-%m-%dT00:00:00"), return_type=str, when_used="json")]
