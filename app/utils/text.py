import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize text for deduplication and matching:
    - Convert to uppercase
    - Remove accents/diacritics
    - Collapse multiple spaces to single space
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    # Convert to uppercase
    text = text.upper()

    # Remove accents using NFD normalization
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Strip
    return text.strip()
