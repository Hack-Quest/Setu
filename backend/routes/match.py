from fastapi import APIRouter, Depends
# Note: In production, these imports must point to your real database files
# from backend.auth import verify_token
# from database.needs_db import get_open_needs
# from database.volunteers_db import get_available_volunteers
# from database.assignments_db import save_assignment

router = APIRouter()

@router.get("/match")
def match_needs(token: str = "test-token"): # Simplified for standalone testing
    matches = []
    open_needs = get_open_needs()

    for need in open_needs:
        # GUARD: Skip untrustworthy reports 
        if need.get("trust_score", 100) < 50:
            print(f"[Match] Skipping need {need.get('id')} — low trust score ({need.get('trust_score')}).")
            continue

        best_volunteer = None
        available_vols = get_available_volunteers()
        
        for vol in available_vols:
            # Skill match logic: Check if need category is in volunteer skills 
            if need.get("category") in vol.get("skills", []):
                # Basic proximity logic (Simplified)
                best_volunteer = vol
                break

        if best_volunteer:
            save_assignment(need.get("id"), best_volunteer.get("id"))
            matches.append({
                "need_id": need.get("id"),
                "assigned_volunteer": best_volunteer.get("name"),
                "status": "assigned"
            })

    return {
        "total_matches_made": len(matches),
        "matches": matches
    }

# ==========================================
# 🧪 TEST CASE SECTION (STANDALONE RUNNER)
# ==========================================

def get_open_needs():
    """Mocking database/needs_db.py"""
    return [
        {"id": "N1", "category": "medical", "trust_score": 90, "description": "Broken leg"},
        {"id": "N2", "category": "rescue", "trust_score": 20, "description": "Fake report"}, # Should be skipped
        {"id": "N3", "category": "food", "trust_score": 75, "description": "Hungry families"}
    ]

def get_available_volunteers():
    """Mocking database/volunteers_db.py"""
    return [
        {"id": "V1", "name": "Dr. Smith", "skills": ["medical"]},
        {"id": "V2", "name": "Rescue Team", "skills": ["rescue"]},
        {"id": "V3", "name": "Food Bank", "skills": ["food"]}
    ]

def save_assignment(need_id, vol_id):
    """Mocking database/assignments_db.py"""
    print(f"DEBUG: Saved Assignment in DB -> Need:{need_id} to Vol:{vol_id}")

if __name__ == "__main__":
    print("🚀 Starting Local Match Logic Test...\n")
    
    # Execute the function
    result = match_needs()
    
    print("\n--- Final Results ---")
    print(f"Total Matches: {result['total_matches_made']}")
    for m in result['matches']:
        print(f"✅ Assigned {m['need_id']} to {m['assigned_volunteer']}")
    
    # Assertions to verify correctness
    assert result['total_matches_made'] == 2, "Test Failed: Should have matched 2 needs (N1 and N3)."
    print("\n🎉 Test Passed: Trust guard worked (skipped N2) and skills matched correctly.")