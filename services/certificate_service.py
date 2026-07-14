"""
Servicio de generación de certificados en PDF y envío por email.

El PDF se genera en horizontal (landscape) usando una plantilla PNG como fondo.
Solo se superpone el nombre del participante y las firmas de speakers.
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
    build_activation_email_body,
)
from config import Config

logger = logging.getLogger(__name__)

# ── Ruta a la plantilla de fondo ────────────────────────
_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "plantilla_certificado.png",
)


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


def _draw_background_image(c: canvas.Canvas, width: float, height: float,
                           template_path: str):
    """Dibuja la imagen de plantilla escalada a toda la página."""
    if not os.path.isfile(template_path):
        logger.warning(f"Plantilla no encontrada: {template_path}, usando fondo blanco")
        c.setFillColor(white)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        return

    from PIL import Image as PILImage

    img = PILImage.open(template_path)
    img_w, img_h = img.size  # píxeles originales

    # Calcular escala para cubrir toda la página (cover)
    scale_x = width / img_w
    scale_y = height / img_h
    scale = max(scale_x, scale_y)

    draw_w = img_w * scale
    draw_h = img_h * scale

    # Centrar si sobra espacio
    x_offset = (width - draw_w) / 2
    y_offset = (height - draw_h) / 2

    c.drawImage(
        ImageReader(template_path),
        x_offset, y_offset,
        width=draw_w, height=draw_h,
        preserveAspectRatio=False,
    )


def generate_certificate_pdf(certificado: dict) -> str:
    """
    Genera un PDF de certificado usando la plantilla PNG como fondo.

    Solo se superponen:
    - Nombre del participante (centrado, en el área 'Otorgado a:')
    - Código QR pequeño (esquina inferior derecha)
    """
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    filename = f"certificado_{certificado['id']}_{certificado['nombre_completo'].replace(' ', '_')}.pdf"
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)

    width, height = landscape(letter)  # 792 x 567 puntos
    c = canvas.Canvas(filepath, pagesize=landscape(letter))

    # ── 1. Fondo: imagen de plantilla a página completa ──
    _draw_background_image(c, width, height, _TEMPLATE_PATH)

    # ── 2. Nombre del participante ───────────────────────
    # Línea dorada está al 34.5% desde arriba → nombre al ~36.5%
    # En PDF coords: 1 - 0.365 = 0.635 desde abajo
    nombre = certificado["nombre_completo"].upper()

    # Ajustar tamaño de fuente si el nombre es muy largo
    font_size = 24
    name_w = c.stringWidth(nombre, "Helvetica-Bold", font_size)
    max_name_width = width * 0.55
    if name_w > max_name_width:
        ratio = max_name_width / name_w
        font_size = max(14, int(font_size * ratio))
        name_w = c.stringWidth(nombre, "Helvetica-Bold", font_size)

    name_y = height * 0.535  # 5% más de margen top adicional
    name_x = width / 2

    c.setFillColor(HexColor("#1a1a1a"))
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(name_x, name_y, nombre)



    # ═══════════════════════════════════════════════════
    #  4. QR pequeño (esquina inferior derecha)
    # ═══════════════════════════════════════════════════
    verify_url = f"https://tu-dominio.com/verify/{certificado['codigo_verif']}"
    qr_png = _generate_qr_base64(verify_url)
    qr_size = 55
    qr_x = width - qr_size - 30
    qr_y = 30

    c.drawImage(
        ImageReader(io.BytesIO(qr_png)),
        qr_x, qr_y, width=qr_size, height=qr_size,
    )
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 6)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 9,
                        certificado["codigo_verif"])

    # ── Código ID en esquina inferior izquierda ─────────
    c.setFillColor(HexColor("#bbbbbb"))
    c.setFont("Helvetica", 6)
    c.drawString(30, 30, f"ID: {certificado['codigo_verif']}")

    c.save()
    logger.info(f"PDF generado: {filepath}")
    return filepath


def send_certificate(cert_id: int) -> dict:
    """Envía email con código de activación (sin adjuntar PDF)."""
    certificado = db.get_certificate_by_id(cert_id)
    if not certificado:
        raise ValueError(f"Certificado con ID {cert_id} no encontrado")

    evento = db.get_event_by_id(certificado["evento_id"]) if certificado.get("evento_id") else None
    event_name = evento.get("nombre", "Evento") if evento else "Evento"
    subject = f"Su Certificado - {event_name}"

    body_html = build_activation_email_body(certificado, event_name)

    success = send_email_with_attachment(
        to_email=certificado["email"],
        subject=subject,
        body_html=body_html,
        attachment_path=None,
    )

    if success:
        db.mark_as_sent(cert_id)
        logger.info(f"Email de activacion enviado a {certificado['email']}")
        return {"success": True, "message": f"Correo de activacion enviado a {certificado['email']}"}
    else:
        return {"success": False, "message": "Error al enviar el correo de activacion"}


def send_certificate_bulk(cert_ids: list) -> dict:
    """Envía emails de activación masivos (sin adjuntar PDFs)."""
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
            evento = db.get_event_by_id(certificado["evento_id"]) if certificado.get("evento_id") else None
            event_name = evento.get("nombre", "Evento") if evento else "Evento"
            body_html = build_activation_email_body(certificado, event_name)
            success = send_email_with_attachment(
                to_email=certificado["email"],
                subject=f"Su Certificado - {event_name}",
                body_html=body_html,
                attachment_path=None,
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
    """Busca por código, intentando con y sin prefijo CERT-."""
    result = db.get_certificate_by_code(code)
    if not result and not code.startswith("CERT-"):
        result = db.get_certificate_by_code(f"CERT-{code}")
    return result


def update_certificate(cert_id, **kwargs):
    return db.update_certificate(cert_id, **kwargs)


def delete_certificate(cert_id):
    return db.delete_certificate(cert_id)