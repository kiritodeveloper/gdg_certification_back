# Guía de Configuración del Backend de Certificados

Este documento explica cómo configurar las variables de entorno necesarias en el archivo `.env` para que la aplicación funcione correctamente.

## Resumen de Pasos

1.  **Configurar Google Cloud**: Crear un proyecto, habilitar APIs y generar credenciales de una cuenta de servicio.
2.  **Configurar Google Sheets**: Crear una hoja de cálculo y compartirla con la cuenta de servicio.
3.  **Configurar el Envío de Emails**: Generar una contraseña de aplicación para tu cuenta de Gmail.
4.  **Completar el archivo `.env`**: Rellenar todas las variables con la información obtenida.
5.  **Inicializar la Base de Datos**: Ejecutar el script `init_db.py`.

---

## 1. Configuración de Google Sheets y Google Cloud

Esta es la sección más importante, ya que conecta la aplicación con tu hoja de cálculo que funcionará como base de datos.

### Paso 1.1: Crear y Configurar el Proyecto en Google Cloud

1.  **Ve a la Consola de Google Cloud**: Inicia sesión en https://console.cloud.google.com/.
2.  **Crea o selecciona un proyecto**: En la parte superior, puedes crear un nuevo proyecto (ej. "Proyecto Certificados") o usar uno que ya tengas.
3.  **Habilita las APIs necesarias**:
    *   Usa la barra de búsqueda para encontrar y habilitar **"Google Sheets API"**.
    *   Luego, busca y habilita **"Google Drive API"**.

### Paso 1.2: Crear una Cuenta de Servicio (Service Account)

Una cuenta de servicio es como un "usuario robot" que tu aplicación usará para acceder a la hoja de cálculo.

1.  En el menú de navegación (☰), ve a `IAM y administración` > `Cuentas de servicio`.
2.  Haz clic en `+ CREAR CUENTA DE SERVICIO`.
3.  Dale un nombre (ej. `api-certificados`) y una descripción. Haz clic en `CREAR Y CONTINUAR`.
4.  En el paso de "roles", asígnale el rol de **Editor** para que pueda modificar tus archivos de Google. Haz clic en `CONTINUAR` y luego en `LISTO`.

### Paso 1.3: Obtener las Credenciales (`GOOGLE_CREDENTIALS_JSON`)

1.  En la lista de cuentas de servicio, busca la que acabas de crear y haz clic en ella.
2.  Ve a la pestaña `CLAVES`.
3.  Haz clic en `AGREGAR CLAVE` > `Crear clave nueva`.
4.  Selecciona el tipo **JSON** y haz clic en `CREAR`. Se descargará un archivo `.json` a tu computadora.
5.  Abre el archivo `.json` que descargaste con un editor de texto (como VS Code o Bloc de notas).
6.  Copia **todo el contenido** del archivo.
7.  Pega ese contenido como el valor de `GOOGLE_CREDENTIALS_JSON` en tu archivo `.env`. Debe ser una sola línea larga.

    ```dotenv
    GOOGLE_CREDENTIALS_JSON={"type": "service_account", "project_id": "...", ...}
    ```

### Paso 1.4: Obtener el ID de la Hoja de Cálculo (`GOOGLE_SHEET_ID`)

1.  Crea una nueva hoja de cálculo en Google Sheets.
2.  Mira la URL en la barra de direcciones de tu navegador. Tendrá este formato:
    `https://docs.google.com/spreadsheets/d/`**`ESTE_ES_EL_ID_LARGO`**`/edit`
3.  Copia esa parte del medio (la cadena larga de letras y números) y pégala como el valor de `GOOGLE_SHEET_ID` en tu archivo `.env`.

    ```dotenv
    GOOGLE_SHEET_ID=1a2b3c4d_5e6f7g8h_ESTE_ES_EL_ID_DE_TU_HOJA
    ```

### Paso 1.5: Compartir la Hoja de Cálculo

**¡Este paso es crucial!** Debes dar permiso a tu "usuario robot" para que edite la hoja.

1.  Abre tu archivo de credenciales `.json` y busca el valor de `"client_email"`. Será algo como `api-certificados@tu-proyecto.iam.gserviceaccount.com`.
2.  En tu Google Sheet, haz clic en el botón verde `Compartir` (arriba a la derecha).
3.  Pega esa dirección de correo en el campo y asígnale permisos de **Editor**. Haz clic en `Enviar`.

---

## 2. Configuración de Autenticación (JWT)

### `JWT_SECRET_KEY`

Esta es una clave secreta para firmar los tokens de seguridad de los usuarios. **Nunca uses la clave por defecto.**

**Cómo generar una clave segura:**
Puedes ejecutar este comando en tu terminal y copiar el resultado:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Pega el resultado en tu archivo `.env`:
```dotenv
JWT_SECRET_KEY=f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8
```

---

## 3. Configuración de Email

Esta sección es para que la aplicación pueda enviar los certificados por correo.

### `EMAIL_SENDER`

Tu dirección de correo electrónico desde la cual se enviarán los certificados (ej. `tu.correo@gmail.com`).

### `EMAIL_PASSWORD`

**¡No es tu contraseña normal!** Si usas Gmail, necesitas una **"Contraseña de Aplicación"**.

**Cómo obtener una Contraseña de Aplicación en Gmail:**
1.  Ve a la configuración de tu Cuenta de Google: https://myaccount.google.com/
2.  Asegúrate de tener la **Verificación en dos pasos** activada (es un requisito). La encuentras en la sección `Seguridad`.
3.  En la misma sección de `Seguridad`, busca y haz clic en `Contraseñas de aplicaciones`.
4.  Crea una nueva: selecciona "Correo" como la aplicación y "Otro (nombre personalizado)" como el dispositivo. Dale un nombre como "API Certificados".
5.  Google te dará una contraseña de 16 letras. **Cópiala inmediatamente** (no podrás verla de nuevo) y pégala en `EMAIL_PASSWORD` en tu archivo `.env`.

    ```dotenv
    EMAIL_PASSWORD=abdcdefghijklmno
    ```

---

## 4. Configuración de Flask

Los valores por defecto son ideales para el desarrollo. No necesitas cambiarlos para empezar.

```dotenv
FLASK_ENV=development
FLASK_PORT=5000
FLASK_DEBUG=True
```

---

## 5. Inicialización

Una vez que tu archivo `.env` esté completo y guardado, abre una terminal en la carpeta del proyecto y ejecuta:

1.  **Inicializa la base de datos y crea el usuario admin**:
    ```bash
    python init_db.py
    ```
    Sigue las instrucciones para crear tu cuenta de administrador.

2.  **Inicia el servidor de la API**:
    ```bash
    python app.py
    ```

¡Listo! Tu API estará corriendo en `http://localhost:5000`.