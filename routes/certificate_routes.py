"""
Rutas de la API para la gestión de certificados.
"""

from flask import Blueprint, request, jsonify, g
from services import certificate_service
from utils.decorators import token_required, admin_required

cert_bp = Blueprint("certificates", __name__, url_prefix="/api/certificates")


@cert_bp.route("/", methods=["POST"])
@admin_required
def create_certificate_route():
    """Crea un nuevo certificado y genera el PDF."""
    data = request.get_json()
    try:
        certificate = certificate_service.create_certificate(
            nombre_completo=data.get("nombre_completo"),
            email=data.get("email"),
            curso=data.get("curso"),
            fecha_emision=data.get("fecha_emision"),
            descripcion=data.get("descripcion"),
            creado_por=g.user["email"],
        )
        return jsonify({"message": "Certificado creado", "certificate": certificate}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@cert_bp.route("/upload", methods=["POST"])
@admin_required
def upload_certificate_route():
    """
    Crea un certificado a partir de un PDF subido.
    El archivo se envía como 'multipart/form-data' con el campo 'file'.
    Los datos del certificado se envían como campos de formulario.
    """
    if "file" not in request.files:
        return jsonify({"error": "No se encontró el archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    data = request.form
    try:
        certificate = certificate_service.register_certificate_from_upload(
            file_storage=file,
            nombre_completo=data.get("nombre_completo"),
            email=data.get("email"),
            curso=data.get("curso"),
            fecha_emision=data.get("fecha_emision"),
            descripcion=data.get("descripcion"),
            creado_por=g.user["email"],
        )
        return jsonify({"message": "Certificado subido y registrado", "certificate": certificate}), 201
    except (ValueError, Exception) as e:
        return jsonify({"error": str(e)}), 400


@cert_bp.route("/", methods=["GET"])
@token_required
def get_all_certificates_route():
    """Obtiene todos los certificados."""
    certificates = certificate_service.get_all_certificates()
    return jsonify(certificates)


@cert_bp.route("/<int:cert_id>", methods=["GET"])
@token_required
def get_certificate_route(cert_id):
    """Obtiene un certificado por ID."""
    certificate = certificate_service.get_certificate(cert_id)
    if certificate:
        return jsonify(certificate)
    return jsonify({"error": "Certificado no encontrado"}), 404


@cert_bp.route("/<int:cert_id>", methods=["PUT"])
@admin_required
def update_certificate_route(cert_id):
    """Actualiza un certificado."""
    data = request.get_json()
    certificate = certificate_service.update_certificate(cert_id, **data)
    if certificate:
        return jsonify({"message": "Certificado actualizado", "certificate": certificate})
    return jsonify({"error": "Certificado no encontrado"}), 404


@cert_bp.route("/<int:cert_id>", methods=["DELETE"])
@admin_required
def delete_certificate_route(cert_id):
    """Elimina un certificado."""
    if certificate_service.delete_certificate(cert_id):
        return jsonify({"message": "Certificado eliminado"})
    return jsonify({"error": "Certificado no encontrado"}), 404


@cert_bp.route("/verify/<code>", methods=["GET"])
def verify_certificate_route(code):
    """Verifica un certificado por código (público)."""
    certificate = certificate_service.verify_certificate(code)
    if certificate:
        return jsonify(certificate)
    return jsonify({"error": "Código de verificación inválido"}), 404


@cert_bp.route("/send/<int:cert_id>", methods=["POST"])
@admin_required
def send_certificate_route(cert_id):
    """Envía un certificado por email."""
    result = certificate_service.send_certificate(cert_id)
    return jsonify(result), 200 if result["success"] else 500


@cert_bp.route("/send-bulk", methods=["POST"])
@admin_required
def send_bulk_certificates_route():
    """Envía múltiples certificados."""
    data = request.get_json()
    cert_ids = data.get("certificate_ids", [])
    result = certificate_service.send_certificate_bulk(cert_ids)
    return jsonify(result)