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
    PRESENTE = "presente"
    AUSENTE = "ausente"
    ESTAFA = "estafa"


class EtiquetaCodigo(StrEnum):
    INT = "INT"
    F = "F"
    CORTO = "CORTO"
    LAVADO = "LAVADO"
    AC = "AC"
    TC = "TC"
    XL = "XL"
    CM = "CM"
    DC = "DC"


ETIQUETA_LABELS = {
    EtiquetaCodigo.INT: "Interno",
    EtiquetaCodigo.F: "Cabello fuerte",
    EtiquetaCodigo.CORTO: "Cabello corto",
    EtiquetaCodigo.LAVADO: "Cabello limpio",
    EtiquetaCodigo.AC: "Asesoría de color",
    EtiquetaCodigo.TC: "Trabajo de color",
    EtiquetaCodigo.XL: "Cabello largo",
    EtiquetaCodigo.CM: "Cabello maltratado",
    EtiquetaCodigo.DC: "Diseño de corte",
}
