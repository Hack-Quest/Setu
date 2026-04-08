import time
from database.needs_db import save_need, get_open_needs
from database.volunteers_db import save_volunteer, get_available_volunteers
from database.assignments_db import save_assignment, resolve_assignment

print("🚀 STARTING DATABASE SMOKE TEST...\n")

# --- 1. Testing Needs ---
print("--- 1. Testing Needs ---")
need_data = {
    "description": "Flood victims trapped on roof, need rescue boat.",
    "severity": "critical",
    "category": "rescue",
    "lat": 26.8467,
    "lng": 80.9462
}
fake_need_id = save_need(need_data)

# 🚨 RUN NEED ASSERTIONS HERE (While it is still open!)
assert fake_need_id is not None, "🚨 Need ID should not be None!"
assert len(get_open_needs()) >= 1, "🚨 Should have at least 1 open need!"

print(f"Open Needs List: {len(get_open_needs())} items found.\n")

# --- 2. Testing Volunteers ---
print("--- 2. Testing Volunteers ---")
volunteer_data = {
    "name": "Animesh (Test)",
    "skills": ["rescue", "medical"],
    "phone": "+91-9876543210",
    "lat": 26.8500,
    "lng": 80.9500
}
fake_vol_id = save_volunteer(volunteer_data)

# 🚨 RUN VOLUNTEER ASSERTION HERE
assert fake_vol_id is not None, "🚨 Volunteer ID should not be None!"

print(f"Available Volunteers List: {len(get_available_volunteers())} people found.\n")

# --- 3. Testing Assignments ---
print("--- 3. Testing Assignments ---")
print("Assigning volunteer to the rescue mission...")
assignment_id = save_assignment(fake_need_id, fake_vol_id)

time.sleep(1)

assert len([n for n in get_open_needs() if n["id"] == fake_need_id]) == 0, "🚨 Need should no longer be open after assignment!"

# --- 4. Testing Resolution ---
print("\n--- 4. Testing Resolution ---")
print("Mission accomplished! Resolving the assignment...")
resolve_assignment(assignment_id, fake_need_id, fake_vol_id)

print("\n🎉 ALL TESTS PASSED! YOUR DATABASE IS PRODUCTION-READY!")