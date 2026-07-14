"""
Rutas de eventos: CRUD de eventos y consulta de speakers/certificados relacionados.

Todas las rutas requieren rol 'admin'.
"""

import logging
from flask import Blueprint, request, jsonify
from routes.auth import admin_required
from services import event_service

logger = logging.getLogger(__name__)

events_bp = Blueprint("events", __name__, url_prefix="/api/events")


@events_bp.route("/", methods=["GET"])
@admin_required
def list_events():
    """
    Lista todos los eventos.

    Requiere header: Authorization: Bearer <token> (admin)

    Respuesta:
        {
            "events": [...],
            "total": N
        }
    """
    try:
        events = event_service.get_all_events()
        return jsonify({
            "events": events,
            "total": len(events),
        }), 200
    except Exception as e:
        logger.error(f"Error listando eventos: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/", methods=["POST"])
@admin_required
def create_event():
    """
    Crea un nuevo evento.

    Requiere header: Authorization: Bearer <token> (admin)

    Body JSON esperado:
        {
            "nombre": "Conferencia 2025",
            "descripcion": "Descripción del evento",
            "fecha": "2025-06-15",
            "color_primario": "#1a3a5c",
            "color_secundario": "#c8a45a"
        }

    Los colores son opcionales (valores por defecto si no se envían).
    El campo 'creado_por' se toma automáticamente del token del usuario.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        nombre = data.get("nombre", "")
        descripcion = data.get("descripcion", "")
        fecha = data.get("fecha", "")
        color_primario = data.get("color_primario", "#1a3a5c")
        color_secundario = data.get("color_secundario", "#c8a45a")

        if not nombre or not nombre.strip():
            return jsonify({"error": "El nombre del evento es obligatorio"}), 400
        if not fecha or not fecha.strip():
            return jsonify({"error": "La fecha del evento es obligatoria"}), 400

        creado_por = request.user["email"]
        event = event_service.create_event(
            nombre, descripcion, fecha,
            color_primario, color_secundario, creado_por,
        )
        logger.info(f"Evento creado: ID={event['id']} por {creado_por}")
        return jsonify({
            "message": "Evento creado exitosamente",
            "event": event,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creando evento: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/<int:event_id>", methods=["GET"])
@admin_required
def get_event(event_id):
    """
    Obtiene un evento específico con su lista de speakers.

    Los datos de firma_base64 se excluyen de la respuesta.

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        result = event_service.get_event_with_speakers(event_id)
        if not result:
            return jsonify({"error": f"Evento {event_id} no encontrado"}), 404
        return jsonify({"event": result}), 200
    except Exception as e:
        logger.error(f"Error obteniendo evento {event_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/<int:event_id>", methods=["PUT"])
@admin_required
def update_event(event_id):
    """
    Actualiza campos de un evento existente.

    Body JSON (todos los campos son opcionales):
        {
            "nombre": "Nuevo nombre",
            "descripcion": "Nueva descripción",
            "fecha": "2025-07-20",
            "color_primario": "#2a4a6c",
            "color_secundario": "#d8b46a",
            "activo": true
        }

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo debe ser JSON"}), 400

        event = event_service.update_event(event_id, **data)
        if not event:
            return jsonify({"error": f"Evento {event_id} no encontrado"}), 404

        logger.info(f"Evento {event_id} actualizado")
        return jsonify({
            "message": "Evento actualizado",
            "event": event,
        }), 200

    except Exception as e:
        logger.error(f"Error actualizando evento {event_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    """
    Elimina un evento.

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        success = event_service.delete_event(event_id)
        if success:
            logger.info(f"Evento {event_id} eliminado")
            return jsonify({"message": f"Evento {event_id} eliminado correctamente"}), 200
        return jsonify({"error": f"Evento {event_id} no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error eliminando evento {event_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/<int:event_id>/certificates", methods=["GET"])
@admin_required
def get_event_certificates(event_id):
    """
    Obtiene todos los certificados asociados a un evento.

    Requiere header: Authorization: Bearer <token> (admin)

    Respuesta:
        {
            "event_id": 1,
            "certificates": [...],
            "total": N
        }
    """
    try:
        event = event_service.get_event(event_id)
        if not event:
            return jsonify({"error": f"Evento {event_id} no encontrado"}), 404

        certificates = event_service.get_certificates_by_event(event_id)
        return jsonify({
            "event_id": event_id,
            "certificates": certificates,
            "total": len(certificates),
        }), 200

    except Exception as e:
        logger.error(f"Error obteniendo certificados del evento {event_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@events_bp.route("/<int:event_id>/speakers", methods=["GET"])
@admin_required
def get_event_speakers(event_id):
    """
    Obtiene todos los speakers de un evento.

    Los datos de firma_base64 se excluyen de la respuesta.

    Requiere header: Authorization: Bearer <token> (admin)

    Respuesta:
        {
            "event_id": 1,
            "speakers": [...],
            "total": N
        }
    """
    try:
        event = event_service.get_event(event_id)
        if not event:
            return jsonify({"error": f"Evento {event_id} no encontrado"}), 404

        speakers = event_service.get_speakers_by_event(event_id)
        event_service._strip_signatures(speakers)
        return jsonify({
            "event_id": event_id,
            "speakers": speakers,
            "total": len(speakers),
        }), 200

    except Exception as e:
        logger.error(f"Error obteniendo speakers del evento {event_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500