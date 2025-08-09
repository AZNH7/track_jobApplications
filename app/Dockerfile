FROM debian:bookworm-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TMPDIR=/var/tmp

# Create entrypoint script
RUN echo '#!/bin/bash\n\
# Add host.docker.internal to /etc/hosts if not running on Docker Desktop\n\
if ! grep -q "host.docker.internal" /etc/hosts; then\n\
    DOCKER_INTERNAL_HOST="$(ip route | awk '"'"'/default/ { print $3 }'"'"')"\n\
    echo "$DOCKER_INTERNAL_HOST host.docker.internal" >> /etc/hosts\n\
fi\n\
\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

# Ensure /var/tmp exists and is world-writable
RUN mkdir -p /var/tmp && chmod 1777 /var/tmp

# Update package lists and install ca-certificates first
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxss1 \
    libgconf-2-4 \
    libnss3 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    # Manim dependencies
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libgl1-mesa-glx \
    # Additional dependencies for enhanced features
    libmagic1 \
    libpq-dev \
    build-essential \
    # PDF processing dependencies
    poppler-utils \
    ghostscript \
    # Additional build dependencies for problematic packages
    gcc \
    g++ \
    make \
    pkg-config \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install remaining Python dependencies via pip
COPY app/requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code (always copy fresh to ensure updates)
COPY app/ .

# Ensure shared directory exists
RUN mkdir -p /app/shared/cv

# Copy CV files if they exist (optional)
COPY shared/cv/ /app/shared/cv/ 2>/dev/null || echo "No CV files found - will use mounted volume"

# Copy verification script if it exists
RUN if [ -f "scripts/verify_cv.py" ]; then \
        cp scripts/verify_cv.py /app/verify_cv.py && \
        python3 /app/verify_cv.py || echo "CV verification completed"; \
    else \
        echo "CV verification script not found - skipping"; \
    fi

# Copy all scripts for database maintenance if they exist
RUN if [ -d "scripts" ]; then \
        cp -r scripts/ /app/scripts/; \
    else \
        echo "Scripts directory not found - creating empty directory" && \
        mkdir -p /app/scripts; \
    fi

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose port
EXPOSE 8501

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "streamlit", "run", "src/app.py"] 