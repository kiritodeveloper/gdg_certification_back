"""
Rutas de speakers: CRUD de speakers y gestión de firmas.

Todas las rutas requieren rol 'admin'.
"""

import logging
from flask import Blueprint, request, jsonify
from routes.auth import admin_required
from services import event_service

logger = logging.getLogger(__name__)

speakers_bp = Blueprint("speakers", __name__, url_prefix="/api/speakers")


@speakers_bp.route("/", methods=["GET"])
@admin_required
def list_speakers():
    """
    Lista todos los speakers.

    Por defecto se excluye firma_base64 de la respuesta.
    Incluye firma si se pasa el query param ?include_signature=true

    Requiere header: Authorization: Bearer <token> (admin)

    Respuesta:
        {
            "speakers": [...],
            "total": N
        }
    """
    try:
        include_sig = request.args.get("include_signature", "false").lower() == "true"
        speakers = event_service.get_all_speakers(include_signature=include_sig)
        return jsonify({
            "speakers": speakers,
            "total": len(speakers),
        }), 200
    except Exception as e:
        logger.error(f"Error listando speakers: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/", methods=["POST"])
@admin_required
def create_speaker():
    """
    Crea un nuevo speaker.

    Requiere header: Authorization: Bearer <token> (admin)

    Body JSON esperado:
        {
            "nombre": "Dr. Juan Pérez",
            "cargo": "Director General",
            "email": "juan@ejemplo.com",
            "evento_id": 1
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        nombre = data.get("nombre", "")
        cargo = data.get("cargo", "")
        email = data.get("email", "")
        evento_id = data.get("evento_id")

        if not nombre or not nombre.strip():
            return jsonify({"error": "El nombre del speaker es obligatorio"}), 400
        if not evento_id:
            return jsonify({"error": "El evento_id es obligatorio"}), 400

        speaker = event_service.create_speaker(nombre, cargo, email, evento_id)
        logger.info(f"Speaker creado: ID={speaker['id']} para evento {evento_id}")
        return jsonify({
            "message": "Speaker creado exitosamente",
            "speaker": speaker,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creando speaker: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/<int:speaker_id>", methods=["GET"])
@admin_required
def get_speaker(speaker_id):
    """
    Obtiene un speaker específico por su ID.

    Incluye todos los campos del speaker.

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        speaker = event_service.get_speaker(speaker_id)
        if not speaker:
            return jsonify({"error": f"Speaker {speaker_id} no encontrado"}), 404
        return jsonify({"speaker": speaker}), 200
    except Exception as e:
        logger.error(f"Error obteniendo speaker {speaker_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/<int:speaker_id>", methods=["PUT"])
@admin_required
def update_speaker(speaker_id):
    """
    Actualiza campos de un speaker existente.

    Body JSON (campos opcionales, solo se actualizan los enviados):
        {
            "nombre": "Nuevo nombre",
            "cargo": "Nuevo cargo",
            "email": "nuevo@email.com"
        }

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo debe ser JSON"}), 400

        # Solo permitir actualizar estos campos
        allowed_fields = ("nombre", "cargo", "email")
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({
                "error": "No se enviaron campos válidos para actualizar. "
                        f"Campos permitidos: {', '.join(allowed_fields)}"
            }), 400

        speaker = event_service.update_speaker(speaker_id, **update_data)
        if not speaker:
            return jsonify({"error": f"Speaker {speaker_id} no encontrado"}), 404

        logger.info(f"Speaker {speaker_id} actualizado")
        return jsonify({
            "message": "Speaker actualizado",
            "speaker": speaker,
        }), 200

    except Exception as e:
        logger.error(f"Error actualizando speaker {speaker_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/<int:speaker_id>", methods=["DELETE"])
@admin_required
def delete_speaker(speaker_id):
    """
    Elimina un speaker.

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        success = event_service.delete_speaker(speaker_id)
        if success:
            logger.info(f"Speaker {speaker_id} eliminado")
            return jsonify({"message": f"Speaker {speaker_id} eliminado correctamente"}), 200
        return jsonify({"error": f"Speaker {speaker_id} no encontrado"}), 404
    except Exception as e:
        logger.error(f"Error eliminando speaker {speaker_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/<int:speaker_id>/signature", methods=["POST"])
@admin_required
def save_signature(speaker_id):
    """
    Guarda la firma de un speaker.

    El body debe contener la firma como data URL completa:
        {
            "firma_base64": "data:image/png;base64,iVBORw0KGgo..."
        }

    El sistema extrae automáticamente la parte base64 de la data URL.

    Requiere header: Authorization: Bearer <token> (admin)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        firma_data_url = data.get("firma_base64", "")
        if not firma_data_url or not firma_data_url.strip():
            return jsonify({"error": "El campo firma_base64 es obligatorio"}), 400

        result = event_service.save_signature(speaker_id, firma_data_url.strip())
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error guardando firma del speaker {speaker_id}: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@speakers_bp.route("/event/<int:event_id>", methods=["GET"])
@admin_required
def get_speakers_by_event(event_id):
    """
    Obtiene todos los speakers de un evento específico (alias).

    Se excluye firma_base64 de la respuesta.

    Requiere header: Authorization: Bearer <token> (admin)

    Respuesta:
        {
            "event_id": 1,
            "speakers": [...],
            "total": N
        }
    """
    try:
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