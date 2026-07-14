"""
Rutas de autenticación: registro, login y gestión de usuarios.

Todas las rutas de gestión de usuarios requieren token JWT con rol 'admin'.
"""

from functools import wraps
from flask import Blueprint, request, jsonify
from services import auth_service
from utils.token import verify_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def token_required(f):
    """Decorador: requiere token JWT válido en el header Authorization."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Token requerido. Envía Authorization: Bearer <token>"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Formato de token inválido. Usa: Bearer <token>"}), 401

        token = parts[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Token inválido o expirado"}), 401

        request.user = payload
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorador: requiere token JWT con rol 'admin'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Token requerido"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Formato de token inválido"}), 401

        token = parts[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Token inválido o expirado"}), 401

        if payload.get("rol") != "admin":
            return jsonify({"error": "Acceso denegado. Se requiere rol de administrador"}), 403

        request.user = payload
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/register", methods=["POST"])
@admin_required
def register():
    """
    Registra un nuevo usuario.

    Solo los administradores pueden registrar nuevos usuarios.
    El campo 'rol' es opcional (por defecto: 'usuario').

    Body JSON esperado:
        {
            "nombre": "Juan Pérez",
            "email": "juan@ejemplo.com",
            "password": "mi_contraseña_segura",
            "rol": "usuario"        // opcional, por defecto "usuario"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        nombre = data.get("nombre", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        rol = data.get("rol", "usuario").strip().lower()

        # Validaciones
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        if not email or "@" not in email:
            return jsonify({"error": "Email inválido"}), 400
        if len(password) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
        if rol not in ("admin", "usuario"):
            return jsonify({"error": "Rol inválido. Valores permitidos: admin, usuario"}), 400

        user = auth_service.register_user(nombre, email, password, rol)
        return jsonify({
            "message": "Usuario registrado exitosamente",
            "user": user,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Inicia sesión y devuelve un token JWT.

    Body JSON esperado:
        {
            "email": "admin@ejemplo.com",
            "password": "mi_contraseña"
        }

    Respuesta exitosa:
        {
            "token": "eyJhbGciOi...",
            "user": {
                "id": 1,
                "nombre": "Administrador",
                "email": "admin@ejemplo.com",
                "rol": "admin"
            }
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "El cuerpo de la petición debe ser JSON"}), 400

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"error": "Email y contraseña son obligatorios"}), 400

        result = auth_service.login_user(email, password)
        if not result:
            return jsonify({"error": "Credenciales inválidas"}), 401

        return jsonify({
            "message": "Login exitoso",
            **result,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user():
    """
    Obtiene la información del usuario autenticado actual.

    Requiere header: Authorization: Bearer <token>
    """
    user = request.user
    return jsonify({
        "email": user["email"],
        "nombre": user["nombre"],
        "rol": user["rol"],
    }), 200


@auth_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """
    Lista todos los usuarios del sistema.

    Solo accesible para administradores.
    Requiere header: Authorization: Bearer <token>
    """
    users = auth_service.get_users_list()
    return jsonify({"users": users, "total": len(users)}), 200


@auth_bp.route("/users/<email>", methods=["DELETE"])
@admin_required
def delete_user(email):
    """
    Elimina un usuario del sistema.

    Solo accesible para administradores.
    No se puede eliminar a sí mismo.
    """
    if request.user["email"] == email:
        return jsonify({"error": "No puedes eliminar tu propia cuenta"}), 400

    success = auth_service.remove_user(email)
    if success:
        return jsonify({"message": f"Usuario '{email}' eliminado correctamente"}), 200
    return jsonify({"error": f"Usuario '{email}' no encontrado"}), 404