from enum import StrEnum


class ManualStatus(StrEnum):
    """Estado manual elegido desde el panel."""

    DISPONIBLE = "disponible"
    OCUPADO = "ocupado"
    BREAK = "break"


class EffectiveStatus(StrEnum):
    """Estado efectivo expuesto al frontend."""

    DISPONIBLE = "disponible"
    OCUPADO = "ocupado"
    BREAK = "break"
