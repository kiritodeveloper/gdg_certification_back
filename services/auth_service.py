"""
Servicio de autenticación: registro, login y gestión de usuarios.
"""

import logging
from werkzeug.security import generate_password_hash, check_password_hash
from models.google_sheets import db
from utils.token import generate_token

logger = logging.getLogger(__name__)


def register_user(nombre: str, email: str, password: str, rol: str = "usuario") -> dict:
    """
    Registra un nuevo usuario en el sistema.

    Hashea el password con werkzeug antes de almacenarlo en Google Sheets.
    Por defecto, los nuevos usuarios tienen rol 'usuario'.
    Solo un admin puede crear otros usuarios con rol 'admin'.

    Args:
        nombre: Nombre completo del usuario.
        email: Email del usuario (debe ser único).
        password: Contraseña en texto plano (se hashea antes de guardar).
        rol: Rol del usuario ('admin' o 'usuario').

    Returns:
        Diccionario con los datos del usuario creado (sin password).

    Raises:
        ValueError: Si el email ya está registrado.
    """
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    user = db.create_user(nombre, email, password_hash, rol)
    return user


def login_user(email: str, password: str) -> dict | None:
    """
    Autentica a un usuario y genera un token JWT.

    Args:
        email: Email del usuario.
        password: Contraseña en texto plano.

    Returns:
        Diccionario con token y datos del usuario, o None si las credenciales
        son inválidas.
    """
    user = db.get_user_by_email(email)

    if not user:
        logger.warning(f"Intento de login con email no registrado: {email}")
        return None

    if not check_password_hash(user["password"], password):
        logger.warning(f"Contraseña incorrecta para: {email}")
        return None

    # Generar token JWT
    token = generate_token(
        user_email=user["email"],
        user_role=user["rol"],
        user_name=user["nombre"],
    )

    logger.info(f"Login exitoso: {email} (rol: {user['rol']})")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "nombre": user["nombre"],
            "email": user["email"],
            "rol": user["rol"],
        },
    }


def get_users_list() -> list[dict]:
    """Retorna la lista de todos los usuarios (sin passwords)."""
    return db.get_all_users()


def remove_user(email: str) -> bool:
    """Elimina un usuario del sistema."""
    return db.delete_user(email)