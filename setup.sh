#!/bin/bash
# Job Application Tracker - Cross-Platform Setup Script (Unix/Linux/macOS)
# This script sets up the Job Application Tracker on Unix-like systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Main setup function
main() {
    print_status "🚀 Starting Job Application Tracker Setup"
    
    # Detect operating system
    OS=$(detect_os)
    print_status "Detected OS: $OS"
    
    # Check for required tools
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first:"
        echo "  - Linux: https://docs.docker.com/engine/install/"
        echo "  - macOS: https://docs.docker.com/desktop/mac/"
        echo "  - Windows: https://docs.docker.com/desktop/windows/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    print_success "All prerequisites are available"
    
    # Set up directories
    print_status "Setting up directories..."
    mkdir -p exports imports logs shared/data shared/logs shared/postgres-init
    
    # Create .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        print_status "Creating .env file from template..."
        if [[ -f "app/env.template" ]]; then
            cp app/env.template .env
            print_warning "Please edit .env file with your LinkedIn credentials before starting the application"
        else
            # Generate a secure random password
            POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
            print_status "Generated secure PostgreSQL password"
            
            cat > .env << EOF
# LinkedIn Authentication (required for LinkedIn job scraping)
LINKEDIN_LI_AT="Your_long_cookie_string_goes_here"

# Database Configuration (defaults are fine for Docker setup)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jobtracker
POSTGRES_USER=jobtracker
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# FlareSolverr Configuration
FLARESOLVERR_URL=http://localhost:8190/v1

# Ollama Configuration (for AI features)
OLLAMA_HOST=http://localhost:11434

# Application Configuration
DATA_EXPORT_PATH=./exports
DATA_IMPORT_PATH=./imports
CACHE_DURATION=300
EOF
            print_warning "Created .env file with secure password. Please edit it with your configuration before starting."
        fi
    else
        print_success ".env file already exists"
    fi
    

    
    # Set up Ollama (optional)
    print_status "Setting up AI features (Ollama)..."
    if command_exists ollama; then
        print_success "Ollama is already installed"
        print_status "Checking for required models..."
        
        if ollama list | grep -q "gemma3:1b"; then
            print_success "AI model is ready"
        else
            print_status "Downloading AI model (this may take a while)..."
            ollama pull gemma3:1b || print_warning "Failed to download AI model. You can install it later with: ollama pull gemma3:1b"
        fi
    else
        print_warning "Ollama not found. AI features will be disabled."
        print_status "To enable AI features, install Ollama:"
        echo "  - Visit: https://ollama.ai/"
        echo "  - Then run: ollama pull gemma3:1b"
    fi
    
    # Start the application
    print_status "Starting Job Application Tracker..."
    cd app
    
    # Use docker compose or docker-compose depending on what's available
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    print_status "Building and starting containers..."
    $DOCKER_COMPOSE up -d --build
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check if services are running
    if $DOCKER_COMPOSE ps | grep -q "Up"; then
        print_success "Job Application Tracker is now running!"
        echo ""
        echo "🌐 Access the application at: http://localhost:8501"
        echo ""
        echo "📚 Next steps:"
        echo "  1. Edit .env file with your LinkedIn credentials"

        echo "  3. Visit http://localhost:8501 to start using the application"
        echo ""
        echo "🔧 Useful commands:"
        echo "  - View logs: $DOCKER_COMPOSE logs -f"
        echo "  - Stop application: $DOCKER_COMPOSE down"
        echo "  - Restart application: $DOCKER_COMPOSE restart"
        echo "  - Update application: git pull && $DOCKER_COMPOSE up -d --build"
    else
        print_error "Some services failed to start. Check the logs:"
        echo "  $DOCKER_COMPOSE logs"
    fi
}

# Run main function
main "$@"
