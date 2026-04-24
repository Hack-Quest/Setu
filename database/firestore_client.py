import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv("config/.env")

PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "project-ecb78041-2b9f-43b6-a06")

# ✅ Cloud-native init: uses Application Default Credentials (ADC).
# On Cloud Run this is the attached service account; locally it uses
# `gcloud auth application-default login`.  No serviceAccountKey.json needed.
if not firebase_admin._apps:
    try:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
        print("[OK] Firestore Client: initialized via ADC", flush=True)
    except Exception as e:
        print(f"[WARN] ADC failed ({e}). Falling back to project-only init.", flush=True)
        firebase_admin.initialize_app(options={"projectId": PROJECT_ID})

db = firestore.client()

print("[OK] Firestore Client Initialized Successfully")
