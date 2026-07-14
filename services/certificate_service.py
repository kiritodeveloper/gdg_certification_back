"""
Servicio de generación de certificados en PDF y envío por email.

El PDF se genera en horizontal (landscape) con:
- Borde decorativo con colores del evento
- Código QR con link de verificación
- Firmas de speakers del evento
- Diseño profesional similar a certificados modernos
"""

import os
import io
import base64
import logging
import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from models.google_sheets import db
from utils.email_sender import (
    send_email_with_attachment,
    build_certificate_email_body,
)
from config import Config

logger = logging.getLogger(__name__)


def create_certificate(
    nombre_completo, email, evento_id,
    fecha_emision, descripcion, creado_por
):
    if not nombre_completo or not email or not evento_id:
        raise ValueError("nombre_completo, email y evento_id son obligatorios")
    if not fecha_emision:
        fecha_emision = datetime.datetime.now().strftime("%Y-%m-%d")
    return db.create_certificate(
        nombre_completo, email, evento_id,
        fecha_emision, descripcion, creado_por
    )


def _generate_qr_base64(data: str) -> bytes:
    """Genera un QR code como PNG en memoria."""
    qr = qrcode.QRCode(
        version=2, error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8, border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a3a5c", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _parse_base64_image(b64_string: str) -> bytes | None:
    """Convierte un string base64 (con o sin data URI) a bytes de imagen."""
    if not b64_string:
        return None
    try:
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]
        return base64.b64decode(b64_string)
    except Exception:
        return None


def generate_certificate_pdf(certificado: dict) -> str:
    """
    Genera un PDF de certificado horizontal profesional.

    Incluye: borde decorativo con colores del evento, QR de verificación,
    firmas de speakers, nombre del participante, nombre del evento.
    """
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Obtener datos del evento y speakers
    evento = db.get_event_by_id(certificado["evento_id"]) if certificado.get("evento_id") else None
    speakers = []
    if evento:
        speakers = db.get_speakers_by_event(certificado["evento_id"])

    # Colores del evento o defaults
    color_primary = evento.get("color_primario", "#1a73e8") if evento else "#1a73e8"
    color_secondary = evento.get("color_secundario", "#c8a45a") if evento else "#c8a45a"
    nombre_evento = evento.get("nombre", "Evento") if evento else "Evento"

    prim = HexColor(color_primary)
    sec = HexColor(color_secondary)
    prim_light = Color(
        prim.red * 0.15 + 0.85,
        prim.green * 0.15 + 0.85,
        prim.blue * 0.15 + 0.85,
    )

    filename = f"certificado_{certificado['id']}_{certificado['nombre_completo'].replace(' ', '_')}.pdf"
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)

    width, height = landscape(letter)
    c = canvas.Canvas(filepath, pagesize=landscape(letter))

    # ── Fondo blanco ────────────────────────────────────
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # ── Borde decorativo exterior grueso ────────────────
    c.setStrokeColor(prim)
    c.setLineWidth(6)
    c.roundRect(18, 18, width - 36, height - 36, 12, fill=0, stroke=1)

    # ── Borde interior dorado ───────────────────────────
    c.setStrokeColor(sec)
    c.setLineWidth(1.5)
    c.roundRect(28, 28, width - 56, height - 56, 8, fill=0, stroke=1)

    # ── Esquinas decorativas ────────────────────────────
    corner_len = 35
    c.setStrokeColor(prim)
    c.setLineWidth(4)
    corners = [
        (30, height - 30, 30 + corner_len, height - 30, 30, height - 30 - corner_len),
        (width - 30, height - 30, width - 30 - corner_len, height - 30, width - 30, height - 30 - corner_len),
        (30, 30, 30 + corner_len, 30, 30, 30 + corner_len),
        (width - 30, 30, width - 30 - corner_len, 30, width - 30, 30 + corner_len),
    ]
    for cx, cy, x1, y1, x2, y2 in corners:
        c.line(cx, cy, x1, y1)
        c.line(cx, cy, x2, y2)

    # ── Línea decorativa multicolor bajo título ─────────
    colors_bar = [
        HexColor("#e74c3c"), HexColor("#e67e22"), HexColor("#f1c40f"),
        HexColor("#2ecc71"), HexColor("#3498db"), HexColor("#9b59b6"),
    ]
    bar_y = height - 120
    bar_width = 300
    bar_start = (width - bar_width) / 2
    seg = bar_width / len(colors_bar)
    for i, col in enumerate(colors_bar):
        c.setFillColor(col)
        c.rect(bar_start + i * seg, bar_y, seg + 1, 3, fill=1, stroke=0)

    # ── Título CERTIFICADO ─────────────────────────────
    c.setFillColor(prim)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2, height - 85, "CERTIFICADO DE PARTICIPACION")

    # ── "Se certifica que" ─────────────────────────────
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 150, "Se certifica que")

    # ── Nombre del participante ────────────────────────
    c.setFillColor(prim)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 195, certificado["nombre_completo"])

    # ── Línea bajo nombre ──────────────────────────────
    name_w = c.stringWidth(certificado["nombre_completo"], "Helvetica-Bold", 28)
    c.setStrokeColor(sec)
    c.setLineWidth(1.5)
    c.line(width / 2 - name_w / 2 - 15, height - 205,
           width / 2 + name_w / 2 + 15, height - 205)

    # ── "ha participado en el evento" ──────────────────
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 235, "ha participado exitosamente en el evento:")

    # ── Nombre del evento ──────────────────────────────
    c.setFillColor(prim)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 270, nombre_evento)

    # ── Descripción si existe ──────────────────────────
    desc_y = height - 295
    if certificado.get("descripcion"):
        c.setFillColor(HexColor("#666666"))
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, desc_y, certificado["descripcion"])
        desc_y -= 20

    # ── Fecha ──────────────────────────────────────────
    c.setFillColor(HexColor("#666666"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, desc_y - 5,
        f"Fecha de emision: {certificado['fecha_emision']}")

    # ══════════════════════════════════════════════════
    #  SECCIÓN INFERIOR: QR + Firmas
    # ══════════════════════════════════════════════════
    bottom_section_y = 70

    # ── Generar QR ──────────────────────────────────────
    verify_url = f"https://tu-dominio.com/verify/{certificado['codigo_verif']}"
    qr_png = _generate_qr_base64(verify_url)
    qr_path = os.path.join(Config.UPLOAD_FOLDER, f"_qr_{certificado['id']}.png")
    with open(qr_path, "wb") as f:
        f.write(qr_png)

    # Dibujar QR centrado o a la izquierda
    if speakers:
        # QR a la izquierda
        qr_x = 80
        qr_y = bottom_section_y + 10
        qr_size = 80
        c.drawImage(ImageReader(io.BytesIO(qr_png)),
                     qr_x, qr_y, width=qr_size, height=qr_size)
        c.setFillColor(HexColor("#888888"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 12,
                            "Escanea para verificar")
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 22,
                            certificado["codigo_verif"])

        # ── Firmas de speakers ─────────────────────────
        sig_start_x = 220
        available_width = width - sig_start_x - 60
        n_speakers = len(speakers)
        if n_speakers > 0:
            slot_width = available_width / n_speakers
            for idx, sp in enumerate(speakers):
                sx = sig_start_x + (slot_width * idx) + slot_width / 2

                # Firma imagen si existe
                firma_data = sp.get("firma_base64", "")
                if firma_data:
                    img_bytes = _parse_base64_image(firma_data)
                    if img_bytes:
                        try:
                            sig_w, sig_h = 140, 55
                            sig_path = os.path.join(Config.UPLOAD_FOLDER,
                                f"_sig_{sp['id']}.png")
                            with open(sig_path, "wb") as f:
                                f.write(img_bytes)
                            c.drawImage(ImageReader(io.BytesIO(img_bytes)),
                                       sx - sig_w / 2, bottom_section_y + 45,
                                       width=sig_w, height=sig_h,
                                       mask='auto')
                        except Exception:
                            pass

                # Línea de firma
                line_w = 120
                c.setStrokeColor(HexColor("#999999"))
                c.setLineWidth(0.8)
                c.line(sx - line_w / 2, bottom_section_y + 38,
                       sx + line_w / 2, bottom_section_y + 38)

                # Nombre del speaker
                c.setFillColor(HexColor("#333333"))
                c.setFont("Helvetica-Bold", 9)
                c.drawCentredString(sx, bottom_section_y + 22, sp.get("nombre", ""))

                # Cargo
                c.setFillColor(HexColor("#777777"))
                c.setFont("Helvetica", 8)
                c.drawCentredString(sx, bottom_section_y + 10, sp.get("cargo", ""))
    else:
        # Sin speakers: QR centrado
        qr_size = 90
        c.drawImage(ImageReader(io.BytesIO(qr_png)),
                     width / 2 - qr_size / 2, bottom_section_y,
                     width=qr_size, height=qr_size)
        c.setFillColor(HexColor("#888888"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, bottom_section_y - 12,
                            "Escanea para verificar")
        c.drawCentredString(width / 2, bottom_section_y - 22,
                            certificado["codigo_verif"])

    # ── Código en esquina inferior ─────────────────────
    c.setFillColor(HexColor("#bbbbbb"))
    c.setFont("Helvetica", 7)
    c.drawRightString(width - 45, 35, f"ID: {certificado['codigo_verif']}")
    c.drawRightString(width - 45, 25, certificado["fecha_emision"])

    c.save()
    logger.info(f"PDF generado: {filepath}")

    # Limpiar archivos temporales
    try:
        os.remove(qr_path)
    except Exception:
        pass

    return filepath


def send_certificate(cert_id: int) -> dict:
    certificado = db.get_certificate_by_id(cert_id)
    if not certificado:
        raise ValueError(f"Certificado con ID {cert_id} no encontrado")

    pdf_path = generate_certificate_pdf(certificado)
    body_html = build_certificate_email_body(certificado)

    # Ajustar para el nuevo formato con eventos
    evento = db.get_event_by_id(certificado["evento_id"]) if certificado.get("evento_id") else None
    event_name = evento.get("nombre", "Evento") if evento else "Evento"
    subject = f"Su Certificado - {event_name}"

    success = send_email_with_attachment(
        to_email=certificado["email"],
        subject=subject,
        body_html=body_html,
        attachment_path=pdf_path,
    )

    if success:
        db.mark_as_sent(cert_id)
        logger.info(f"Certificado {cert_id} enviado a {certificado['email']}")
        return {"success": True, "message": f"Certificado enviado a {certificado['email']}", "pdf_path": pdf_path}
    else:
        return {"success": False, "message": "Error al enviar el certificado por email", "pdf_path": pdf_path}


def send_certificate_bulk(cert_ids: list) -> dict:
    results = {"sent": [], "failed": []}
    for cert_id in cert_ids:
        try:
            certificado = db.get_certificate_by_id(cert_id)
            if not certificado:
                results["failed"].append({"id": cert_id, "reason": "No encontrado"})
                continue
            if certificado["enviado"]:
                results["failed"].append({"id": cert_id, "reason": "Ya fue enviado"})
                continue
            pdf_path = generate_certificate_pdf(certificado)
            evento = db.get_event_by_id(certificado["evento_id"]) if certificado.get("evento_id") else None
            event_name = evento.get("nombre", "Evento") if evento else "Evento"
            body_html = build_certificate_email_body(certificado)
            success = send_email_with_attachment(
                to_email=certificado["email"],
                subject=f"Su Certificado - {event_name}",
                body_html=body_html,
                attachment_path=pdf_path,
            )
            if success:
                db.mark_as_sent(cert_id)
                results["sent"].append(cert_id)
            else:
                results["failed"].append({"id": cert_id, "reason": "Error de envio"})
        except Exception as e:
            results["failed"].append({"id": cert_id, "reason": str(e)})
            logger.error(f"Error enviando certificado {cert_id}: {e}")
    return results


def get_all_certificates(creado_por=None):
    if creado_por:
        return db.get_certificates_by_creator(creado_por)
    return db.get_all_certificates()


def get_certificate(cert_id):
    return db.get_certificate_by_id(cert_id)


def verify_certificate(code):
    return db.get_certificate_by_code(code)


def update_certificate(cert_id, **kwargs):
    return db.update_certificate(cert_id, **kwargs)


def delete_certificate(cert_id):
    return db.delete_certificate(cert_id)