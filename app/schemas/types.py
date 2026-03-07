from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Decimal que se serializa como número JSON (float) en lugar de string.
DecimalAsFloat = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
