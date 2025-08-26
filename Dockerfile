# Unified Jetson Server Dockerfile
# Folosește imagine de bază Ubuntu pentru compatibilitate cu Jetson
FROM ubuntu:20.04

# Evită prompturile interactive
ENV DEBIAN_FRONTEND=noninteractive

# Instalează dependențele de sistem
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libv4l-dev \
    v4l-utils \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Creează directorul de lucru
WORKDIR /app

# Copiază requirements.txt și instalează dependențele Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiază codul sursă
COPY server.py .

# Configurare porturi
EXPOSE 8080 8081

# Configurare variabile de mediu
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Verifică dispozitivele video la startup
RUN echo '#!/bin/bash\n\
echo "🔍 Verificare dispozitive video disponibile:"\n\
ls -la /dev/video* 2>/dev/null || echo "❌ Nu s-au găsit dispozitive video"\n\
echo "🔍 Verificare module V4L2:"\n\
lsmod | grep -E "(uvcvideo|v4l2)" || echo "⚠️ Module V4L2 nu sunt încărcate"\n\
echo "🚀 Starting Unified Jetson Server..."\n\
exec python3 server.py\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Comandă de rulare
CMD ["/app/entrypoint.sh"]

# Metadata
LABEL maintainer="Claude AI Assistant"
LABEL description="Unified Jetson Server - Monitoring și WebRTC Streaming"
LABEL version="1.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/status || exit 1
