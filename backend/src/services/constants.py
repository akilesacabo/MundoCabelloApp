"""Áreas del salón. `key` es la identidad estable (usada en URLs, DB y FE)."""

from enum import StrEnum


class AreaKey(StrEnum):
    PELUQUERIA = "peluqueria"
    HIDRATACION = "hidratacion"
    MANICURE = "manicure"
    CEJAS = "cejas"
    MAQUILLAJE = "maquillaje"
