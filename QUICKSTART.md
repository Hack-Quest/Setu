# SETU AI - Complete Integration Quickstart

## ✅ Status: Backend Running on Port 8000

Your backend is **live and responding** with all 4 endpoints operational:
- ✅ Health check (`/health`) - 200 OK
- ✅ Dashboard (`/dashboard`) - 33 needs, 21 volunteers
- ✅ Volunteer registration (`POST /volunteer`) - Auth working
- ✅ Need submission (`POST /need`) - Auth working
- ✅ Match engine (`GET /match`) - Auth working

---

## 🚀 Complete Setup Instructions

### Step 1: Start Backend (Already Running ✓)
```powershell
# Port 8000 - Backend API
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Step 2: Start Frontend Server (REQUIRED)
```powershell
# Open NEW terminal (Terminal 2)
cd C:\Users\bigbo\OneDrive\Documents\Setu
python -m http.server 5500 --bind 127.0.0.1
```
Expected output:
```
Serving HTTP on 127.0.0.1:5500...
```

### Step 3: Open New Professional UI
```
http://127.0.0.1:5500/new_frontend/index.html
```

---

## 🧪 Testing the Integration

### Option A: Browser Testing (Recommended)
1. Go to **http://127.0.0.1:5500/new_frontend/index.html**
2. Click **Dashboard** tab → See live stats
3. Click **Report Need** tab → Fill form → Submit
4. Click **Volunteer** tab → Fill form → Submit
5. Click **Match Engine** tab → Click button → See assignments

### Option B: PowerShell Script Testing
```powershell
# Run comprehensive API tests
.\test_integration.ps1
```

### Option C: Manual curl Commands
```powershell
# Health check
curl.exe -s http://127.0.0.1:8000/health

# Dashboard (public)
curl.exe -s http://127.0.0.1:8000/dashboard

# Register volunteer (with auth)
$vol = @{name="Test";phone="9876543210";location="Test";skills="rescue"}
curl.exe -s -X POST http://127.0.0.1:8000/volunteer `
  -H "Authorization: Bearer hackathon-secret" `
  -H "Content-Type: application/json" `
  -d ($vol | ConvertTo-Json)
```

---

## 📊 What You'll See

### Dashboard
- **Open Needs**: 33 (from live Firestore)
- **Volunteers**: 21 active
- **Critical Cases**: 2 
- **High Priority**: 7
- **Recent Report**: Shows latest need with trust_score and dispatch_action

### Report Need Form
Submit with:
- Reporter Name: "Test User"
- Phone: "9876543210"
- Location: "Lucknow, India"
- Disaster: "flood"
- Help Needed: "rescue"
- Description: "Water overflowing, need assistance" (min 10 chars)

**Response shows**:
- Category (AI-detected)
- Severity (critical/high/medium/low)
- Trust Score (0-100)
- Dispatch Action (auto_dispatch/human_review/flagged)
- Priority (HIGH/MEDIUM/LOW)
- Trust Reasons (geocoding, phone validation, AI consistency, weather correlation, corroboration)

### Volunteer Registration
Submit with:
- Name: "John Rescue"
- Phone: "9876543211"
- Location: "Mumbai, Maharashtra"
- Skills: "rescue, medical"

**Response shows**:
- Confirmation message
- Total active volunteers updated

### Match Engine
- Click "Run Match Engine" button
- AI matches volunteers to needs based on:
  - Skill intersection
  - Distance (50km radius)
  - Trust score (needs ≥50)
  - Volunteer availability
- Displays: Total matches + list with distance and status

---

## 🔐 Authentication

**All requests use Bearer token**:
```
Authorization: Bearer hackathon-secret
```

This is **automatically included** in the new_frontend UI - no manual token entry needed.

---

## 🎨 New Frontend Features

| Feature | Location | Status |
|---------|----------|--------|
| **Professional UI** | `new_frontend/` | ✅ Complete |
| **API Client** | `new_frontend/api.js` | ✅ Auto-auth |
| **Responsive Design** | `new_frontend/index.html` | ✅ Mobile-ready |
| **Live Dashboard** | Tab 1 | ✅ 30-sec auto-refresh |
| **Report Form** | Tab 2 | ✅ AI processing |
| **Volunteer Form** | Tab 3 | ✅ Geocoding |
| **Match Engine** | Tab 4 | ✅ Haversine matching |
| **Error Handling** | All tabs | ✅ Feedback messages |

---

## 🔧 Backend Features (Preserved)

- ✅ **Gemini→Groq Fallback**: If Gemini unavailable, auto-switch to Llama 3.3-70b
- ✅ **Trust Scoring**: Geocoding (10) + Phone (10) + AI (30) + Weather (20) + Corroboration (40)
- ✅ **Haversine Matching**: Calculates actual distance between volunteer and need
- ✅ **Firestore Persistence**: All data saved to cloud database
- ✅ **Email Alerts**: Sends Gmail notification on auto_dispatch
- ✅ **CORS Configured**: Frontend origin allowed

---

## 📁 Directory Structure

```
new_frontend/
  ├── index.html          (Main SPA with all tabs)
  ├── api.js              (Centralized API client)
  ├── README.md           (Documentation)
  └── new_frontend/       (Nested old structure - can ignore)

backend/
  ├── main.py             (FastAPI app with CORS)
  ├── models.py           (Pydantic schemas)
  ├── auth.py             (Bearer token verification)
  └── routes/
      ├── need.py         (POST /need - AI processing)
      ├── volunteer.py    (POST /volunteer - Geocoding)
      ├── match.py        (GET /match - Haversine matching)
      └── dashboard.py    (GET /dashboard - Live stats)

database/
  ├── firestore_client.py (Firebase connection)
  ├── needs_db.py
  ├── volunteers_db.py
  ├── geocoding.py        (Google Maps / OSM fallback)
  └── verification.py     (Trust score calculation)

ai_processing/
  └── gemini_processor.py (Gemini + Groq fallback)
```

---

## ⚠️ Troubleshooting

### "Connection refused" on port 8000?
```powershell
# Kill existing processes
Get-Process python | Stop-Process -Force

# Restart backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### API returns 401 (Unauthorized)?
- New frontend auto-includes token ✓
- Manual curl must use: `-H "Authorization: Bearer hackathon-secret"`

### POST /need timeout?
- Normal - AI processing takes 5-10 seconds
- Browser waits automatically
- Curl timeout can be increased: `--max-time 30`

### "JSON decode error" in POST?
- Use `Invoke-WebRequest` (PowerShell) or `requests` (Python)
- Direct curl with backticks in PowerShell causes escaping issues
- Use `test_integration.ps1` for reliable testing

### Firestore connection error?
- Backend tries env var `GOOGLE_APPLICATION_CREDENTIALS` first
- Falls back to `config/serviceAccountKey.json`
- Check that file exists and is valid JSON

---

## ✨ Next Steps

### For Testing
1. ✅ Backend running on 8000
2. ⏳ **[NEXT]** Start frontend server on 5500
3. ⏳ **[NEXT]** Open http://127.0.0.1:5500/new_frontend/index.html
4. ⏳ **[NEXT]** Test each tab with sample data

### For Deployment
1. Push to GitHub
2. Deploy backend to Heroku/GCP/AWS
3. Deploy frontend to GitHub Pages/Netlify
4. Update API endpoint in `new_frontend/api.js`

### For Production
1. Move API key to environment variables
2. Enable rate limiting
3. Add user authentication (OAuth2)
4. Set up monitoring & logging
5. Enable HTTPS

---

## 📞 Support

Backend endpoints: `http://127.0.0.1:8000`
- `/health` - Status check
- `/dashboard` - Public stats
- `/need` - Requires auth
- `/volunteer` - Requires auth
- `/match` - Requires auth

Frontend: `http://127.0.0.1:5500/new_frontend/index.html`

---

**SETU AI v1.0** | Emergency Response Coordination | 2026
