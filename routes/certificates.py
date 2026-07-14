"""
Rutas de certificados: CRUD, envío individual/masivo, importación Excel y verificación pública.

- Rutas de creación/edición/eliminación: requieren rol 'admin'
- Ruta de envío: requiere rol 'admin' o 'usuario'
- Ruta de verificación: pública (no requiere autenticación)
"""

import logging
from flask import Blueprint, request, jsonify
from routes.auth import token_required, admin_required
from services import certificate_service

logger = logging.getLogger(__name__)

certs_bp = Blueprint("certificates", __name__, url_prefix="/api/certificates")


@certs_bp.route("/", methods=["POST"])
@admin_required
def create():
    """
    Crea un nuevo certificado.

    Requiere rol de administrador.
    Header: Authorization: Bearer <token>

    Body JSON esperado:
        {
            "nombre_completo": "María García",
            "email": "maria@ejemplo.com",
            "evento_id": 1,
            "fecha_emision": "2025-01-15",   // opcional, default: hoy
            "descripcion": "300 horas"        // opcional
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        nombre = data.get("nombre_completo", "").strip()
        email = data.get("email", "").strip().lower()
        evento_id = data.get("evento_id")
        fecha = data.get("fecha_emision", "").strip()
        desc = data.get("descripcion", "").strip()

        if not nombre:
            return jsonify({"error": "nombre_completo es obligatorio"}), 400
        if not email or "@" not in email:
            return jsonify({"error": "email inválido"}), 400
        if not evento_id:
            return jsonify({"error": "evento_id es obligatorio"}), 400

        creado_por = request.user["email"]
        cert = certificate_service.create_certificate(
            nombre, email, evento_id, fecha, desc, creado_por
        )
        return jsonify({
            "message": "Certificado creado exitosamente",
            "certificate": cert,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/", methods=["GET"])
@token_required
def list_all():
    """
    Obtiene todos los certificados.

    Los usuarios normales solo ven sus propios certificados.
    Los administradores ven todos los certificados del sistema.
    """
    try:
        user = request.user
        if user["rol"] == "admin":
            certs = certificate_service.get_all_certificates()
        else:
            certs = certificate_service.get_all_certificates(creado_por=user["email"])

        return jsonify({
            "certificates": certs,
            "total": len(certs),
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/<int:cert_id>", methods=["GET"])
@token_required
def get_one(cert_id):
    """Obtiene un certificado específico por su ID."""
    try:
        cert = certificate_service.get_certificate(cert_id)
        if not cert:
            return jsonify({"error": f"Certificado {cert_id} no encontrado"}), 404
        return jsonify({"certificate": cert}), 200
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/<int:cert_id>", methods=["PUT"])
@admin_required
def update(cert_id):
    """
    Actualiza campos de un certificado existente.

    Body JSON (todos los campos son opcionales):
        {
            "nombre_completo": "Nuevo nombre",
            "email": "nuevo@email.com",
            "evento_id": 1,
            "fecha_emision": "2025-02-01",
            "descripcion": "Nueva descripción"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo debe ser JSON"}), 400

        cert = certificate_service.update_certificate(cert_id, **data)
        if not cert:
            return jsonify({"error": f"Certificado {cert_id} no encontrado"}), 404
        return jsonify({
            "message": "Certificado actualizado",
            "certificate": cert,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/<int:cert_id>", methods=["DELETE"])
@admin_required
def delete(cert_id):
    """Elimina un certificado por ID."""
    try:
        success = certificate_service.delete_certificate(cert_id)
        if success:
            return jsonify({"message": f"Certificado {cert_id} eliminado"}), 200
        return jsonify({"error": f"Certificado {cert_id} no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/<int:cert_id>/send", methods=["POST"])
@token_required
def send_single(cert_id):
    """
    Genera el PDF y envía un certificado por email.

    Disponible para admin y usuario.
    """
    try:
        result = certificate_service.send_certificate(cert_id)
        if result["success"]:
            return jsonify(result), 200
        return jsonify(result), 500

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/send-bulk", methods=["POST"])
@token_required
def send_bulk():
    """
    Envía múltiples certificados por email de forma masiva.

    Body JSON esperado:
        {
            "certificate_ids": [1, 2, 3, 4, 5]
        }
    """
    try:
        data = request.get_json()
        if not data or "certificate_ids" not in data:
            return jsonify({"error": "Envía certificate_ids como lista de IDs"}), 400

        cert_ids = data["certificate_ids"]
        if not isinstance(cert_ids, list) or len(cert_ids) == 0:
            return jsonify({"error": "certificate_ids debe ser una lista no vacía"}), 400

        results = certificate_service.send_certificate_bulk(cert_ids)
        return jsonify({
            "message": f"Envío masivo completado",
            "sent_count": len(results["sent"]),
            "failed_count": len(results["failed"]),
            "details": results,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/import-excel", methods=["POST"])
@admin_required
def import_excel():
    """
    Importa participantes desde un archivo Excel (.xlsx) o CSV (.csv) y los crea como certificados.

    El archivo debe tener las columnas:
        - Columna A: Nombre completo (obligatorio)
        - Columna B: Email (obligatorio)
        - Columna C: Fecha de emisión (opcional, formato YYYY-MM-DD)
        - Columna D: Descripción (opcional)

    Se envía como multipart/form-data con:
        - file: archivo .xlsx o .csv
        - evento_id: ID del evento
    """
    try:
        if "file" not in request.files:
            return jsonify({"error": "No se envió ningún archivo"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Archivo vacío"}), 400

        evento_id = request.form.get("evento_id", "")
        if not evento_id:
            return jsonify({"error": "evento_id es obligatorio"}), 400

        try:
            evento_id = int(evento_id)
        except ValueError:
            return jsonify({"error": "evento_id debe ser un número"}), 400

        # Validar que el evento existe
        from models.google_sheets import db
        evento = db.get_event_by_id(evento_id)
        if not evento:
            return jsonify({"error": f"Evento {evento_id} no encontrado"}), 404

        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        rows = []
        if ext in ("xlsx", "xls"):
            import openpyxl
            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            wb.close()
        elif ext == "csv":
            import csv
            import io as _io
            try:
                raw = file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                file.seek(0)
                raw = file.read().decode("latin-1")
            reader = csv.reader(_io.StringIO(raw))
            header = next(reader, None)  # saltar encabezado
            for csv_row in reader:
                rows.append(tuple(csv_row))
        else:
            return jsonify({"error": "Formato no soportado. Use archivos .xlsx o .csv"}), 400

        if not rows:
            return jsonify({"error": "El archivo está vacío (sin filas de datos)"}), 400

        creado_por = request.user["email"]
        created = []
        failed = []
        fecha_default = request.form.get("fecha_emision", "").strip()

        for i, row in enumerate(rows, start=2):
            try:
                if not row or len(row) < 2:
                    failed.append({"row": i, "reason": "Fila vacía o incompleta"})
                    continue

                nombre = str(row[0] or "").strip()
                email = str(row[1] or "").strip()

                if not nombre:
                    failed.append({"row": i, "reason": "Nombre vacío"})
                    continue
                if not email or "@" not in email:
                    failed.append({"row": i, "reason": f"Email inválido: {email}"})
                    continue

                fecha = str(row[2] or "").strip() if len(row) > 2 and row[2] else fecha_default
                desc = str(row[3] or "").strip() if len(row) > 3 and row[3] else ""

                cert = certificate_service.create_certificate(
                    nombre, email, evento_id, fecha, desc, creado_por
                )
                created.append(cert)

            except Exception as e:
                failed.append({"row": i, "reason": str(e)})

        logger.info(
            f"Importación Excel: evento={evento_id}, "
            f"creados={len(created)}, fallidos={len(failed)}"
        )

        return jsonify({
            "message": f"Importación completada: {len(created)} creados, {len(failed)} fallidos",
            "created_count": len(created),
            "failed_count": len(failed),
            "certificates": created,
            "failed": failed,
            "evento": evento["nombre"],
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error importando Excel: {e}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/verify/<code>", methods=["GET"])
def verify(code):
    """
    Verifica un certificado por su código de verificación.

    RUTA PÚBLICA - No requiere autenticación.
    Permite que cualquier persona verifique la autenticidad de un certificado.
    """
    try:
        cert = certificate_service.verify_certificate(code)
        if not cert:
            return jsonify({
                "valid": False,
                "message": "Certificado no encontrado o código inválido"
            }), 404

        # Obtener nombre del evento si existe
        evento = None
        if cert.get("evento_id"):
            from models.google_sheets import db
            evento = db.get_event_by_id(cert["evento_id"])

        return jsonify({
            "valid": True,
            "certificate": {
                "nombre_completo": cert["nombre_completo"],
                "evento_id": cert.get("evento_id"),
                "evento_nombre": evento.get("nombre", "") if evento else "",
                "fecha_emision": cert["fecha_emision"],
                "descripcion": cert["descripcion"],
                "codigo_verif": cert["codigo_verif"],
                "enviado": cert["enviado"],
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


@certs_bp.route("/public/lookup", methods=["POST"])
def public_lookup():
    """
    Busca certificados por email (portal público).
    RUTA PÚBLICA - No requiere autenticación.
    """
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "Email inválido"}), 400

        from models.google_sheets import db
        db.connect()

        records = db.certs_sheet.get_all_values()
        if len(records) <= 1:
            return jsonify({"found": False, "message": "No hay certificados registrados"}), 200

        email_idx = db._CERT_HEADERS.index("email")
        certs = []
        for row in records[1:]:
            if len(row) > email_idx and row[email_idx].strip().lower() == email:
                c = db._row_to_dict(db._CERT_HEADERS, row)
                c["id"] = db._safe_int(c["id"])
                c["evento_id"] = db._safe_int(c.get("evento_id", 0))
                c["enviado"] = str(c.get("enviado", "False")).strip().lower() == "true"

                evento = None
                if c.get("evento_id"):
                    evento = db.get_event_by_id(c["evento_id"])
                c["evento_nombre"] = evento.get("nombre", "") if evento else ""

                certs.append({
                    "id": c["id"],
                    "nombre_completo": c["nombre_completo"],
                    "evento_id": c["evento_id"],
                    "evento_nombre": c["evento_nombre"],
                    "fecha_emision": c["fecha_emision"],
                    "descripcion": c["descripcion"],
                    "codigo_verif": c["codigo_verif"],
                    "enviado": c["enviado"],
                })

        if not certs:
            return jsonify({"found": False, "message": "No se encontraron certificados para este email"}), 200

        return jsonify({"found": True, "certificates": certs, "total": len(certs)}), 200

    except Exception as e:
        logger.error(f"Error en lookup público: {e}")
        return jsonify({"error": "Error interno"}), 500


@certs_bp.route("/public/download/<int:cert_id>", methods=["GET"])
def public_download(cert_id):
    """
    Genera y descarga el PDF de un certificado por ID (portal público).
    RUTA PÚBLICA - No requiere autenticación.
    El email se valida como query param.
    """
    try:
        email = request.args.get("email", "").strip().lower()
        if not email:
            return jsonify({"error": "Email requerido como parámetro"}), 400

        from models.google_sheets import db
        cert = db.get_certificate_by_id(cert_id)
        if not cert:
            return jsonify({"error": "Certificado no encontrado"}), 404

        if cert["email"].strip().lower() != email:
            return jsonify({"error": "El email no coincide con el certificado"}), 403

        pdf_path = certificate_service.generate_certificate_pdf(cert)

        return_data = open(pdf_path, "rb").read()
        filename = f"certificado_{cert['nombre_completo'].replace(' ', '_')}.pdf"

        from flask import make_response
        response = make_response(return_data)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(f"PDF descargado públicamente: cert {cert_id} por {email}")
        return response

    except Exception as e:
        logger.error(f"Error descarga pública: {e}")
        return jsonify({"error": "Error interno"}), 500


@certs_bp.route("/public/activate/<code>", methods=["GET"])
def public_activate(code):
    """
    Activa un certificado por su código de verificación y genera el PDF.

    RUTA PÚBLICA — No requiere autenticación.
    El participante recibe el código por email y lo usa aquí para descargar.
    """
    try:
        cert = certificate_service.verify_certificate(code)
        if not cert:
            return jsonify({
                "valid": False,
                "message": "Codigo de activacion invalido o certificado no encontrado"
            }), 404

        # Obtener nombre del evento
        evento = None
        if cert.get("evento_id"):
            from models.google_sheets import db
            evento = db.get_event_by_id(cert["evento_id"])

        # Generar el PDF al activar
        pdf_path = certificate_service.generate_certificate_pdf(cert)

        return_data = open(pdf_path, "rb").read()
        filename = f"certificado_{cert['nombre_completo'].replace(' ', '_')}.pdf"

        from flask import make_response
        response = make_response(return_data)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(f"Certificado activado y descargado: {code}")
        return response

    except Exception as e:
        logger.error(f"Error activando certificado {code}: {e}")
        return jsonify({"error": "Error interno"}), 500


@certs_bp.route("/public/activate/<code>/info", methods=["GET"])
def public_activate_info(code):
    """
    Retorna la info del certificado sin generar el PDF.
    Útil para mostrar una vista previa antes de descargar.
    """
    try:
        cert = certificate_service.verify_certificate(code)
        if not cert:
            return jsonify({
                "valid": False,
                "message": "Codigo invalido"
            }), 404

        evento = None
        if cert.get("evento_id"):
            from models.google_sheets import db
            evento = db.get_event_by_id(cert["evento_id"])

        return jsonify({
            "valid": True,
            "certificate": {
                "nombre_completo": cert["nombre_completo"],
                "evento_id": cert.get("evento_id"),
                "evento_nombre": evento.get("nombre", "") if evento else "",
                "fecha_emision": cert["fecha_emision"],
                "descripcion": cert["descripcion"],
                "codigo_verif": cert["codigo_verif"],
            }
        }), 200

    except Exception as e:
        logger.error(f"Error en activate info: {e}")
        return jsonify({"error": "Error interno"}), 500


@certs_bp.route("/public/search", methods=["POST"])
def public_search():
    """
    Busca certificados por nombre o email (público, sin auth).

    Body JSON:
        { "query": "maria" }   o   { "query": "maria@ejemplo.com" }
    """
    try:
        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()
        if not query or len(query) < 2:
            return jsonify({"found": False, "message": "Ingresa al menos 2 caracteres"}), 200

        from models.google_sheets import db
        db.connect()

        records = db.certs_sheet.get_all_values()
        if len(records) <= 1:
            return jsonify({"found": False, "message": "No hay certificados registrados"}), 200

        headers = db._CERT_HEADERS
        name_idx = headers.index("nombre_completo")
        email_idx = headers.index("email")
        query_lower = query.lower()

        certs = []
        for row in records[1:]:
            if len(row) <= max(name_idx, email_idx):
                continue
            nombre = row[name_idx].strip().lower() if row[name_idx] else ""
            email = row[email_idx].strip().lower() if row[email_idx] else ""

            match = query_lower in nombre or query_lower in email
            if not match:
                continue

            c = db._row_to_dict(headers, row)
            c["id"] = db._safe_int(c["id"])
            c["evento_id"] = db._safe_int(c.get("evento_id", 0))
            c["enviado"] = str(c.get("enviado", "False")).strip().lower() == "true"

            evento = None
            if c.get("evento_id"):
                evento = db.get_event_by_id(c["evento_id"])

            certs.append({
                "id": c["id"],
                "nombre_completo": c["nombre_completo"],
                "email": c["email"],
                "evento_id": c["evento_id"],
                "evento_nombre": evento.get("nombre", "") if evento else "",
                "fecha_emision": c["fecha_emision"],
                "descripcion": c["descripcion"],
                "codigo_verif": c["codigo_verif"],
                "enviado": c["enviado"],
            })

        if not certs:
            return jsonify({"found": False, "message": "No se encontraron certificados"}), 200

        return jsonify({"found": True, "certificates": certs, "total": len(certs)}), 200

    except Exception as e:
        logger.error(f"Error en búsqueda pública: {e}")
        return jsonify({"error": "Error interno"}), 500