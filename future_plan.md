# 🚀 SETU — Future Development Plan & Local Setup Guide

> **Target Audience:** Engineering Team & Project Contributors  
> **Goal:** Run SETU locally with **Zero Paid API Dependencies** and set up a **Local/Free Database Infrastructure**.

---

## 📌 Executive Summary

This document outlines the roadmap for running the SETU platform completely free of paid API keys (such as Google Maps or paid Gemini API keys) and establishing a local database environment. 

---

## 📜 1. Recent Accomplishments (Git Commit Overview)

To keep everyone up to speed on what has been built and how the codebase evolved:

* **AI Processing Refactor (`b2aa1b0`)**: Integrated the latest `google-genai` SDK (`gemini-2.0-flash`) with automatic fallback to **Groq API** (`llama-3.3-70b-versatile`) and a safe static default dictionary.
* **Modern UI & Tactical Map (`87f7a9e`, `8bb0386`)**: Replaced the front end with a modern design system (`frontendnew/`) featuring an interactive map using **Leaflet.js + OpenStreetMap** (`map.html`).
* **Hybrid Geocoding (`b429bb7`, `4704a23`)**: Updated `database/geocoding.py` so that if Google Maps is unavailable or unconfigured, it automatically falls back to **OpenStreetMap (Nominatim)**.
* **Cloud-Native Auth & Emulator Support (`90d1716`)**: Added support for Google Application Default Credentials (ADC) and local **Firestore Emulator** detection (`FIRESTORE_EMULATOR_HOST`).
* **Smart Matching & Tiered Volunteer View (`a255561`, `e963857`)**: Connected the proximity matching engine (`/match`) and categorized responders into Tier 1 (NGO-verified) and Tier 2 (Community).

---

## 🔑 2. Transitioning Off Paid Google APIs (100% Free Setup)

### A. AI Emergency Classification (Replacing Paid Gemini)
* **Current Status:** `ai_processing/gemini_processor.py` relies on `GEMINI_API_KEY`.
* **Team Action Plan:**
  1. **Option 1 — Free Tier Groq API (Easiest)**: Obtain a free API key from [Groq Console](https://console.groq.com/) and set `GROQ_API_KEY` in `config/.env`. Groq fallback logic is already built in!
  2. **Option 2 — Local Ollama (Zero API Cost)**: Install [Ollama](https://ollama.com/) locally and run `ollama run llama3.2` or `qwen2.5`. Update `gemini_processor.py` to call `http://localhost:11434/v1/chat/completions`.
  3. **Option 3 — Local Keyword/Rule Classifier**: Implement a basic rule-based backup function using regex/keyword matching (e.g. searching for `"medical"`, `"trapped"`, `"flood"`, `"rescue"`) to process reports completely offline.

### B. Maps & Geocoding (Replacing Paid Google Maps)
* **Current Status:** `database/geocoding.py` checks `GOOGLE_MAPS_KEY` first.
* **Team Action Plan:**
  1. **Backend Geocoding:** Modify `database/geocoding.py` to default directly to **OpenStreetMap (Nominatim)**, bypassing Google Maps entirely.
  2. **Backend Config Endpoint:** Update `backend/main.py` (`GET /config/public`) so it does not throw a `503` error when no `GOOGLE_MAPS_KEY` is present.
  3. **Frontend Tactical Map:** `frontendnew/map.html` **already uses Leaflet + OpenStreetMap tiles** for plotting disaster markers. No changes required!
  4. **Map Links:** Update direct link generation in `frontendnew/js/volunteer.js` to point to OpenStreetMap (`https://www.openstreetmap.org/search?query=...`).

---

## 🗄️ 3. Database Infrastructure Plan

The application requires 5 data collections/tables:
1. `needs_reports` (Distress requests, location, severity, status)
2. `volunteers` (Name, contact, skills, coordinates, availability)
3. `assignments` (Dispatches connecting volunteers to needs)
4. `ngos` (Registered organizations and verification status)
5. `otps` (One-time auth tokens with expiration timestamps)

### Recommended Database Solutions:

#### Option 1: Local Firebase / Firestore Emulator (Recommended — 0 Code Changes)
Because `database/firestore_client.py` already supports `FIRESTORE_EMULATOR_HOST`, you can run a local Firestore database with zero code modifications:
1. Install Node.js & Firebase Tools: `npm install -g firebase-tools`
2. Start local emulator: `firebase emulators:start --only firestore`
3. Add the following to your local `config/.env`:
   ```env
   FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"
   FIREBASE_PROJECT_ID="setu-local"
   ```
4. Seed mock data: `python database/ingest.py`

#### Option 2: SQLite Local Database (100% Offline & File-Based)
If the team wants to avoid Java/Firebase dependencies completely:
* Refactor `database/*_db.py` files to use Python's built-in `sqlite3` driver.
* Data will be saved in a local file (`database/setu.db`).
* Requires no background servers, accounts, or setup commands.

#### Option 3: PostgreSQL + PostGIS (Production Readiness)
For scaling or advanced spatial queries:
* Run PostgreSQL with PostGIS in Docker:
  ```bash
  docker run -d --name setu-db -p 5432:5432 -e POSTGRES_PASSWORD=setu postgis/postgis
  ```
* Leverage SQL spatial functions (`ST_Distance`) for high-precision volunteer proximity matching.

---

## 📋 4. Team Action Checklist

- [ ] **Setup `.env`**: Copy `config/.env.example` to `config/.env`.
- [ ] **Choose AI Backend**: Add a free `GROQ_API_KEY` or start local Ollama.
- [ ] **Choose Database Option**:
  - Run `firebase emulators:start --only firestore` (Option 1)
  - OR implement the SQLite database wrapper (Option 2).
- [ ] **Run Backend**: `uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload`
- [ ] **Run Frontend**: `python -m http.server 3000 --directory frontendnew`
- [ ] **Verify Map & Matching**: Open `http://localhost:3000/map.html` and click **Run Matching**.

---

*Document compiled for SETU Development Team.*
