"""
Utilidades para generación y validación de tokens JWT.
"""

import datetime
import jwt
from config import Config


def generate_token(user_email: str, user_role: str, user_name: str) -> str:
    """
    Genera un token JWT para un usuario autenticado.

    El token incluye:
      - email del usuario
      - rol (admin / usuario)
      - nombre completo
      - fecha de expiración

    Args:
        user_email: Email del usuario.
        user_role: Rol del usuario (admin o usuario).
        user_name: Nombre completo del usuario.

    Returns:
        Token JWT codificado como string.
    """
    payload = {
        "email": user_email,
        "rol": user_role,
        "nombre": user_name,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")
    return token


def verify_token(token: str) -> dict | None:
    """
    Verifica y decodifica un token JWT.

    Args:
        token: Token JWT a verificar.

    Returns:
        Diccionario con los datos del payload si es válido, None si no.
    """
    try:
        payload = jwt.decode(
            token, Config.JWT_SECRET_KEY, algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None