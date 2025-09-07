@echo off
echo [INFO] Windows Docker Troubleshooting Script
echo ===========================================
echo.

echo [INFO] Checking Docker Desktop status...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not accessible
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
) else (
    echo [SUCCESS] Docker is running
)

echo.
echo [INFO] Checking if port 8501 is available...
netstat -an | findstr ":8501" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8501 is already in use
    echo This might prevent the application from starting
    echo Please stop any other services using port 8501
) else (
    echo [SUCCESS] Port 8501 is available
)

echo.
echo [INFO] Checking Windows Firewall...
netsh advfirewall firewall show rule name="Docker Desktop" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker Desktop firewall rule not found
    echo This might block container connectivity
) else (
    echo [SUCCESS] Docker Desktop firewall rule exists
)

echo.
echo [INFO] Testing Docker networking...
docker run --rm alpine ping -c 1 google.com >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker container cannot reach external network
    echo This might affect application functionality
) else (
    echo [SUCCESS] Docker networking is working
)

echo.
echo [INFO] Checking Docker Desktop settings...
echo Please ensure the following in Docker Desktop:
echo 1. WSL 2 backend is enabled
echo 2. Expose daemon on tcp://localhost:2375 is DISABLED
echo 3. Use the WSL 2 based engine is ENABLED
echo 4. Resources ^> Memory: At least 4GB allocated
echo 5. Resources ^> Disk image size: At least 60GB
echo.

echo [INFO] Stopping any existing containers...
cd app
docker-compose -f docker-compose.windows.yml down >nul 2>&1

echo [INFO] Starting with Windows-compatible configuration...
docker-compose -f docker-compose.windows.yml up -d --build

echo.
echo [INFO] Waiting for services to start...
timeout /t 30 >nul

echo.
echo [INFO] Checking container status...
docker-compose -f docker-compose.windows.yml ps

echo.
echo [INFO] Testing application connectivity...
timeout /t 5 >nul
curl -I http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Application is not accessible at http://localhost:8501
    echo.
    echo [TROUBLESHOOTING STEPS:]
    echo 1. Check Docker Desktop is running
    echo 2. Ensure no other services are using port 8501
    echo 3. Try accessing http://127.0.0.1:8501 instead
    echo 4. Check Windows Firewall settings
    echo 5. Restart Docker Desktop
    echo.
    echo [DEBUG INFO:]
    echo Container logs:
    docker-compose -f docker-compose.windows.yml logs --tail=20
) else (
    echo [SUCCESS] Application is accessible at http://localhost:8501
    echo.
    echo 🌐 You can now access the application in your browser
    echo 📱 Try: http://localhost:8501 or http://127.0.0.1:8501
)

echo.
echo Press any key to exit...
pause >nul
