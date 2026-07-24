from enum import StrEnum


class ServicioEstado(StrEnum):
    PENDIENTE = "pendiente"
    EN_ATENCION = "en_atencion"
    FINALIZADO = "finalizado"


class TurnoEstado(StrEnum):
    """Estado del turno completo, derivado de sus servicios."""

    EN_ESPERA = "en_espera"
    EN_ATENCION = "en_atencion"
    FINALIZADO = "finalizado"


class SituacionTurno(StrEnum):
    NORMAL = "normal"
    AUSENTE = "ausente"
    ESTAFA = "estafa"
