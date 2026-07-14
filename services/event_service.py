"""
Servicio de eventos y speakers: capa de lógica de negocio.

Encapsula las llamadas a Google Sheets para eventos, speakers y
relaciones con certificados, con manejo centralizado de errores.
"""

import logging
from models.google_sheets import db

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
#  EVENTOS
# ════════════════════════════════════════════════════════════

def get_all_events() -> list[dict]:
    """Obtiene todos los eventos."""
    return db.get_all_events()


def get_event(event_id: int) -> dict | None:
    """Obtiene un evento por su ID. Devuelve None si no existe."""
    return db.get_event_by_id(event_id)


def create_event(nombre: str, descripcion: str, fecha: str,
                 color_primario: str, color_secundario: str,
                 creado_por: str) -> dict:
    """
    Crea un nuevo evento.

    Args:
        nombre: Nombre del evento.
        descripcion: Descripción del evento.
        fecha: Fecha del evento (formato YYYY-MM-DD).
        color_primario: Color primario en formato hexadecimal (#RRGGBB).
        color_secundario: Color secundario en formato hexadecimal (#RRGGBB).
        creado_por: Email del administrador que crea el evento.

    Returns:
        Diccionario con los datos del evento creado.

    Raises:
        ValueError: Si faltan campos obligatorios.
    """
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del evento es obligatorio")
    if not fecha or not fecha.strip():
        raise ValueError("La fecha del evento es obligatoria")

    return db.create_event(
        nombre.strip(),
        descripcion.strip() if descripcion else "",
        fecha.strip(),
        color_primario.strip() if color_primario else "#1a3a5c",
        color_secundario.strip() if color_secundario else "#c8a45a",
        creado_por,
    )


def update_event(event_id: int, **kwargs) -> dict | None:
    """
    Actualiza campos de un evento existente.

    Returns:
        Diccionario actualizado o None si no existe.
    """
    return db.update_event(event_id, **kwargs)


def delete_event(event_id: int) -> bool:
    """
    Elimina un evento.

    Returns:
        True si se eliminó correctamente, False si no se encontró.
    """
    return db.delete_event(event_id)


# ════════════════════════════════════════════════════════════
#  SPEAKERS
# ════════════════════════════════════════════════════════════

def get_all_speakers(include_signature: bool = False) -> list[dict]:
    """
    Obtiene todos los speakers.

    Args:
        include_signature: Si es False, se elimina firma_base64 de la respuesta.
    """
    speakers = db.get_all_speakers()
    if not include_signature:
        _strip_signatures(speakers)
    return speakers


def get_speaker(speaker_id: int) -> dict | None:
    """Obtiene un speaker por su ID."""
    return db.get_speaker_by_id(speaker_id)


def get_speakers_by_event(evento_id: int) -> list[dict]:
    """Obtiene los speakers de un evento específico."""
    return db.get_speakers_by_event(evento_id)


def create_speaker(nombre: str, cargo: str, email: str,
                   evento_id: int) -> dict:
    """
    Crea un nuevo speaker.

    Args:
        nombre: Nombre del speaker.
        cargo: Cargo del speaker.
        email: Email del speaker.
        evento_id: ID del evento al que pertenece.

    Returns:
        Diccionario con los datos del speaker creado.

    Raises:
        ValueError: Si faltan campos obligatorios.
    """
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del speaker es obligatorio")
    if not evento_id:
        raise ValueError("El evento_id es obligatorio")

    return db.create_speaker(
        nombre.strip(),
        cargo.strip() if cargo else "",
        email.strip().lower() if email else "",
        evento_id,
    )


def update_speaker(speaker_id: int, **kwargs) -> dict | None:
    """
    Actualiza campos de un speaker existente.

    Returns:
        Diccionario actualizado o None si no existe.
    """
    return db.update_speaker(speaker_id, **kwargs)


def delete_speaker(speaker_id: int) -> bool:
    """
    Elimina un speaker.

    Returns:
        True si se eliminó correctamente, False si no se encontró.
    """
    return db.delete_speaker(speaker_id)


def save_signature(speaker_id: int, firma_data_url: str) -> dict:
    """
    Guarda la firma de un speaker extrayendo los datos base64 de la data URL.

    Args:
        speaker_id: ID del speaker.
        firma_data_url: Data URL completa (data:image/png;base64,...).

    Returns:
        Diccionario con el resultado de la operación.

    Raises:
        ValueError: Si el speaker no existe o el formato de firma es inválido.
    """
    speaker = db.get_speaker_by_id(speaker_id)
    if not speaker:
        raise ValueError(f"Speaker con ID {speaker_id} no encontrado")

    if not firma_data_url or "," not in firma_data_url:
        raise ValueError("Formato de firma inválido. Se espera data:image/...;base64,...")

    # Extraer solo la parte base64 después de la coma
    base64_data = firma_data_url.split(",", 1)[1]

    if not base64_data.strip():
        raise ValueError("Los datos de la firma están vacíos")

    success = db.save_speaker_signature(speaker_id, base64_data)
    if success:
        logger.info(f"Firma guardada para speaker {speaker_id}")
        return {"message": "Firma guardada correctamente", "speaker_id": speaker_id}
    else:
        raise ValueError(f"No se pudo guardar la firma para el speaker {speaker_id}")


# ════════════════════════════════════════════════════════════
#  CONSULTAS COMPUESTAS
# ════════════════════════════════════════════════════════════

def get_event_with_speakers(event_id: int) -> dict | None:
    """
    Obtiene un evento junto con su lista de speakers.

    Se excluye firma_base64 de la respuesta para optimizar el tamaño.

    Args:
        event_id: ID del evento.

    Returns:
        Diccionario con los datos del evento y la lista de speakers,
        o None si el evento no existe.
    """
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            logger.warning(f"Evento {event_id} no encontrado")
            return None

        speakers = db.get_speakers_by_event(event_id)
        _strip_signatures(speakers)

        event["speakers"] = speakers
        return event

    except Exception as e:
        logger.error(f"Error obteniendo evento {event_id} con speakers: {e}")
        raise


def get_event_with_certificates(event_id: int) -> dict | None:
    """
    Obtiene un evento junto con su lista de certificados.

    Args:
        event_id: ID del evento.

    Returns:
        Diccionario con los datos del evento y la lista de certificados,
        o None si el evento no existe.
    """
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            logger.warning(f"Evento {event_id} no encontrado")
            return None

        certificates = db.get_certificates_by_event(event_id)

        event["certificates"] = certificates
        return event

    except Exception as e:
        logger.error(f"Error obteniendo evento {event_id} con certificados: {e}")
        raise


def get_certificates_by_event(event_id: int) -> list[dict]:
    """Obtiene todos los certificados de un evento."""
    return db.get_certificates_by_event(event_id)


# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════

def _strip_signatures(speakers: list[dict]) -> None:
    """Elimina el campo firma_base64 de cada speaker en la lista (in-place)."""
    for speaker in speakers:
        speaker.pop("firma_base64", None)