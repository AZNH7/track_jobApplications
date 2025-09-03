FROM debian:bookworm-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TMPDIR=/var/tmp

# Create simplified entrypoint script for Windows compatibility
RUN echo '#!/bin/bash\n\
# Simple entrypoint for Windows compatibility\n\
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

# Configure pip for better reliability (after Python is installed)
RUN pip3 config set global.timeout 300 && \
    pip3 config set global.retries 3

# Copy requirements and install remaining Python dependencies via pip
COPY app/requirements.txt .

# Install Python dependencies with retry logic and increased timeout
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir --break-system-packages --timeout 300 --retries 3 -r requirements.txt || \
    (echo "First attempt failed, retrying with longer timeout..." && \
     pip3 install --no-cache-dir --break-system-packages --timeout 600 --retries 5 -r requirements.txt)

# Copy application code (always copy fresh to ensure updates)
COPY app/ .

# Ensure shared directory exists
RUN mkdir -p /app/shared

# Ensure scripts directory exists
RUN mkdir -p /app/scripts

# Set environment variables
ENV PYTHONPATH=/app/src
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose port
EXPOSE 8501

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "streamlit", "run", "src/app.py"] 