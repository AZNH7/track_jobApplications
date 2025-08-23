# Windows Setup Guide

This guide helps Windows users set up and run the Job Application Tracker successfully.

## Prerequisites

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Ensure WSL 2 backend is enabled
   - Allocate at least 4GB RAM and 60GB disk space

2. **Windows 10/11** with WSL 2 support

## Quick Start

### Option 1: Automated Setup (Recommended)
```cmd
setup.bat
```

### Option 2: Manual Setup
1. Run `setup.bat` to create the `.env` file and set up directories
2. Edit the `.env` file with your LinkedIn credentials
3. Run the Windows troubleshooting script:
   ```cmd
   windows-troubleshoot.bat
   ```

## Common Windows Issues & Solutions

### Issue 1: "Port 8501 is already in use"
**Solution:**
```cmd
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Issue 2: "Docker Desktop is not running"
**Solution:**
1. Start Docker Desktop
2. Wait for it to fully initialize
3. Ensure WSL 2 backend is enabled

### Issue 3: "Application not accessible"
**Solutions:**
1. Try `http://127.0.0.1:8501` instead of `http://localhost:8501`
2. Check Windows Firewall settings
3. Restart Docker Desktop
4. Run `windows-troubleshoot.bat`

### Issue 4: "Container networking issues"
**Solution:**
1. In Docker Desktop settings:
   - Enable "Use the WSL 2 based engine"
   - Disable "Expose daemon on tcp://localhost:2375"
   - Increase memory allocation to at least 4GB

## Docker Commands for Windows

### Start the application:
```cmd
cd app
docker-compose -f docker-compose.windows.yml up -d --build
```

### View logs:
```cmd
docker-compose -f docker-compose.windows.yml logs -f
```

### Stop the application:
```cmd
docker-compose -f docker-compose.windows.yml down
```

### Restart the application:
```cmd
docker-compose -f docker-compose.windows.yml restart
```

## Troubleshooting

### If the application still doesn't work:

1. **Check Docker Desktop settings:**
   - Open Docker Desktop
   - Go to Settings > General
   - Ensure "Use the WSL 2 based engine" is checked
   - Go to Settings > Resources
   - Allocate at least 4GB RAM

2. **Check Windows Firewall:**
   - Allow Docker Desktop through Windows Firewall
   - Allow port 8501 if prompted

3. **Reset Docker Desktop:**
   - Open Docker Desktop
   - Go to Settings > Troubleshoot
   - Click "Reset to factory defaults"

4. **Use the troubleshooting script:**
   ```cmd
   windows-troubleshoot.bat
   ```

## Accessing the Application

Once running successfully, access the application at:
- **Primary URL:** http://localhost:8501
- **Alternative URL:** http://127.0.0.1:8501

## Support

If you continue to have issues:
1. Run `windows-troubleshoot.bat` and share the output
2. Check the container logs: `docker-compose -f docker-compose.windows.yml logs`
3. Ensure Docker Desktop is up to date
4. Try restarting your computer and Docker Desktop
