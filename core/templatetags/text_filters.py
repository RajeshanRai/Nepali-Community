from django import template

register = template.Library()

_MOJIBAKE_HINTS = ("â", "Ã", "Â")
_FALLBACK_MAP = {
    "â€œ": '"',
    "â€": '"',
    "â€™": "'",
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "Â": "",
}


@register.filter(name="fix_mojibake")
def fix_mojibake(value):
    if not isinstance(value, str) or not value:
        return value

    cleaned = value

    # Common mojibake often comes from UTF-8 bytes read as Windows-1252.
    if any(hint in cleaned for hint in _MOJIBAKE_HINTS):
        try:
            repaired = cleaned.encode("cp1252").decode("utf-8")
            if repaired:
                cleaned = repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    for bad, good in _FALLBACK_MAP.items():
        cleaned = cleaned.replace(bad, good)

    return cleaned
