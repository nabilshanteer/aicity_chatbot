# Citizens Chatbot - System Reset
# Cleans up all artifacts and prepared state for fresh start

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "========================================" -ForegroundColor Red
Write-Host "Citizens Chatbot - FULL SYSTEM RESET" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "WARNING: This will delete:" -ForegroundColor Yellow
Write-Host "  - Python virtual environments and cache"
Write-Host "  - Node modules and build artifacts"
Write-Host "  - All temporary files"
Write-Host ""
$confirm = Read-Host "Type 'YES' to continue"

if ($confirm -ne "YES") {
    Write-Host "Reset cancelled." -ForegroundColor Gray
    exit
}

Write-Host ""

# Stop any running services
Write-Host ">>> Stopping any running services..." -ForegroundColor Yellow
Get-Job | Stop-Job -ErrorAction SilentlyContinue
Get-Job | Remove-Job -ErrorAction SilentlyContinue
Write-Host "✓ Services stopped" -ForegroundColor Green

# Backend cleanup
Write-Host ""
Write-Host ">>> Cleaning BACKEND..." -ForegroundColor Yellow
Set-Location $backendDir

Write-Host "  Removing Python cache..." -ForegroundColor Gray
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter ".pytest_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✓ Backend cleaned" -ForegroundColor Green

# Frontend cleanup
Write-Host ""
Write-Host ">>> Cleaning FRONTEND..." -ForegroundColor Yellow
Set-Location $frontendDir

Write-Host "  Removing node_modules..." -ForegroundColor Gray
if (Test-Path "node_modules") {
    Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
}

Write-Host "  Removing .next build..." -ForegroundColor Gray
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
}

Write-Host "✓ Frontend cleaned" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "RESET COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run: .\startup.ps1" -ForegroundColor Yellow
Write-Host ""
