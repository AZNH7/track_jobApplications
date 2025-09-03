@echo off
REM Job Application Tracker - Cross-Platform Setup Script (Windows)
REM This script sets up the Job Application Tracker on Windows systems

setlocal enabledelayedexpansion

echo [INFO] Starting Job Application Tracker Setup for Windows
echo.
echo [NOTE] This setup will guide you through the installation process.
echo [NOTE] You may need to press Enter at certain points to continue.
echo.

REM Function to check if command exists
echo [INFO] Checking Docker installation...
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo Please install Docker Desktop for Windows:
    echo https://docs.docker.com/desktop/windows/
    echo.
    echo Press Enter to exit...
    pause
    exit /b 1
)

REM Check if Docker is running
echo [INFO] Checking if Docker is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    echo.
    echo Press Enter to exit...
    pause
    exit /b 1
)

REM Check Docker Compose
echo [INFO] Checking Docker Compose...
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose is not available.
        echo Please ensure Docker Desktop is properly installed.
        echo.
        echo Press Enter to exit...
        pause
        exit /b 1
    ) else (
        set DOCKER_COMPOSE=docker-compose
    )
) else (
    set DOCKER_COMPOSE=docker compose
)

echo [SUCCESS] All prerequisites are available
echo.
echo [INFO] Press Enter to continue with directory setup...
pause >nul

REM Set up directories
echo [INFO] Setting up directories...
if not exist "exports" mkdir exports
if not exist "imports" mkdir imports
if not exist "logs" mkdir logs
if not exist "shared" mkdir shared

if not exist "shared\data" mkdir shared\data
if not exist "shared\logs" mkdir shared\logs
if not exist "shared\postgres-init" mkdir shared\postgres-init

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    if exist "app\env.template" (
        copy "app\env.template" ".env" >nul
        echo [WARNING] Please edit .env file with your LinkedIn credentials before starting the application
    ) else (
        (
            echo # LinkedIn Authentication ^(required for LinkedIn job scraping^)
            echo LINKEDIN_LI_AT="Your_long_cookie_string_goes_here"
            echo.
            echo # Database Configuration ^(defaults are fine for Docker setup^)
            echo POSTGRES_HOST=postgres
            echo POSTGRES_PORT=5432
            echo POSTGRES_DB=jobtracker
            echo POSTGRES_USER=jobtracker
            echo POSTGRES_PASSWORD=secure_password_2024
            echo.
            echo # Redis Configuration
            echo REDIS_HOST=redis
            echo REDIS_PORT=6379
            echo REDIS_DB=0
            echo.
            echo # FlareSolverr Configuration
            echo FLARESOLVERR_URL=http://flaresolverr:8191/v1
            echo.
            echo # Ollama Configuration ^(for AI features^)
            echo OLLAMA_HOST=http://host.docker.internal:11434
            echo.
            echo # Application Configuration
            echo DATA_EXPORT_PATH=./exports
            echo DATA_IMPORT_PATH=./imports
            echo CACHE_DURATION=300
        ) > .env
        echo [WARNING] Created .env file. Please edit it with your configuration before starting.
    )
) else (
    echo [SUCCESS] .env file already exists
)

echo [SUCCESS] Directory setup completed
echo.
echo [INFO] Press Enter to continue with AI features setup...
pause >nul

REM Set up Ollama (optional)
echo [INFO] Setting up AI features ^(Ollama^)...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found. AI features will be disabled.
    echo To enable AI features, install Ollama:
    echo   - Visit: https://ollama.ai/
    echo   - Then run: ollama pull llama3.2:latest
) else (
    echo [SUCCESS] Ollama is already installed
    echo [INFO] Checking for required models...
    
    ollama list | findstr "llama3.2" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Downloading AI model ^(this may take a while^)...
        ollama pull llama3.2:latest || echo [WARNING] Failed to download AI model. You can install it later with: ollama pull llama3.2:latest
    ) else (
        echo [SUCCESS] AI model is ready
    )
)

echo [SUCCESS] AI features setup completed
echo.
echo [INFO] Press Enter to start the application...
pause >nul

REM Start the application
echo [INFO] Starting Job Application Tracker...
cd app

echo [INFO] Building and starting containers with Windows-optimized configuration...
echo [NOTE] This may take several minutes. Please wait...
%DOCKER_COMPOSE% -f docker-compose.windows.yml up -d --build

REM Wait for services to be ready
echo [INFO] Waiting for services to start...
timeout /t 30 >nul

REM Check if services are running
%DOCKER_COMPOSE% -f docker-compose.windows.yml ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Some services failed to start. Check the logs:
    echo   %DOCKER_COMPOSE% -f docker-compose.windows.yml logs
) else (
    echo [SUCCESS] Job Application Tracker is now running!
    echo.
    echo 🌐 Access the application at: http://localhost:8501
    echo.
    echo 📚 Next steps:
    echo   1. Edit .env file with your LinkedIn credentials
    echo   2. Visit http://localhost:8501 to start using the application
    echo.
    echo 🔧 Useful commands:
    echo   - View logs: %DOCKER_COMPOSE% -f docker-compose.windows.yml logs -f
    echo   - Stop application: %DOCKER_COMPOSE% -f docker-compose.windows.yml down
    echo   - Restart application: %DOCKER_COMPOSE% -f docker-compose.windows.yml restart
    echo   - Update application: git pull ^&^& %DOCKER_COMPOSE% -f docker-compose.windows.yml up -d --build
)

echo.
echo Press any key to exit...
pause >nul
