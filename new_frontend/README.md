# SETU AI - New Professional Frontend

This is the primary professional minimalist UI for the SETU emergency response coordination system.

## 🎨 Design Philosophy

- **Minimalist & Professional**: Deep Navy (#0b1326), Slate Gray (#4a5f7f), and Safety Orange (#ff6b35)
- **Data-Focused**: Clear, readable information without unnecessary animations
- **Emergency-Grade**: Clean layout designed for high-stress response scenarios
- **Single-Page App**: Seamless navigation between Dashboard, Report, Volunteer, and Match Engine

## 🚀 Getting Started

### Prerequisites
- Backend running: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- This folder served via HTTP

### Launch
```bash
cd new_frontend
python -m http.server 5500 --bind 127.0.0.1
```

Then open: **http://127.0.0.1:5500/index.html**

## 📋 Sections

### 1. **Dashboard**
- Live statistics: Open Needs, Volunteers, Critical/High Priority cases
- Recent report preview
- Auto-refreshes every 30 seconds
- No authentication required for display

### 2. **Report Need**
- Submit emergency reports with full details
- AI processes reports for category, severity, and trust score
- Displays dispatch action recommendation (auto_dispatch, human_review, flagged)
- Shows detailed trust scoring reasons
- **Auth**: Bearer token: `hackathon-secret`

### 3. **Volunteer Registration**
- Register available responders with skills
- Auto-geocodes location
- Tracks total active volunteers
- **Auth**: Bearer token: `hackathon-secret`

### 4. **Match Engine**
- Runs intelligent volunteer-to-need matching
- Uses Haversine distance for proximity matching
- Filters by skills and trust score
- Displays assignments with distance and status
- **Auth**: Bearer token: `hackathon-secret`

## 🔐 Authentication

All API endpoints that require auth use:
```
Authorization: Bearer hackathon-secret
```

This is configured globally in `api.js` and automatically included in all POST/GET requests.

## 📁 Files

- **index.html** - Main single-page application with all sections and styling
- **api.js** - Centralized API client with global auth header handling
- **README.md** - This file

## 🔧 Technical Integration

### API Endpoints Used

1. `POST /need` - Submit emergency report
   - Input: reporter_name, reporter_phone, location_text, disaster_type, help_needed, description
   - Output: Full need object with trust_score, dispatch_action, priority

2. `POST /volunteer` - Register volunteer
   - Input: name, phone, location, skills
   - Output: message, total_volunteers count

3. `GET /match` - Run match engine
   - Output: total_matches_made, matches array

4. `GET /dashboard` - Get statistics (no auth required by backend)
   - Output: total_needs, total_volunteers, priority counts, recent_need

### Backend Features (Preserved)

- ✅ Gemini/Groq AI fallback system
- ✅ Multi-layer trust scoring
- ✅ Haversine distance matching
- ✅ Firestore persistence
- ✅ Weather API correlation
- ✅ Corroboration checking
- ✅ Email alerts on auto-dispatch

## 🎯 UI/UX Highlights

- **Professional Color Scheme**: Deep Navy background with Safety Orange accents for critical alerts
- **Clear Data Hierarchy**: Large, readable stats and structured forms
- **Instant Feedback**: Success/error messages on all actions
- **Real-Time Updates**: Dashboard auto-refreshes and Match results display instantly
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices
- **Accessibility**: Clear labels, proper form semantics, readable contrast

## 🚫 Deprecated

The original `frontend/` folder is no longer the primary UI. This `new_frontend/` is the production interface.

---

**SETU AI v1.0** | Emergency Response Coordination System | 2026
