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
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        print(f"[INFO] Connecting to Firestore Emulator at {os.getenv('FIRESTORE_EMULATOR_HOST')}", flush=True)
        firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
    else:
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
            # Test getting the client to trigger credential loading
            _ = firestore.client()
            print("[OK] Firestore Client: initialized via ADC", flush=True)
        except Exception as e:
            print(f"[WARN] ADC failed ({e}). Falling back to project-only init.", flush=True)
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
            firebase_admin.initialize_app(options={"projectId": PROJECT_ID})

try:
    db = firestore.client()
    print("[OK] Firestore Client Initialized Successfully")
except Exception as e:
    print("\n❌ ERROR: Failed to initialize Firestore Client.")
    print("If you are running locally, please ensure that you have either:")
    print("  1. Authenticated with Google Cloud: Run `gcloud auth application-default login` in your terminal.")
    print("  2. Set up a local Firestore Emulator: Run the emulator and set the `FIRESTORE_EMULATOR_HOST` environment variable.")
    print(f"Details: {e}\n")
    raise e
