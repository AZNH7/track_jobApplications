#!/bin/bash

# Docker Performance Optimization Script for Job Tracker
# This script optimizes Docker container performance for faster job searches

echo "🚀 Optimizing Docker performance for Job Tracker..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Optimize Docker daemon settings
echo "🔧 Optimizing Docker daemon settings..."

# Create or update Docker daemon configuration
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5,
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Hard": 64000,
      "Name": "nofile",
      "Soft": 64000
    }
  }
}
EOF

# Restart Docker daemon to apply changes
echo "🔄 Restarting Docker daemon..."
sudo systemctl restart docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 10

# Check if containers are running
if docker ps | grep -q "job-tracker"; then
    echo "📦 Job Tracker containers are running. Optimizing..."
    
    # Optimize PostgreSQL container
    echo "🗄️ Optimizing PostgreSQL container..."
    docker exec job-tracker-postgres psql -U jobtracker -d jobtracker -c "
        ALTER SYSTEM SET shared_buffers = '256MB';
        ALTER SYSTEM SET effective_cache_size = '1GB';
        ALTER SYSTEM SET maintenance_work_mem = '64MB';
        ALTER SYSTEM SET checkpoint_completion_target = 0.9;
        ALTER SYSTEM SET wal_buffers = '16MB';
        ALTER SYSTEM SET default_statistics_target = 100;
        ALTER SYSTEM SET random_page_cost = 1.1;
        ALTER SYSTEM SET effective_io_concurrency = 200;
        SELECT pg_reload_conf();
    " 2>/dev/null || echo "⚠️ Could not optimize PostgreSQL settings"
    
    # Optimize FlareSolverr container
    echo "🌐 Optimizing FlareSolverr container..."
    docker exec job-tracker-flaresolverr sh -c "
        echo 'vm.max_map_count=262144' >> /etc/sysctl.conf
        sysctl -p
    " 2>/dev/null || echo "⚠️ Could not optimize FlareSolverr settings"
    
    # Optimize main application container
    echo "🐍 Optimizing Python application container..."
    docker exec job-tracker-app sh -c "
        # Increase file descriptor limits
        ulimit -n 65536
        
        # Optimize Python garbage collection
        export PYTHONGC=1
        export PYTHONUNBUFFERED=1
        
        # Set memory limits for Python
        export PYTHONMALLOC=malloc
    " 2>/dev/null || echo "⚠️ Could not optimize Python settings"
    
else
    echo "📦 Starting Job Tracker containers with optimizations..."
    
    # Start containers with optimized settings
    cd "$(dirname "$0")/../"
    
    # Create optimized docker-compose override
    cat > docker-compose.override.yml <<EOF
version: '3.8'
services:
  job-tracker:
    environment:
      - PYTHONGC=1
      - PYTHONUNBUFFERED=1
      - PYTHONMALLOC=malloc
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
  
  postgres:
    environment:
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      - POSTGRES_MAINTENANCE_WORK_MEM=64MB
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
  
  flaresolverr:
    environment:
      - NODE_OPTIONS=--max-old-space-size=1024
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
EOF
    
    # Start containers
    docker-compose up -d
    
    echo "⏳ Waiting for containers to start..."
    sleep 30
fi

# Verify optimizations
echo "✅ Verifying optimizations..."

# Check container resource usage
echo "📊 Container resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check PostgreSQL performance
echo "🗄️ PostgreSQL performance check:"
docker exec job-tracker-postgres psql -U jobtracker -d jobtracker -c "
    SELECT name, setting, unit FROM pg_settings 
    WHERE name IN ('shared_buffers', 'effective_cache_size', 'maintenance_work_mem')
    ORDER BY name;
" 2>/dev/null || echo "⚠️ Could not check PostgreSQL settings"

echo "🎉 Docker optimization complete!"
echo ""
echo "💡 Performance Tips:"
echo "   - Monitor resource usage with: docker stats"
echo "   - Check logs with: docker-compose logs -f"
echo "   - Restart containers if needed: docker-compose restart"
echo "   - Consider increasing Docker memory limit in Docker Desktop settings" 