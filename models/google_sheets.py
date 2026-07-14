"""
Modelo de datos usando Google Sheets como base de datos.

Hojas: 'usuarios', 'certificados', 'eventos', 'speakers'
"""

import json
import logging
import datetime
import uuid

import gspread
from config import Config

logger = logging.getLogger(__name__)


class GoogleSheetsDB:
    """Interfaz con Google Sheets como base de datos."""

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.users_sheet = None
        self.certs_sheet = None
        self.events_sheet = None
        self.speakers_sheet = None
        self._connected = False

    # ── Conexión ────────────────────────────────────────

    def connect(self):
        if self._connected:
            return True
        try:
            creds_json = Config.GOOGLE_CREDENTIALS_JSON
            if not creds_json:
                raise ValueError("GOOGLE_CREDENTIALS_JSON no está configurado")
            credentials = json.loads(creds_json)
            self.client = gspread.service_account_from_dict(credentials)
            self.spreadsheet = self.client.open_by_key(Config.GOOGLE_SHEET_ID)

            self._ensure_sheet("usuarios", self._USER_HEADERS)
            self._ensure_sheet("certificados", self._CERT_HEADERS)
            self._ensure_sheet("eventos", self._EVENT_HEADERS)
            self._ensure_sheet("speakers", self._SPEAKER_HEADERS)

            self.users_sheet = self.spreadsheet.worksheet("usuarios")
            self.certs_sheet = self.spreadsheet.worksheet("certificados")
            self.events_sheet = self.spreadsheet.worksheet("eventos")
            self.speakers_sheet = self.spreadsheet.worksheet("speakers")

            self._connected = True
            logger.info("Conexión exitosa a Google Sheets (4 hojas)")
            return True
        except Exception as e:
            logger.error(f"Error conectando a Google Sheets: {e}")
            raise

    def _ensure_sheet(self, sheet_name: str, headers: list):
        try:
            self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=25)
            ws.append_row(headers)
            logger.info(f"Hoja '{sheet_name}' creada con encabezados")

    # ── Encabezados ─────────────────────────────────────

    _USER_HEADERS = ["id", "nombre", "email", "password", "rol", "fecha_creacion"]

    _CERT_HEADERS = [
        "id", "nombre_completo", "email", "evento_id", "fecha_emision",
        "descripcion", "codigo_verif", "enviado", "fecha_envio", "creado_por"
    ]

    _EVENT_HEADERS = [
        "id", "nombre", "descripcion", "fecha", "color_primario",
        "color_secundario", "activo", "creado_por", "fecha_creacion"
    ]

    _SPEAKER_HEADERS = [
        "id", "nombre", "cargo", "email", "evento_id", "firma_base64", "firma_guardada"
    ]

    # ── Helpers ─────────────────────────────────────────

    @staticmethod
    def _safe_int(value, default=0):
        """Convierte un valor a int de forma segura. Si falla, retorna default."""
        try:
            return int(value) if value and str(value).strip() else default
        except (ValueError, TypeError):
            return default

    def _get_next_id(self, sheet) -> int:
        records = sheet.get_all_values()
        if len(records) <= 1:
            return 1
        return int(records[-1][0]) + 1

    def _row_to_dict(self, headers: list, row: list) -> dict:
        d = dict(zip(headers, row))
        # Rellenar campos faltantes si la fila es más corta que los headers
        for h in headers:
            if h not in d:
                d[h] = ""
        return d

    def _find_by_field(self, sheet, headers, field_name, value):
        try:
            records = sheet.get_all_values()
            if len(records) <= 1:
                return None
            field_index = headers.index(field_name)
            for row in records[1:]:
                if len(row) > field_index and row[field_index] == str(value):
                    return self._row_to_dict(headers, row)
            return None
        except Exception as e:
            logger.error(f"Error buscando: {e}")
            return None

    def _find_all_by_field(self, sheet, headers, field_name, value) -> list:
        try:
            records = sheet.get_all_values()
            if len(records) <= 1:
                return []
            field_index = headers.index(field_name)
            results = []
            for row in records[1:]:
                if len(row) > field_index and row[field_index] == str(value):
                    results.append(self._row_to_dict(headers, row))
            return results
        except Exception as e:
            logger.error(f"Error buscando múltiples: {e}")
            return []

    # ════════════════════════════════════════════════════
    #  USUARIOS (sin cambios)
    # ════════════════════════════════════════════════════

    def create_user(self, nombre, email, password_hash, rol="usuario"):
        self.connect()
        existing = self._find_by_field(self.users_sheet, self._USER_HEADERS, "email", email)
        if existing:
            raise ValueError(f"El email '{email}' ya está registrado")
        uid = self._get_next_id(self.users_sheet)
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.users_sheet.append_row([uid, nombre, email, password_hash, rol, fecha])
        return {"id": uid, "nombre": nombre, "email": email, "rol": rol, "fecha_creacion": fecha}

    def get_user_by_email(self, email):
        self.connect()
        return self._find_by_field(self.users_sheet, self._USER_HEADERS, "email", email)

    def get_all_users(self):
        self.connect()
        records = self.users_sheet.get_all_values()
        if len(records) <= 1:
            return []
        users = []
        for row in records[1:]:
            u = self._row_to_dict(self._USER_HEADERS, row)
            del u["password"]
            users.append(u)
        return users

    def delete_user(self, email):
        self.connect()
        records = self.users_sheet.get_all_values()
        idx = self._USER_HEADERS.index("email")
        for i, row in enumerate(records[1:], start=2):
            if len(row) > idx and row[idx] == email:
                self.users_sheet.delete_rows(i)
                return True
        return False

    # ════════════════════════════════════════════════════
    #  EVENTOS
    # ════════════════════════════════════════════════════

    def create_event(self, nombre, descripcion, fecha, color_primario,
                     color_secundario, creado_por):
        self.connect()
        eid = self._get_next_id(self.events_sheet)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [eid, nombre, descripcion, fecha, color_primario,
               color_secundario, "True", creado_por, now]
        self.events_sheet.append_row(row)
        logger.info(f"Evento creado: ID={eid} '{nombre}'")
        return {
            "id": eid, "nombre": nombre, "descripcion": descripcion,
            "fecha": fecha, "color_primario": color_primario,
            "color_secundario": color_secundario, "activo": True,
            "creado_por": creado_por, "fecha_creacion": now,
        }

    def get_event_by_id(self, event_id):
        self.connect()
        try:
            records = self.events_sheet.get_all_values()
            if len(records) <= 1:
                return None
            for row in records[1:]:
                if row[0] == str(event_id):
                    ev = self._row_to_dict(self._EVENT_HEADERS, row)
                    ev["id"] = self._safe_int(ev["id"])
                    ev["activo"] = ev.get("activo", "True") == "True"
                    return ev
            return None
        except Exception as e:
            logger.error(f"Error obteniendo evento: {e}")
            return None

    def get_all_events(self):
        self.connect()
        records = self.events_sheet.get_all_values()
        if len(records) <= 1:
            return []
        events = []
        for row in records[1:]:
            ev = self._row_to_dict(self._EVENT_HEADERS, row)
            ev["id"] = self._safe_int(ev["id"])
            ev["activo"] = ev.get("activo", "True") == "True"
            events.append(ev)
        return events

    def update_event(self, event_id, **kwargs):
        self.connect()
        records = self.events_sheet.get_all_values()
        if len(records) <= 1:
            return None
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(event_id):
                for col_idx, header in enumerate(self._EVENT_HEADERS, start=1):
                    if header in kwargs and kwargs[header] is not None:
                        self.events_sheet.update_cell(i, col_idx, str(kwargs[header]))
                return self.get_event_by_id(event_id)
        return None

    def delete_event(self, event_id):
        self.connect()
        records = self.events_sheet.get_all_values()
        if len(records) <= 1:
            return False
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(event_id):
                self.events_sheet.delete_rows(i)
                return True
        return False

    # ════════════════════════════════════════════════════
    #  SPEAKERS
    # ════════════════════════════════════════════════════

    def create_speaker(self, nombre, cargo, email, evento_id):
        self.connect()
        sid = self._get_next_id(self.speakers_sheet)
        row = [sid, nombre, cargo, email, evento_id, "", "False"]
        self.speakers_sheet.append_row(row)
        logger.info(f"Speaker creado: ID={sid} '{nombre}' para evento {evento_id}")
        return {
            "id": sid, "nombre": nombre, "cargo": cargo,
            "email": email, "evento_id": evento_id,
            "firma_base64": "", "firma_guardada": False,
        }

    def get_speaker_by_id(self, speaker_id):
        self.connect()
        records = self.speakers_sheet.get_all_values()
        if len(records) <= 1:
            return None
        for row in records[1:]:
            if row[0] == str(speaker_id):
                s = self._row_to_dict(self._SPEAKER_HEADERS, row)
                s["id"] = self._safe_int(s["id"])
                s["evento_id"] = self._safe_int(s.get("evento_id", 0))
                s["firma_guardada"] = s.get("firma_guardada", "False") == "True"
                return s
        return None

    def get_speakers_by_event(self, evento_id) -> list:
        self.connect()
        results = self._find_all_by_field(
            self.speakers_sheet, self._SPEAKER_HEADERS, "evento_id", evento_id
        )
        for s in results:
            s["id"] = self._safe_int(s["id"])
            s["evento_id"] = self._safe_int(s.get("evento_id", 0))
            s["firma_guardada"] = s.get("firma_guardada", "False") == "True"
        return results

    def get_all_speakers(self) -> list:
        self.connect()
        records = self.speakers_sheet.get_all_values()
        if len(records) <= 1:
            return []
        speakers = []
        for row in records[1:]:
            s = self._row_to_dict(self._SPEAKER_HEADERS, row)
            s["id"] = self._safe_int(s["id"])
            s["evento_id"] = self._safe_int(s.get("evento_id", 0))
            s["firma_guardada"] = s.get("firma_guardada", "False") == "True"
            speakers.append(s)
        return speakers

    def save_speaker_signature(self, speaker_id, firma_base64):
        self.connect()
        records = self.speakers_sheet.get_all_values()
        if len(records) <= 1:
            return False
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(speaker_id):
                firma_index = self._SPEAKER_HEADERS.index("firma_base64")
                guardada_index = self._SPEAKER_HEADERS.index("firma_guardada")
                self.speakers_sheet.update_cell(i, firma_index + 1, firma_base64)
                self.speakers_sheet.update_cell(i, guardada_index + 1, "True")
                logger.info(f"Firma guardada para speaker {speaker_id}")
                return True
        return False

    def update_speaker(self, speaker_id, **kwargs):
        self.connect()
        records = self.speakers_sheet.get_all_values()
        if len(records) <= 1:
            return None
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(speaker_id):
                for col_idx, header in enumerate(self._SPEAKER_HEADERS, start=1):
                    if header in kwargs and kwargs[header] is not None:
                        self.speakers_sheet.update_cell(i, col_idx, str(kwargs[header]))
                return self.get_speaker_by_id(speaker_id)
        return None

    def delete_speaker(self, speaker_id):
        self.connect()
        records = self.speakers_sheet.get_all_values()
        if len(records) <= 1:
            return False
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(speaker_id):
                self.speakers_sheet.delete_rows(i)
                return True
        return False

    # ════════════════════════════════════════════════════
    #  CERTIFICADOS (actualizado con evento_id)
    # ════════════════════════════════════════════════════

    def create_certificate(self, nombre_completo, email, evento_id,
                           fecha_emision, descripcion, creado_por):
        self.connect()
        cid = self._get_next_id(self.certs_sheet)
        codigo = self._generate_verification_code()
        row = [
            cid, nombre_completo, email, evento_id, fecha_emision,
            descripcion, codigo, "False", "", creado_por
        ]
        self.certs_sheet.append_row(row)
        logger.info(f"Certificado creado: ID={cid} para {nombre_completo}")
        return {
            "id": cid, "nombre_completo": nombre_completo, "email": email,
            "evento_id": evento_id, "fecha_emision": fecha_emision,
            "descripcion": descripcion, "codigo_verif": codigo,
            "enviado": False, "fecha_envio": "", "creado_por": creado_por,
        }

    def get_certificate_by_id(self, cert_id):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return None
        for row in records[1:]:
            if row[0] == str(cert_id):
                c = self._row_to_dict(self._CERT_HEADERS, row)
                c["enviado"] = c.get("enviado", "False") == "True"
                c["id"] = self._safe_int(c["id"])
                c["evento_id"] = self._safe_int(c.get("evento_id", 0))
                return c
        return None

    def get_certificate_by_code(self, code):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return None
        code_index = self._CERT_HEADERS.index("codigo_verif")
        for row in records[1:]:
            if len(row) > code_index and row[code_index] == code:
                c = self._row_to_dict(self._CERT_HEADERS, row)
                c["enviado"] = c.get("enviado", "False") == "True"
                c["id"] = self._safe_int(c["id"])
                c["evento_id"] = self._safe_int(c.get("evento_id", 0))
                return c
        return None

    def get_all_certificates(self):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return []
        certs = []
        for row in records[1:]:
            c = self._row_to_dict(self._CERT_HEADERS, row)
            c["enviado"] = c.get("enviado", "False") == "True"
            c["id"] = self._safe_int(c["id"])
            c["evento_id"] = self._safe_int(c.get("evento_id", 0))
            certs.append(c)
        return certs

    def get_certificates_by_creator(self, creado_por):
        self.connect()
        results = self._find_all_by_field(
            self.certs_sheet, self._CERT_HEADERS, "creado_por", creado_por
        )
        for c in results:
            c["enviado"] = c.get("enviado", "False") == "True"
            c["id"] = self._safe_int(c["id"])
            c["evento_id"] = self._safe_int(c.get("evento_id", 0))
        return results

    def get_certificates_by_event(self, evento_id):
        self.connect()
        results = self._find_all_by_field(
            self.certs_sheet, self._CERT_HEADERS, "evento_id", evento_id
        )
        for c in results:
            c["enviado"] = c.get("enviado", "False") == "True"
            c["id"] = self._safe_int(c["id"])
            c["evento_id"] = self._safe_int(c.get("evento_id", 0))
        return results

    def mark_as_sent(self, cert_id):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return False
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(cert_id):
                self.certs_sheet.update_cell(i, 8, "True")
                self.certs_sheet.update_cell(i, 9, fecha)
                return True
        return False

    def delete_certificate(self, cert_id):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return False
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(cert_id):
                self.certs_sheet.delete_rows(i)
                return True
        return False

    def update_certificate(self, cert_id, **kwargs):
        self.connect()
        records = self.certs_sheet.get_all_values()
        if len(records) <= 1:
            return None
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(cert_id):
                for col_idx, header in enumerate(self._CERT_HEADERS, start=1):
                    if header in kwargs and kwargs[header] is not None:
                        self.certs_sheet.update_cell(i, col_idx, str(kwargs[header]))
                return self.get_certificate_by_id(cert_id)
        return None

    @staticmethod
    def _generate_verification_code():
        short = uuid.uuid4().hex[:8].upper()
        ts = str(int(datetime.datetime.now().timestamp()))[-4:]
        return f"CERT-{short}-{ts}"


db = GoogleSheetsDB()