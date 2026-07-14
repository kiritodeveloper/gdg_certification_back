"""
Certificados Backend - Flask API

Backend para la gestión y envío de certificados usando Google Sheets como base de datos.

Para iniciar:
    1. Copia .env.example a .env y configura tus credenciales
    2. pip install -r requirements.txt
    3. python app.py

La API estará disponible en http://localhost:5000
"""

import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes.auth import auth_bp
from routes.certificates import certs_bp
from routes.events import events_bp
from routes.speakers import speakers_bp


# ── Configuración de logging ───────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Crear aplicación Flask ─────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# CORS habilitado para todas las rutas (ajustar en producción)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ── Registrar blueprints (rutas) ───────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(certs_bp)
app.register_blueprint(events_bp)
app.register_blueprint(speakers_bp)


# ── Ruta de salud del servidor ─────────────────────────────
@app.route("/api/health", methods=["GET"])
def health_check():
    """Verifica que el servidor está activo."""
    return jsonify({
        "status": "ok",
        "service": "Certificados Backend API",
        "version": "1.0.0",
    }), 200


# ── Manejador de errores global ────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Ruta no encontrada", "available_routes": [
        "POST   /api/auth/login",
        "POST   /api/auth/register   (admin)",
        "GET    /api/auth/me          (autenticado)",
        "GET    /api/auth/users       (admin)",
        "POST   /api/certificates/    (admin)",
        "GET    /api/certificates/    (autenticado)",
        "PUT    /api/certificates/<id> (admin)",
        "DELETE /api/certificates/<id> (admin)",
        "POST   /api/certificates/<id>/send (autenticado)",
        "POST   /api/certificates/send-bulk (autenticado)",
        "GET    /api/certificates/verify/<code> (publico)",
        "CRUD   /api/events/          (admin)",
        "CRUD   /api/speakers/        (admin)",
        "POST   /api/speakers/<id>/signature (admin)",
        "GET    /api/health           (publico)",
    ]}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Error interno del servidor"}), 500


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Método HTTP no permitido"}), 405


# ── Punto de entrada ────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Iniciando Certificados Backend API...")
    logger.info(f"Modo: {'DESARROLLO' if Config.DEBUG else 'PRODUCCIÓN'}")
    logger.info(f"Puerto: {Config.PORT}")

    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )