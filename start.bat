@echo off
REM One command: FastAPI engine (port 8000) + Next.js web app (port 3000)
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
if not exist backend\.env copy backend\.env.example backend\.env
echo Starting WhyBot engine on http://localhost:8000
start "WhyBot engine" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
cd web
if not exist node_modules call npm install
if not exist .next call npm run build
echo Web app on http://localhost:3000
call npm run start
