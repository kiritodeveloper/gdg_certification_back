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
    """Genera el HTML del correo usando el nombre del evento (legacy)."""
    return build_activation_email_body(certificado, "Evento")


def build_activation_email_body(certificado: dict, evento_nombre: str = "Evento") -> str:
    """Genera email con código de activación y guía para descargar el certificado."""

    # Leer la URL base desde config o usar placeholder
    try:
        from config import Config
        base_url = getattr(Config, "BASE_URL", "https://tu-dominio.com")
    except Exception:
        base_url = "https://tu-dominio.com"

    activate_url = f"{base_url}/ver-certificado/{certificado['codigo_verif']}"

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
                margin: 0 0 8px;
                font-size: 22px;
                font-weight: 600;
            }}
            .header p {{
                margin: 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .content {{
                padding: 35px 40px;
            }}
            .content p {{
                color: #333;
                line-height: 1.7;
                font-size: 15px;
                margin: 0 0 14px;
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
            .code-box {{
                background: #f8f9fa;
                border: 2px dashed #1a73e8;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin: 25px 0;
            }}
            .code-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            .code-value {{
                font-family: 'Courier New', monospace;
                font-size: 22px;
                font-weight: bold;
                color: #1a73e8;
                letter-spacing: 2px;
                margin: 0;
            }}
            .steps {{
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 10px;
                padding: 20px 25px;
                margin: 25px 0;
            }}
            .steps-title {{
                color: #166534;
                font-size: 16px;
                font-weight: bold;
                margin: 0 0 15px;
            }}
            .step {{
                display: flex;
                align-items: flex-start;
                margin-bottom: 14px;
            }}
            .step:last-child {{
                margin-bottom: 0;
            }}
            .step-num {{
                background: #22c55e;
                color: white;
                width: 26px;
                height: 26px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 13px;
                font-weight: bold;
                flex-shrink: 0;
                margin-right: 14px;
                margin-top: 2px;
            }}
            .step-text {{
                color: #333;
                font-size: 14px;
                line-height: 1.6;
                padding-top: 3px;
            }}
            .step-text strong {{
                color: #166534;
            }}
            .activate-btn {{
                display: inline-block;
                background: linear-gradient(135deg, #1a73e8, #0d47a1);
                color: white !important;
                text-decoration: none;
                padding: 14px 36px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                margin: 25px 0;
                text-align: center;
            }}
            .or-text {{
                text-align: center;
                color: #999;
                font-size: 13px;
                margin: 15px 0;
            }}
            .manual-link {{
                text-align: center;
                font-size: 14px;
                color: #1a73e8;
                word-break: break-all;
                margin: 10px 0;
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
                <h1>Tu Certificado esta Listo</h1>
                <p> Solo necesitas activarlo con tu codigo</p>
            </div>
            <div class="content">
                <p>Hola <strong>{certificado['nombre_completo']}</strong>,</p>
                <p>
                    Felicidades por tu participacion exitosa en:
                </p>
                <div class="highlight">
                    <p style="margin:0"><strong>Evento:</strong> {evento_nombre}</p>
                    <p style="margin:10px 0 0"><strong>Fecha de emision:</strong> {certificado['fecha_emision']}</p>
                </div>

                <p>Tu certificado fue generado y esta listo para descargar. Para obtenerlo, necesitas el siguiente codigo de activacion:</p>

                <div class="code-box">
                    <div class="code-label">Tu Codigo de Activacion</div>
                    <p class="code-value">{certificado['codigo_verif']}</p>
                </div>

                <div class="steps">
                    <p class="steps-title">Como obtener tu certificado:</p>
                    <div class="step">
                        <div class="step-num">1</div>
                        <div class="step-text">
                            <strong>Copia tu codigo</strong> que aparece arriba.
                            Es unico y personal para ti.
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">2</div>
                        <div class="step-text">
                            <strong>Entra a la plataforma</strong> y busca la
                            seccion "Activar Certificado" o haz clic en el
                            boton de abajo.
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">3</div>
                        <div class="step-text">
                            <strong>Pega tu codigo</strong> en el campo de
                            activacion y presiona "Descargar". Tu certificado
                            en PDF se generara automaticamente.
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-num">4</div>
                        <div class="step-text">
                            <strong>Guarda o imprime</strong> tu certificado.
                            Tambien puedes verificar su autenticidad
                            escaneando el codigo QR que incluye.
                        </div>
                    </div>
                </div>

                <div style="text-align:center">
                    <a href="{activate_url}" class="activate-btn">
                        Activar y Descargar mi Certificado
                    </a>
                </div>

                <p class="or-text">o copia este enlace en tu navegador:</p>
                <p class="manual-link">{activate_url}</p>

                <p style="font-size:13px;color:#888;margin-top:20px">
                    Si tienes algun problema, contacta al organizador del evento
                    con tu codigo de activacion.
                </p>
            </div>
            <div class="footer">
                <p>Este correo fue enviado automaticamente. No respondas a este mensaje.</p>
            </div>
        </div>
    </body>
    </html>
    """