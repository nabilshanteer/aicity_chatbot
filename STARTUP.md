# Quick Start Guide

## One-Command Startup

To start the entire system (backend + frontend) with one command:

```powershell
.\startup.ps1
```

This will:
- ✓ Clean Python cache
- ✓ Install backend dependencies
- ✓ Start backend on port 8000
- ✓ Clean node_modules
- ✓ Install frontend dependencies  
- ✓ Start frontend on port 3000

Wait 15-30 seconds for both servers to fully start, then open:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000

## Full System Reset

If you need to reset everything:

```powershell
.\reset.ps1
```

This cleans:
- Python cache and dependencies
- Node modules and build artifacts
- Temporary files

Then run `.\startup.ps1` again.

## Manual Commands

### Backend Only
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Only
```powershell
cd frontend
npm install
npm run dev
```

## Troubleshooting

**Backend won't start?**
- Check Python is installed: `python --version`
- Check pip: `pip --version`
- Manually reset: `.\reset.ps1` then `.\startup.ps1`

**Frontend won't start?**
- Check Node.js is installed: `node --version`
- Check npm: `npm --version`
- Try: `cd frontend && npm install && npm run dev`

**Port conflicts?**
- Backend uses port 8000
- Frontend uses port 3000
- If ports are in use, kill the process or change ports in the scripts

**Stop services:**
```powershell
Stop-Job -Name Backend,Frontend
Get-Job | Remove-Job
```

**View logs:**
```powershell
Get-Job -Name Backend | Receive-Job -Keep
Get-Job -Name Frontend | Receive-Job -Keep
```
