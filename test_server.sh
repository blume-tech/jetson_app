#!/bin/bash

# Test Script pentru Unified Jetson Server
# Autor: Claude AI Assistant
# Verifică că toate serviciile funcționează corect

echo "🧪 === TEST UNIFIED JETSON SERVER ==="
echo ""

# Culori pentru output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurare
FLASK_PORT=8080
WEBSOCKET_PORT=8081
HOST="localhost"

# Funcție pentru testing
test_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${YELLOW}URL:${NC} http://$HOST:$FLASK_PORT$endpoint"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$FLASK_PORT$endpoint" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✅ SUCCESS${NC} - Status: $response"
    else
        echo -e "${RED}❌ FAILED${NC} - Status: $response"
    fi
    echo ""
}

# Verifică dacă serverul rulează
echo -e "${BLUE}🔍 Verificare servere...${NC}"
if ! nc -z $HOST $FLASK_PORT 2>/dev/null; then
    echo -e "${RED}❌ Flask server nu este accesibil pe portul $FLASK_PORT${NC}"
    echo "💡 Pornește serverul cu: python3 server.py"
    echo "💡 Sau cu Docker: docker-compose up -d"
    exit 1
fi

if ! nc -z $HOST $WEBSOCKET_PORT 2>/dev/null; then
    echo -e "${YELLOW}⚠️  WebSocket server nu este accesibil pe portul $WEBSOCKET_PORT${NC}"
    echo "💡 Verifică că serverul WebRTC rulează"
else
    echo -e "${GREEN}✅ WebSocket server accesibil${NC}"
fi

echo ""

# Testează endpoints
echo -e "${BLUE}🔧 Testare API Endpoints...${NC}"
echo ""

test_endpoint "/" "Informații generale server"
test_endpoint "/status" "Status servicii și funcționalități"
test_endpoint "/metrics" "Metrici Jetson în timp real"

# Test download logs (poate să dureze mai mult)
echo -e "${BLUE}Testing:${NC} Download logs CSV"
echo -e "${YELLOW}URL:${NC} http://$HOST:$FLASK_PORT/download_logs"

curl -s "http://$HOST:$FLASK_PORT/download_logs" -o test_logs.csv 2>/dev/null
if [ $? -eq 0 ] && [ -f test_logs.csv ]; then
    file_size=$(wc -c < test_logs.csv)
    if [ $file_size -gt 100 ]; then
        echo -e "${GREEN}✅ SUCCESS${NC} - CSV generat: ${file_size} bytes"
        echo "📄 Fișier salvat ca: test_logs.csv"
        rm -f test_logs.csv  # Curăță
    else
        echo -e "${YELLOW}⚠️  CSV generat dar pare gol${NC}"
    fi
else
    echo -e "${RED}❌ FAILED${NC} - Nu s-a putut descărca CSV"
fi
echo ""

# Verifică dispozitivele video
echo -e "${BLUE}📹 Verificare dispozitive video...${NC}"
video_devices=$(ls /dev/video* 2>/dev/null)
if [ ! -z "$video_devices" ]; then
    echo -e "${GREEN}✅ Dispozitive video găsite:${NC}"
    for device in $video_devices; do
        echo "   📹 $device"
    done
else
    echo -e "${YELLOW}⚠️  Nu s-au găsit dispozitive video în /dev/video*${NC}"
    echo "💡 Pentru WebRTC streaming, conectează camere USB"
fi
echo ""

# Verifică jtop (doar pe Jetson)
echo -e "${BLUE}📊 Verificare jtop (monitorizare Jetson)...${NC}"
if command -v jtop &> /dev/null; then
    echo -e "${GREEN}✅ jtop instalat${NC}"
    echo "💡 Rulează 'sudo jtop' pentru interfață grafică"
else
    echo -e "${YELLOW}⚠️  jtop nu este instalat${NC}"
    echo "💡 Pe Jetson: sudo -H pip3 install jetson-stats"
fi
echo ""

# Verifică Docker (opțional)
echo -e "${BLUE}🐳 Verificare Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker instalat${NC}"
    
    # Verifică dacă containerul rulează
    if docker ps | grep -q "jetson-unified-server"; then
        echo -e "${GREEN}✅ Container Docker rulează${NC}"
    else
        echo -e "${YELLOW}⚠️  Container Docker nu rulează${NC}"
        echo "💡 Pornește cu: docker-compose up -d"
    fi
else
    echo -e "${YELLOW}⚠️  Docker nu este instalat${NC}"
    echo "💡 Pentru instalare: https://docs.docker.com/engine/install/"
fi
echo ""

# Test rapid de performanță
echo -e "${BLUE}⚡ Test performanță API...${NC}"
start_time=$(date +%s.%N)
for i in {1..5}; do
    curl -s "http://$HOST:$FLASK_PORT/status" > /dev/null 2>&1
done
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")

if [ "$duration" != "N/A" ]; then
    avg_time=$(echo "scale=3; $duration / 5" | bc 2>/dev/null)
    echo -e "${GREEN}✅ Timp mediu răspuns:${NC} ${avg_time}s per request"
else
    echo -e "${YELLOW}⚠️  Nu s-a putut măsura performanța${NC}"
fi
echo ""

# Sumar final
echo -e "${BLUE}📋 === SUMAR TEST ===${NC}"
echo -e "${GREEN}✅ Teste completate${NC}"
echo ""
echo -e "${BLUE}🔗 Linkuri utile:${NC}"
echo "   🌐 API: http://$HOST:$FLASK_PORT"
echo "   📊 Status: http://$HOST:$FLASK_PORT/status"
echo "   📈 Metrici: http://$HOST:$FLASK_PORT/metrics"
echo "   📹 WebRTC: ws://$HOST:$WEBSOCKET_PORT"
echo ""
echo -e "${BLUE}📚 Comenzi utile:${NC}"
echo "   docker-compose up -d          # Pornește cu Docker"
echo "   python3 server.py             # Pornește direct"
echo "   curl http://$HOST:$FLASK_PORT/metrics | jq  # Vezi metrici formatate"
echo ""

exit 0
