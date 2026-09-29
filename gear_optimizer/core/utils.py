"""
Utility functions and helpers for the gear optimizer.
Pure functions with no external dependencies.
"""


def safe_int(val, default=0):
    """
    Safely convert a value to an integer with fallback.

    Args:
        val: Value to convert (str, int, float, or None)
        default: Default value if conversion fails

    Returns:
        int: Converted integer or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 999)
        999
        >>> safe_int(None, 0)
        0
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except (TypeError, ValueError, OverflowError):
        return default


def require_int(value, *, field):
    """Fail-loud int coercion for internal / authoritative state (issue #56 B3).

    Unlike `safe_int`, this RAISES instead of returning a default, so a bad value on an
    internal invariant or an authoritative persistence field is surfaced loudly rather
    than silently masked. Use it on internal authority paths; use `safe_int` at external
    boundaries (config, malformed user/DB input, display).
    """
    try:
        return int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {field}: {value!r}") from exc


def safe_float(val, default=0.0):
    """
    Safely convert a value to a float with fallback.

    Args:
        val: Value to convert
        default: Default value if conversion fails

    Returns:
        float: Converted float or default

    Examples:
        >>> safe_float("3.14")
        3.14
        >>> safe_float("-")
        0.0
    """
    try:
        if not val or val == "-":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def get_selected_element(data: object, default: str = "") -> str:
    """
    Normalize the "selected element" field across historical key spellings.

    Runtime payloads typically use "Selected Element" while persisted details
    commonly use "SelectedElement". This helper reads either form.
    """
    if not isinstance(data, dict):
        return str(default or "")

    v = data.get("Selected Element")
    if not v:
        v = data.get("SelectedElement")
    if not v:
        v = default
    return str(v or "")
