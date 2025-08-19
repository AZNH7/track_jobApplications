#!/bin/bash
#
# This script ensures the environment is correctly configured before starting the application.
# It runs the setup_env.py script to create or update the .env file and then
# launches the Docker services.
#

set -e

# Run the environment setup script
echo "Configuring environment..."
python3 streamlit-app/scripts/setup_env.py

# Start Docker services
echo "Starting Docker services..."
docker-compose -f app/docker-compose.yml up --build -d

echo "✅ Application is starting!"
echo "You can view the logs with: docker-compose -f app/docker-compose.yml logs -f"
echo "Streamlit app will be available at http://localhost:8501"