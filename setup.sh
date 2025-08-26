#!/bin/bash

# Quick Setup Script pentru Unified Jetson Server
# Rulează acest script pentru setup rapid

echo "🚀 === UNIFIED JETSON SERVER - QUICK SETUP ==="
echo ""

# Culori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verifică OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${GREEN}✅ OS Linux detectat${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}⚠️  macOS detectat - unele funcții Jetson nu vor funcționa${NC}"
else
    echo -e "${YELLOW}⚠️  OS necunoscut - continuă cu prudență${NC}"
fi

# Verifică Python 3
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python 3 instalat: $python_version${NC}"
else
    echo -e "${RED}❌ Python 3 nu este instalat${NC}"
    echo "💡 Instalează Python 3: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Verifică pip3
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip3 disponibil${NC}"
else
    echo -e "${RED}❌ pip3 nu este instalat${NC}"
    echo "💡 Instalează pip3: sudo apt-get install python3-pip"
    exit 1
fi

echo ""
echo -e "${BLUE}📦 Ce vrei să faci?${NC}"
echo "1) Setup local (fără Docker)"
echo "2) Setup cu Docker"
echo "3) Doar testare (presupune că serverul rulează)"
echo "4) Cleanup complet"
echo ""

read -p "Alege opțiunea (1-4): " choice

case $choice in
    1)
        echo -e "${BLUE}🔧 Setup local...${NC}"
        
        # Instalează dependențele sistem
        echo "📦 Instalare dependențe sistem..."
        sudo apt-get update
        sudo apt-get install -y python3-opencv v4l-utils curl netcat-openbsd bc
        
        # Instalează dependențele Python
        echo "🐍 Instalare dependențe Python..."
        pip3 install -r requirements.txt
        
        # Pe Jetson, încearcă să instaleze jetson-stats
        if grep -q "tegra" /proc/cpuinfo 2>/dev/null; then
            echo "🎯 Jetson detectat - instalez jetson-stats..."
            sudo -H pip3 install jetson-stats
            echo "💡 După instalare, rulează 'sudo reboot' pentru a activa jtop"
        fi
        
        echo -e "${GREEN}✅ Setup local complet!${NC}"
        echo "🚀 Pornește serverul: python3 server.py"
        ;;
        
    2)
        echo -e "${BLUE}🐳 Setup cu Docker...${NC}"
        
        # Verifică Docker
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker nu este instalat${NC}"
            echo "💡 Instalează Docker: https://docs.docker.com/engine/install/"
            exit 1
        fi
        
        # Verifică docker-compose
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${YELLOW}⚠️  docker-compose nu este instalat${NC}"
            echo "📦 Instalez docker-compose..."
            sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        fi
        
        # Construiește imaginea
        echo "🔨 Construire imagine Docker..."
        docker build -t unified-jetson-server .
        
        # Pornește cu docker-compose
        echo "🚀 Pornire cu docker-compose..."
        docker-compose up -d
        
        echo -e "${GREEN}✅ Setup Docker complet!${NC}"
        echo "📊 Verifică status: docker-compose ps"
        ;;
        
    3)
        echo -e "${BLUE}🧪 Rulare teste...${NC}"
        chmod +x test_server.sh
        ./test_server.sh
        ;;
        
    4)
        echo -e "${BLUE}🗑️  Cleanup complet...${NC}"
        
        # Oprește și șterge containere
        docker-compose down 2>/dev/null
        docker stop jetson-unified-server 2>/dev/null
        docker rm jetson-unified-server 2>/dev/null
        docker rmi unified-jetson-server 2>/dev/null
        
        # Șterge fișiere temporare
        rm -f test_logs.csv jetson_logs.csv *.log
        rm -rf logs/ data/ __pycache__/
        
        echo -e "${GREEN}✅ Cleanup complet!${NC}"
        ;;
        
    *)
        echo -e "${RED}❌ Opțiune invalidă${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}📋 Fișiere în proiect:${NC}"
ls -la

echo ""
echo -e "${BLUE}🔗 Linkuri utile după pornire:${NC}"
echo "   🌐 API: http://localhost:8080"
echo "   📊 Status: http://localhost:8080/status"
echo "   📈 Metrici: http://localhost:8080/metrics"
echo "   📹 WebRTC: ws://localhost:8081"

echo ""
echo -e "${GREEN}✨ Setup complet! Happy coding! 🚀${NC}"
