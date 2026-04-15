"""
Integration Test Suite for SETU AI Platform
Tests all endpoints with new_frontend payloads and expected responses
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
TOKEN = "hackathon-secret"
TIMEOUT = 30

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_result(name, passed, message=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} | {name}")
    if message:
        print(f"     {Colors.BLUE}→{Colors.END} {message}")

def test_dashboard():
    """Test GET /dashboard (public endpoint, no auth needed)"""
    print(f"\n{Colors.YELLOW}Testing Dashboard Endpoint{Colors.END}")
    try:
        resp = requests.get(f"{BASE_URL}/dashboard", timeout=TIMEOUT)
        passed = resp.status_code == 200
        test_result("GET /dashboard", passed, f"Status: {resp.status_code}")
        
        if passed:
            data = resp.json()
            required_fields = ['total_needs', 'total_volunteers', 'critical_priority_cases', 'high_priority_cases']
            all_present = all(field in data for field in required_fields)
            test_result("Dashboard fields present", all_present, 
                       f"Needs: {data.get('total_needs')}, Volunteers: {data.get('total_volunteers')}")
            return True
    except Exception as e:
        test_result("GET /dashboard", False, str(e))
    return False

def test_health():
    """Test GET / (health check)"""
    print(f"\n{Colors.YELLOW}Testing Health Endpoint{Colors.END}")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        passed = resp.status_code == 200
        test_result("GET / (health)", passed, f"Status: {resp.status_code}")
        return passed
    except Exception as e:
        test_result("GET / (health)", False, str(e))
    return False

def test_volunteer_registration():
    """Test POST /volunteer with new_frontend payload"""
    print(f"\n{Colors.YELLOW}Testing Volunteer Registration{Colors.END}")
    
    payload = {
        "name": "Integration Test Volunteer",
        "phone": "+91-9876543210",
        "location": "Mumbai, Maharashtra",
        "skills": ["rescue", "medical"]
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/volunteer",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        passed = resp.status_code == 200
        test_result("POST /volunteer", passed, f"Status: {resp.status_code}")
        
        if passed:
            data = resp.json()
            has_count = 'total_volunteers' in data
            test_result("Total volunteers count returned", has_count,
                       f"Total: {data.get('total_volunteers')}")
            return True
    except Exception as e:
        test_result("POST /volunteer", False, str(e))
    return False

def test_need_submission():
    """Test POST /need with new_frontend payload"""
    print(f"\n{Colors.YELLOW}Testing Need Submission{Colors.END}")
    
    payload = {
        "reporter_name": "Integration Test Reporter",
        "reporter_phone": "+91-9876543211",
        "location_text": "Bangalore, Karnataka",
        "disaster_type": "flood",
        "help_needed": "rescue",
        "description": "Integration test for flood response system with multiple affected families in need of immediate assistance"
    }
    
    try:
        print(f"     {Colors.BLUE}→{Colors.END} Processing (Gemini/Groq AI required, may be slow)...")
        resp = requests.post(
            f"{BASE_URL}/need",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        passed = resp.status_code == 200
        test_result("POST /need", passed, f"Status: {resp.status_code}")
        
        if passed:
            data = resp.json()
            required_fields = ['trust_score', 'dispatch_action', 'priority', 'category', 'severity']
            all_present = all(field in data for field in required_fields)
            test_result("Response has required fields", all_present)
            
            if all_present:
                test_result("Trust score valid", 0 <= data['trust_score'] <= 100,
                           f"Score: {data['trust_score']}")
                test_result("Dispatch action valid", data['dispatch_action'] in ['auto_dispatch', 'human_review', 'flagged'],
                           f"Action: {data['dispatch_action']}")
            return True
    except requests.Timeout:
        test_result("POST /need", False, "Timeout (AI processing took >30s, likely API quota)")
    except Exception as e:
        test_result("POST /need", False, str(e))
    return False

def test_match_engine():
    """Test GET /match"""
    print(f"\n{Colors.YELLOW}Testing Match Engine{Colors.END}")
    try:
        resp = requests.get(
            f"{BASE_URL}/match",
            headers=headers,
            timeout=TIMEOUT
        )
        passed = resp.status_code == 200
        test_result("GET /match", passed, f"Status: {resp.status_code}")
        
        if passed:
            data = resp.json()
            has_count = 'total_matches_made' in data
            test_result("Matches count returned", has_count,
                       f"Total: {data.get('total_matches_made', 'N/A')}")
            return True
    except Exception as e:
        test_result("GET /match", False, str(e))
    return False

def test_auth_validation():
    """Test that endpoints reject missing/invalid auth tokens"""
    print(f"\n{Colors.YELLOW}Testing Authentication{Colors.END}")
    
    # Test without token
    try:
        resp = requests.get(f"{BASE_URL}/match", timeout=TIMEOUT)
        no_token_rejected = resp.status_code in [401, 403]
        test_result("Missing auth token rejected", no_token_rejected, f"Status: {resp.status_code}")
    except Exception as e:
        test_result("Missing auth token test", False, str(e))
    
    # Test with invalid token
    try:
        bad_headers = {"Authorization": "Bearer invalid-token"}
        resp = requests.get(f"{BASE_URL}/match", headers=bad_headers, timeout=TIMEOUT)
        bad_token_rejected = resp.status_code in [401, 403]
        test_result("Invalid auth token rejected", bad_token_rejected, f"Status: {resp.status_code}")
    except Exception as e:
        test_result("Invalid auth token test", False, str(e))

def test_cors():
    """Test CORS headers for new_frontend origin"""
    print(f"\n{Colors.YELLOW}Testing CORS Configuration{Colors.END}")
    try:
        resp = requests.get(
            f"{BASE_URL}/dashboard",
            headers={"Origin": "http://127.0.0.1:5500"}
        )
        has_cors = 'access-control-allow-origin' in resp.headers
        test_result("CORS headers present", has_cors,
                   f"Allow-Origin: {resp.headers.get('access-control-allow-origin', 'N/A')}")
    except Exception as e:
        test_result("CORS test", False, str(e))

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"SETU AI Integration Test Suite")
    print(f"{'='*60}{Colors.END}")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run tests
    results.append(("Health", test_health()))
    results.append(("Dashboard", test_dashboard()))
    results.append(("CORS", test_cors()))
    results.append(("Auth", test_auth_validation()))
    results.append(("Volunteer", test_volunteer_registration()))
    results.append(("Match Engine", test_match_engine()))
    results.append(("Need Submission", test_need_submission()))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"Summary{Colors.END}")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if result else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {name}")
    
    print(f"\n{Colors.BLUE}Score: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}All systems operational! ✓{Colors.END}\n")
    elif passed >= total - 2:
        print(f"{Colors.YELLOW}Most systems operational (check AI API quotas){Colors.END}\n")
    else:
        print(f"{Colors.RED}System issues detected{Colors.END}\n")

if __name__ == "__main__":
    main()
