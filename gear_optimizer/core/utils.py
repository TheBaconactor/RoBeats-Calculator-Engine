"""
Utility functions and helpers for the gear optimizer (standard library only).
"""


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
