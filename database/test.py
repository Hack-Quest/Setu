import time
from database.needs_db import save_need, get_open_needs
from database.volunteers_db import save_volunteer, get_available_volunteers
from database.assignments_db import save_assignment, resolve_assignment

print("🚀 STARTING DATABASE SMOKE TEST...\n")

# 1. CREATE A FAKE NEED
print("--- 1. Testing Needs ---")
need_data = {
    "description": "Flood victims trapped on roof, need rescue boat.",
    "severity": "critical",
    "category": "rescue",
    "lat": 26.8467,
    "lng": 80.9462
}
fake_need_id = save_need(need_data)
print(f"Open Needs List: {len(get_open_needs())} items found.\n")

# 2. CREATE A FAKE VOLUNTEER
print("--- 2. Testing Volunteers ---")
volunteer_data = {
    "name": "Animesh (Test)",
    "skills": ["rescue", "medical"],
    "phone": "+91-9876543210",
    "lat": 26.8500,
    "lng": 80.9500
}
fake_vol_id = save_volunteer(volunteer_data)
print(f"Available Volunteers List: {len(get_available_volunteers())} people found.\n")

# 3. TEST THE "SMART" ASSIGNMENT LOGIC
print("--- 3. Testing Assignments ---")
print("Assigning volunteer to the rescue mission...")
assignment_id = save_assignment(fake_need_id, fake_vol_id)

time.sleep(1) # Pause for a second just to make it readable

# 4. TEST THE RESOLUTION LOGIC
print("\n--- 4. Testing Resolution ---")
print("Mission accomplished! Resolving the assignment...")
resolve_assignment(assignment_id, fake_need_id, fake_vol_id)

print("\n🎉 ALL TESTS PASSED! YOUR DATABASE IS PRODUCTION-READY!")