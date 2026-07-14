"""
Script de prueba para verificar que la API funciona correctamente.

Ejecutar después de inicializar la base de datos:
    python test_api.py

Requiere que el servidor Flask esté corriendo en localhost:5000
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"


def print_step(step_num, description):
    print(f"\n{'='*60}")
    print(f"  PASO {step_num}: {description}")
    print(f"{'='*60}")


def print_response(resp):
    print(f"  Status: {resp.status_code}")
    try:
        data = resp.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except Exception:
        print(f"  Response: {resp.text}")


def main():
    print("=" * 60)
    print("  PRUEBAS DE LA API - Certificados Backend")
    print("=" * 60)

    # Verificar que el servidor está activo
    print_step(0, "Verificar salud del servidor")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print_response(resp)
        if resp.status_code != 200:
            print("\n  El servidor no responde. Inicia con: python app.py")
            sys.exit(1)
    except requests.ConnectionError:
        print("  ERROR: No se pudo conectar al servidor.")
        print("  Asegúrate de ejecutar 'python app.py' primero.")
        sys.exit(1)

    # Variables globales para las pruebas
    admin_token = None
    cert_id = None

    # ── 1. Login como admin ─────────────────────────────
    print_step(1, "Login como administrador")
    admin_email = input("  Email del admin: ").strip()
    admin_password = input("  Contraseña: ").strip()

    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": admin_email,
        "password": admin_password,
    })
    print_response(resp)

    if resp.status_code != 200:
        print("\n  No se pudo iniciar sesión. ¿Ejecutaste init_db.py?")
        sys.exit(1)

    admin_token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # ── 2. Obtener info del usuario actual ──────────────
    print_step(2, "Obtener información del usuario actual")
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print_response(resp)

    # ── 3. Crear un certificado ─────────────────────────
    print_step(3, "Crear un certificado")
    resp = requests.post(f"{BASE_URL}/certificates/", headers=headers, json={
        "nombre_completo": "Ana Martínez López",
        "email": "ana.martinez@ejemplo.com",
        "evento_id": 1,
        "fecha_emision": "2025-07-10",
        "descripcion": "120 horas lectivas",
    })
    print_response(resp)

    if resp.status_code == 201:
        cert_id = resp.json()["certificate"]["id"]
        verify_code = resp.json()["certificate"]["codigo_verif"]
        print(f"\n  Certificado ID: {cert_id}")
        print(f"  Código de verificación: {verify_code}")

    # ── 4. Listar todos los certificados ────────────────
    print_step(4, "Listar todos los certificados")
    resp = requests.get(f"{BASE_URL}/certificates/", headers=headers)
    print_response(resp)

    # ── 5. Obtener certificado por ID ───────────────────
    if cert_id:
        print_step(5, f"Obtener certificado ID={cert_id}")
        resp = requests.get(f"{BASE_URL}/certificates/{cert_id}", headers=headers)
        print_response(resp)

    # ── 6. Actualizar certificado ───────────────────────
    if cert_id:
        print_step(6, f"Actualizar certificado ID={cert_id}")
        resp = requests.put(f"{BASE_URL}/certificates/{cert_id}", headers=headers, json={
            "descripcion": "150 horas lectivas - Actualizado",
        })
        print_response(resp)

    # ── 7. Verificar certificado (público) ──────────────
    if verify_code:
        print_step(7, f"Verificar certificado (público) - Código: {verify_code}")
        resp = requests.get(f"{BASE_URL}/certificates/verify/{verify_code}")
        print_response(resp)

    # ── 8. Registrar un nuevo usuario ───────────────────
    print_step(8, "Registrar un nuevo usuario normal")
    resp = requests.post(f"{BASE_URL}/auth/register", headers=headers, json={
        "nombre": "Carlos Usuario",
        "email": "carlos@ejemplo.com",
        "password": "carlos123",
        "rol": "usuario",
    })
    print_response(resp)

    # ── 9. Login como usuario normal ────────────────────
    print_step(9, "Login como usuario normal")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "carlos@ejemplo.com",
        "password": "carlos123",
    })
    print_response(resp)

    if resp.status_code == 200:
        user_token = resp.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # ── 10. Usuario intenta crear certificado (debe fallar) ──
        print_step(10, "Usuario intenta crear certificado (debe ser denegado)")
        resp = requests.post(f"{BASE_URL}/certificates/", headers=user_headers, json={
            "nombre_completo": "Test",
            "email": "test@test.com",
            "evento_id": 1,
        })
        print_response(resp)

    # ── Resumen ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RESUMEN DE PRUEBAS")
    print(f"{'='*60}")
    print("  Si todos los pasos mostraron status 200/201, la API funciona.")
    print("  El paso 10 debe mostrar 403 (acceso denegado para usuario).")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()