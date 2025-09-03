@echo off
REM Job Application Tracker - Windows Troubleshooting Script
REM This script helps diagnose and fix common Windows issues

setlocal enabledelayedexpansion

echo [INFO] Job Application Tracker - Windows Troubleshooting
echo =====================================================
echo.

REM Check Docker status
echo [INFO] Checking Docker status...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not accessible
    echo.
    echo [SOLUTION] Please:
    echo   1. Start Docker Desktop
    echo   2. Wait for it to fully initialize
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
) else (
    echo [SUCCESS] Docker is running
)

REM Check if containers are running
echo.
echo [INFO] Checking container status...
cd app
docker compose -f docker-compose.windows.yml ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose command failed
    echo [SOLUTION] Try using: docker-compose -f docker-compose.windows.yml ps
    echo.
    pause
    exit /b 1
)

REM Show container status
echo [INFO] Current container status:
docker compose -f docker-compose.windows.yml ps
echo.

REM Check for specific issues
echo [INFO] Checking for common issues...

REM Check if port 8501 is in use
echo [INFO] Checking if port 8501 is available...
netstat -an | findstr ":8501" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8501 is already in use
    echo [SOLUTION] Stop other services using port 8501 or change the port in docker-compose.windows.yml
    echo.
)

REM Check if containers are healthy
echo [INFO] Checking container health...
docker compose -f docker-compose.windows.yml ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Some containers are not running properly
    echo.
    echo [SOLUTION] Check the logs:
    echo   docker compose -f docker-compose.windows.yml logs
    echo.
    echo [INFO] Common fixes:
    echo   1. Restart Docker Desktop
    echo   2. Clean up containers: docker compose -f docker-compose.windows.yml down
    echo   3. Rebuild: docker compose -f docker-compose.windows.yml up -d --build
    echo.
) else (
    echo [SUCCESS] All containers are running
)

REM Check network connectivity
echo.
echo [INFO] Testing network connectivity...
echo [INFO] Testing localhost:8501...
curl -s http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Cannot connect to localhost:8501
    echo [SOLUTION] The application may still be starting up. Wait a few minutes and try again.
    echo.
) else (
    echo [SUCCESS] Application is accessible at http://localhost:8501
)

REM Check Docker network
echo.
echo [INFO] Checking Docker networks...
docker network ls | findstr "track_jobapplication-network" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Creating missing network...
    docker network create track_jobapplication-network
) else (
    echo [SUCCESS] Docker network exists
)

REM Show useful commands
echo.
echo [INFO] Useful troubleshooting commands:
echo.
echo [COMMANDS] Container management:
echo   - View logs: docker compose -f docker-compose.windows.yml logs -f
echo   - Stop all: docker compose -f docker-compose.windows.yml down
echo   - Restart: docker compose -f docker-compose.windows.yml restart
echo   - Rebuild: docker compose -f docker-compose.windows.yml up -d --build
echo.
echo [COMMANDS] Individual services:
echo   - App logs: docker compose -f docker-compose.windows.yml logs job-tracker
echo   - DB logs: docker compose -f docker-compose.windows.yml logs postgres
echo   - Redis logs: docker compose -f docker-compose.windows.yml logs redis
echo.
echo [COMMANDS] System cleanup:
echo   - Remove all containers: docker compose -f docker-compose.windows.yml down -v
echo   - Remove all images: docker system prune -a
echo   - Clean Docker cache: docker system prune
echo.

REM Offer to restart services
echo [QUESTION] Would you like to restart the services? ^(Y/N^)
set /p choice="Enter your choice: "
if /i "!choice!"=="Y" (
    echo [INFO] Restarting services...
    docker compose -f docker-compose.windows.yml down
    timeout /t 5 >nul
    docker compose -f docker-compose.windows.yml up -d --build
    echo [INFO] Services restarted. Wait a few minutes for them to fully start.
) else (
    echo [INFO] Services not restarted.
)

echo.
echo [INFO] Troubleshooting complete.
echo [INFO] If you still have issues, check the logs and consider:
echo   1. Restarting Docker Desktop
echo   2. Checking Windows Defender Firewall settings
echo   3. Ensuring WSL2 is properly configured
echo   4. Running as Administrator if needed
echo.
pause