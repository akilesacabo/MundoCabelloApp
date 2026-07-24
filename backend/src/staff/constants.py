from enum import StrEnum


class ManualStatus(StrEnum):
    """Estado manual del especialista. OCUPADO es derivado (no se guarda)."""

    DISPONIBLE = "disponible"
    BREAK = "break"


class EffectiveStatus(StrEnum):
    """Estado efectivo expuesto al frontend."""

    DISPONIBLE = "disponible"
    OCUPADO = "ocupado"
    BREAK = "break"
