"""
Utilidades para el envío de emails con archivos adjuntos.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging

from config import Config

logger = logging.getLogger(__name__)


def send_email_with_attachment(
    to_email: str,
    subject: str,
    body_html: str,
    attachment_path: str = None,
) -> bool:
    """
    Envía un email con contenido HTML y opcionalmente un archivo adjunto (PDF).

    Usa SMTP con TLS (puerto 587), compatible con Gmail y otros proveedores.
    Para Gmail se requiere una "Contraseña de aplicación" (App Password),
    no la contraseña normal de la cuenta.

    Args:
        to_email: Dirección de email del destinatario.
        subject: Asunto del email.
        body_html: Cuerpo del mensaje en formato HTML.
        attachment_path: Ruta al archivo PDF a adjuntar (opcional).

    Returns:
        True si el email se envió correctamente, False en caso contrario.
    """
    if not Config.EMAIL_SENDER or not Config.EMAIL_PASSWORD:
        logger.error("Credenciales de email no configuradas en .env")
        return False

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = Config.EMAIL_SENDER
    msg["To"] = to_email

    # Cuerpo HTML del mensaje
    html_part = MIMEText(body_html, "html", "utf-8")
    msg.attach(html_part)

    # Adjuntar PDF si existe
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                pdf_part = MIMEBase("application", "pdf")
                pdf_part.set_payload(f.read())
            encoders.encode_base64(pdf_part)
            pdf_part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}",
            )
            msg.attach(pdf_part)
            logger.info(f"PDF adjuntado: {attachment_path}")
        except Exception as e:
            logger.error(f"Error adjuntando PDF: {e}")
            return False

    try:
        with smtplib.SMTP(
            Config.EMAIL_SMTP_SERVER, Config.EMAIL_SMTP_PORT
        ) as server:
            server.starttls()
            server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email enviado exitosamente a {to_email}")
            return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación SMTP. Verifica las credenciales.")
        return False
    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        return False


def build_certificate_email_body(certificado: dict) -> str:
    """Genera el HTML del correo usando el nombre del evento."""
    evento_nombre = "Evento"
    if certificado.get("evento_id"):
        try:
            from models.google_sheets import db
            evento = db.get_event_by_id(int(certificado["evento_id"]))
            if evento:
                evento_nombre = evento.get("nombre", "Evento")
        except Exception:
            pass

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #f4f7f6;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            }}
            .header {{
                background: linear-gradient(135deg, #1a73e8, #0d47a1);
                color: white;
                padding: 30px 40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px;
            }}
            .content p {{
                color: #333;
                line-height: 1.7;
                font-size: 16px;
                margin: 0 0 15px;
            }}
            .highlight {{
                background: #e8f0fe;
                border-left: 4px solid #1a73e8;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 0 8px 8px 0;
            }}
            .highlight strong {{
                color: #1a73e8;
            }}
            .code {{
                font-family: 'Courier New', monospace;
                background: #f1f3f4;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 14px;
                letter-spacing: 1px;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 20px 40px;
                text-align: center;
                color: #666;
                font-size: 13px;
                border-top: 1px solid #eee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Certificado Emitido</h1>
            </div>
            <div class="content">
                <p>Estimado/a <strong>{certificado['nombre_completo']}</strong>,</p>
                <p>
                    Nos complace informarle que se ha emitido su certificado por la
                    participación exitosa en:
                </p>
                <div class="highlight">
                    <p style="margin:0"><strong>Evento:</strong> {evento_nombre}</p>
                    <p style="margin:10px 0 0"><strong>Fecha de emisión:</strong> {certificado['fecha_emision']}</p>
                </div>
                <p>
                    Su certificado se adjunta a este correo en formato PDF para que
                    pueda guardarlo e imprimirlo cuando lo desee.
                </p>
                <p>
                    Código de verificación: <span class="code">{certificado['codigo_verif']}</span>
                </p>
                <p>
                    Guarde este código para futuras consultas o verificaciones de
                    autenticidad del certificado.
                </p>
            </div>
            <div class="footer">
                <p>Este correo fue enviado automáticamente. No responda a este mensaje.</p>
            </div>
        </div>
    </body>
    </html>
    """