"""
Script para inicializar la base de datos con un usuario administrador.

Ejecutar una sola vez después de configurar .env:
    python init_db.py
"""

import sys
import os

# Asegurar que el directorio del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.auth_service import register_user
from models.google_sheets import db


def main():
    print("=" * 60)
    print("  INICIALIZACIÓN DE BASE DE DATOS - Certificados Backend")
    print("=" * 60)
    print()

    # Conectar a Google Sheets para verificar credenciales
    print("[1/2] Conectando a Google Sheets...")
    try:
        db.connect()
        print("      Conexión exitosa a Google Sheets")
    except Exception as e:
        print(f"      ERROR: {e}")
        print()
        print("Solución:")
        print("  1. Verifica que GOOGLE_CREDENTIALS_JSON sea válido en .env")
        print("  2. Verifica que GOOGLE_SHEET_ID sea correcto")
        print("  3. Asegúrate de que la Service Account tenga acceso al Sheet")
        sys.exit(1)

    print()

    # Crear usuario administrador
    print("[2/2] Creando usuario administrador...")
    try:
        admin_email = input("  Email del admin: ").strip().lower()
        admin_nombre = input("  Nombre completo: ").strip()
        admin_password = input("  Contraseña: ").strip()

        if not admin_email or not admin_nombre or not admin_password:
            print("  ERROR: Todos los campos son obligatorios")
            sys.exit(1)

        if len(admin_password) < 6:
            print("  ERROR: La contraseña debe tener al menos 6 caracteres")
            sys.exit(1)

        user = register_user(admin_nombre, admin_email, admin_password, "admin")

        print()
        print("-" * 60)
        print("  USUARIO ADMIN CREADO EXITOSAMENTE")
        print("-" * 60)
        print(f"  Nombre:  {user['nombre']}")
        print(f"  Email:   {user['email']}")
        print(f"  Rol:     {user['rol']}")
        print(f"  ID:      {user['id']}")
        print()
        print("  Ya puedes iniciar sesión con la API:")
        print(f"    POST /api/auth/login")
        print(f'    {{"email": "{admin_email}", "password": "{admin_password}"}}')
        print()

    except ValueError as e:
        print(f"  ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()