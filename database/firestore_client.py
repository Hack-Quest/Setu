import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv("config/.env")

cert_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not cert_path:
    cert_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "config", "serviceAccountKey.json"
        )
    )

if not firebase_admin._apps:
    cred = credentials.Certificate(cert_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

print("✅ Firestore Client Initialized Successfully")
