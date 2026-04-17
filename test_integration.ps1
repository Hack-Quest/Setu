#!/usr/bin/env powershell
<#
.SYNOPSIS
Integration test script for SETU AI platform
Tests all 4 API endpoints with proper JSON formatting
#>

$BASE_URL = "http://127.0.0.1:8000"
$TOKEN = "hackathon-secret"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "SETU AI Integration Test Suite" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Helper function to test endpoints
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body,
        [switch]$RequireAuth
    )
    
    $url = "$BASE_URL$Endpoint"
    $headers = @{ "Content-Type" = "application/json" }
    
    if ($RequireAuth) {
        $headers["Authorization"] = "Bearer $TOKEN"
    }
    
    Write-Host "`n[$Method] $Endpoint" -ForegroundColor Yellow
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Uri $url -Method GET -Headers $headers -ErrorAction Stop
        } else {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-WebRequest -Uri $url -Method $Method -Headers $headers -Body $jsonBody -ErrorAction Stop
        }
        
        $data = $response.Content | ConvertFrom-Json
        Write-Host "✓ Status: $($response.StatusCode)" -ForegroundColor Green
        Write-Host "Response:" -ForegroundColor Cyan
        $data | Format-List
        return $true
    } catch {
        Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
        return $false
    }
}

# Test 1: Health Check
Write-Host "`n=== 1. Health Check ===" -ForegroundColor Cyan
Test-Endpoint -Name "Health" -Method "GET" -Endpoint "/health"

# Test 2: Dashboard (No Auth)
Write-Host "`n=== 2. Dashboard Stats ===" -ForegroundColor Cyan
Test-Endpoint -Name "Dashboard" -Method "GET" -Endpoint "/dashboard"

# Test 3: Volunteer Registration (With Auth)
Write-Host "`n=== 3. Register Volunteer ===" -ForegroundColor Cyan
$volPayload = @{
    name = "Integration Test Volunteer"
    phone = "9876543210"
    location = "Mumbai, Maharashtra"
    skills = @("rescue", "medical", "food")
}
Test-Endpoint -Name "Volunteer" -Method "POST" -Endpoint "/volunteer" -Body $volPayload -RequireAuth

# Test 4: Submit Need Report (With Auth)
Write-Host "`n=== 4. Submit Need Report ===" -ForegroundColor Cyan
$needPayload = @{
    reporter_name = "Integration Test"
    reporter_phone = "9876543211"
    location_text = "Bangalore, Karnataka"
    disaster_type = "flood"
    help_needed = "rescue"
    description = "Integration test for flood response system with multiple affected families in need of immediate assistance and rescue operations"
}
Test-Endpoint -Name "Need" -Method "POST" -Endpoint "/need" -Body $needPayload -RequireAuth

# Test 5: Match Engine (With Auth)
Write-Host "`n=== 5. Run Match Engine ===" -ForegroundColor Cyan
Test-Endpoint -Name "Match" -Method "GET" -Endpoint "/match" -RequireAuth

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Integration Tests Complete" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "`nNext Step: Open http://127.0.0.1:5500/new_frontend/index.html in browser" -ForegroundColor Green
