# Citizens Chatbot - One Command Startup
# Run this script to reset and start the entire system

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Citizens Chatbot - Full System Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# BACKEND SETUP
# ============================================
Write-Host ">>> Setting up BACKEND..." -ForegroundColor Yellow
Set-Location $backendDir

Write-Host "  [1/3] Cleaning Python cache..." -ForegroundColor Gray
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "  [2/3] Installing requirements..." -ForegroundColor Gray
pip install -q -r requirements.txt

Write-Host "  [3/3] Starting backend server (port 8000)..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:backendDir
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} -Name "Backend"

Write-Host "  ✓ Backend started in background" -ForegroundColor Green
Write-Host ""

# ============================================
# FRONTEND SETUP
# ============================================
Write-Host ">>> Setting up FRONTEND..." -ForegroundColor Yellow
Set-Location $frontendDir

Write-Host "  [1/3] Cleaning node modules..." -ForegroundColor Gray
if (Test-Path "node_modules") {
    Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
}
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
}

Write-Host "  [2/3] Installing dependencies..." -ForegroundColor Gray
npm install --quiet

Write-Host "  [3/3] Starting frontend server (port 3000)..." -ForegroundColor Green
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:frontendDir
    $env:PORT = 3000
    npm run dev
} -Name "Frontend"

Write-Host "  ✓ Frontend started in background" -ForegroundColor Green
Write-Host ""

# ============================================
# SERVER STATUS
# ============================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SYSTEM STARTUP COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services starting up. Please wait 15-30 seconds..." -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "📋 Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Running jobs:" -ForegroundColor Cyan
Get-Job | Select-Object Name, State | Format-Table -AutoSize
Write-Host ""
Write-Host "To view backend logs:  Get-Job -Name Backend | Receive-Job -Keep" -ForegroundColor Gray
Write-Host "To view frontend logs: Get-Job -Name Frontend | Receive-Job -Keep" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop all services: Stop-Job -Name Backend,Frontend" -ForegroundColor Gray
Write-Host ""
