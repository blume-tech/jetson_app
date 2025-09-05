#!/bin/bash

# Network Setup Script pentru Jetson IP Camera Server
# Acest script te ajută să configurezi accesul online pentru serverul Jetson

echo "🌐 === JETSON NETWORK SETUP - ONLINE ACCESS ==="
echo "🎯 Configurare acces online pentru serverul Jetson"
echo ""

# Culori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verifică informații rețea
echo -e "${BLUE}📡 Informații rețea curente:${NC}"

# IP local
LOCAL_IP=$(ip route get 8.8.8.8 | grep -oP 'src \K\S+' 2>/dev/null || hostname -I | awk '{print $1}')
echo "   🏠 IP Local: $LOCAL_IP"

# Gateway
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
echo "   🚪 Gateway: $GATEWAY"

# IP public (dacă e disponibil)
echo "   🌍 Verific IP public..."
PUBLIC_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || echo "Nu se poate obține")
echo "   🌍 IP Public: $PUBLIC_IP"

# Verifică porturi deschise
echo ""
echo -e "${BLUE}🔌 Verificare porturi:${NC}"

check_port() {
    local port=$1
    local name=$2
    if netstat -tuln | grep -q ":$port "; then
        echo -e "   ✅ Port $port ($name): ${GREEN}DESCHIS${NC}"
    else
        echo -e "   ❌ Port $port ($name): ${RED}ÎNCHIS${NC}"
    fi
}

check_port 8080 "Flask HTTPS"
check_port 8081 "WebRTC WSS"
check_port 22 "SSH"

echo ""
echo -e "${BLUE}🔧 Opțiuni de configurare:${NC}"
echo "1) Configurare automată firewall local"
echo "2) Generare comenzi pentru router port forwarding"
echo "3) Test conectivitate externă"
echo "4) Configurare SSH tunnel (avansată)"
echo "5) Instalare ngrok pentru test rapid"
echo "6) Afișare informații pentru platformă web"
echo ""

read -p "Alege opțiunea (1-6): " choice

case $choice in
    1)
        echo -e "${BLUE}🔥 Configurare firewall local...${NC}"
        
        # Ubuntu/Debian ufw
        if command -v ufw &> /dev/null; then
            echo "📦 Configurez ufw..."
            sudo ufw allow 8080/tcp comment "Jetson Flask HTTPS"
            sudo ufw allow 8081/tcp comment "Jetson WebRTC WSS"
            sudo ufw allow 22/tcp comment "SSH"
            sudo ufw --force enable
            echo -e "${GREEN}✅ Firewall configurat cu ufw${NC}"
        
        # RHEL/CentOS firewalld
        elif command -v firewall-cmd &> /dev/null; then
            echo "📦 Configurez firewalld..."
            sudo firewall-cmd --permanent --add-port=8080/tcp
            sudo firewall-cmd --permanent --add-port=8081/tcp
            sudo firewall-cmd --reload
            echo -e "${GREEN}✅ Firewall configurat cu firewalld${NC}"
        
        # iptables direct
        else
            echo "📦 Configurez iptables..."
            sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
            sudo iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
            
            # Salvare permanentă (Ubuntu/Debian)
            if command -v iptables-save &> /dev/null; then
                sudo iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
            fi
            echo -e "${GREEN}✅ Firewall configurat cu iptables${NC}"
        fi
        ;;
        
    2)
        echo -e "${BLUE}🌐 Configurare router port forwarding...${NC}"
        echo ""
        echo "📋 Adaugă aceste reguli în routerul tău:"
        echo ""
        echo -e "${YELLOW}Regula 1 - Flask HTTPS:${NC}"
        echo "   Service Name: Jetson-HTTPS"
        echo "   External Port: 8080"
        echo "   Internal IP: $LOCAL_IP"
        echo "   Internal Port: 8080"
        echo "   Protocol: TCP"
        echo ""
        echo -e "${YELLOW}Regula 2 - WebRTC WSS:${NC}"
        echo "   Service Name: Jetson-WSS"  
        echo "   External Port: 8081"
        echo "   Internal IP: $LOCAL_IP"
        echo "   Internal Port: 8081"
        echo "   Protocol: TCP"
        echo ""
        echo -e "${BLUE}📱 Acces router:${NC}"
        echo "   🌐 URL Router: http://$GATEWAY"
        echo "   📖 Caută secțiunea: 'Port Forwarding' sau 'Virtual Server'"
        echo ""
        echo -e "${GREEN}🎯 După configurare, serverul va fi accesibil la:${NC}"
        echo "   https://$PUBLIC_IP:8080 (Flask API)"
        echo "   wss://$PUBLIC_IP:8081 (WebRTC)"
        ;;
        
    3)
        echo -e "${BLUE}🧪 Test conectivitate externă...${NC}"
        
        # Test conectivitate internet
        echo "🌍 Test conectivitate internet..."
        if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
            echo -e "   ✅ ${GREEN}Internet OK${NC}"
        else
            echo -e "   ❌ ${RED}Internet FAILED${NC}"
        fi
        
        # Test DNS
        echo "🔍 Test DNS..."
        if nslookup google.com > /dev/null 2>&1; then
            echo -e "   ✅ ${GREEN}DNS OK${NC}"
        else
            echo -e "   ❌ ${RED}DNS FAILED${NC}"
        fi
        
        # Test port extern (dacă serverul rulează)
        echo "🔌 Test porturi locale..."
        if curl -k -s --connect-timeout 5 https://localhost:8080/ping > /dev/null 2>&1; then
            echo -e "   ✅ ${GREEN}Server local OK${NC}"
        else
            echo -e "   ❌ ${RED}Server local nu răspunde${NC}"
            echo "   💡 Pornește serverul cu: python3 server_ip_camera.py"
        fi
        ;;
        
    4)
        echo -e "${BLUE}🚇 Configurare SSH tunnel...${NC}"
        echo ""
        echo "📋 Pentru acces temporar prin SSH tunnel:"
        echo ""
        echo -e "${YELLOW}Pe computer local:${NC}"
        echo "ssh -L 8080:localhost:8080 -L 8081:localhost:8081 user@$PUBLIC_IP"
        echo ""
        echo -e "${YELLOW}Apoi accesează:${NC}"
        echo "https://localhost:8080 (redirect la Jetson)"
        echo ""
        echo -e "${BLUE}Pentru tunnel permanent:${NC}"
        echo "ssh -f -N -L 8080:localhost:8080 -L 8081:localhost:8081 user@$PUBLIC_IP"
        ;;
        
    5)
        echo -e "${BLUE}📡 Instalare ngrok pentru test rapid...${NC}"
        
        # Verifică dacă ngrok e instalat
        if command -v ngrok &> /dev/null; then
            echo -e "${GREEN}✅ ngrok deja instalat${NC}"
        else
            echo "📦 Instalez ngrok..."
            
            # Download ngrok
            if [[ "$OSTYPE" == "linux"* ]]; then
                if [[ "$(uname -m)" == "aarch64" ]]; then
                    # ARM64 pentru Jetson
                    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
                    tar xzf ngrok-v3-stable-linux-arm64.tgz
                else
                    # x86_64
                    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
                    tar xzf ngrok-v3-stable-linux-amd64.tgz
                fi
                sudo mv ngrok /usr/local/bin/
                rm -f ngrok-v3-stable-linux-*.tgz
                echo -e "${GREEN}✅ ngrok instalat${NC}"
            else
                echo -e "${YELLOW}⚠️ Instalează manual ngrok de la https://ngrok.com/download${NC}"
            fi
        fi
        
        echo ""
        echo -e "${BLUE}🚀 Comenzi ngrok pentru test:${NC}"
        echo ""
        echo -e "${YELLOW}Terminal 1 - Pornește serverul:${NC}"
        echo "python3 server_ip_camera.py"
        echo ""
        echo -e "${YELLOW}Terminal 2 - Tunnel HTTPS:${NC}"
        echo "ngrok http 8080"
        echo ""
        echo -e "${YELLOW}Terminal 3 - Tunnel WSS:${NC}"  
        echo "ngrok http 8081"
        echo ""
        echo "💡 ngrok va afișa URL-uri publice temporare pentru test"
        ;;
        
    6)
        echo -e "${BLUE}📱 Informații pentru platformă web...${NC}"
        echo ""
        echo -e "${GREEN}🔗 URL-uri de test:${NC}"
        echo ""
        if [ "$PUBLIC_IP" != "Nu se poate obține" ]; then
            echo -e "${YELLOW}Acces direct (după port forwarding):${NC}"
            echo "   API: https://$PUBLIC_IP:8080"
            echo "   Test: https://$PUBLIC_IP:8080/test-connection"
            echo "   WebRTC: wss://$PUBLIC_IP:8081"
        fi
        echo ""
        echo -e "${YELLOW}Acces local (pentru test):${NC}"
        echo "   API: https://$LOCAL_IP:8080"
        echo "   Test: https://$LOCAL_IP:8080/test-connection"
        echo "   WebRTC: wss://$LOCAL_IP:8081"
        echo ""
        echo -e "${GREEN}📋 Cod JavaScript pentru platformă:${NC}"
        echo ""
        cat << 'EOF'
// Test conexiune Jetson
async function testJetsonConnection(jetsonUrl) {
    try {
        const response = await fetch(`${jetsonUrl}/test-connection`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            return {
                online: true,
                status: data.overall_status,
                message: data.message,
                local_ip: data.server_info?.local_ip,
                cameras: data.test_details?.camera_discovery?.cameras_found || 0
            };
        }
        return { online: false, error: 'HTTP Error' };
    } catch (error) {
        return { online: false, error: error.message };
    }
}

// Utilizare:
testJetsonConnection('https://YOUR_IP:8080').then(result => {
    console.log('Jetson status:', result);
});
EOF
        ;;
        
    *)
        echo -e "${RED}❌ Opțiune invalidă${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✨ Configurare completă!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Pornește serverul: python3 server_ip_camera.py"
echo "2. Testează local: curl -k https://$LOCAL_IP:8080/ping"
if [ "$PUBLIC_IP" != "Nu se poate obține" ]; then
    echo "3. Testează extern: curl -k https://$PUBLIC_IP:8080/ping"
fi
echo "4. Integrează în platformă cu URL-urile afișate"
echo ""
echo -e "${YELLOW}⚠️ Important:${NC}"
echo "- Pentru HTTPS trebuie să accepți certificatul self-signed în browser"
echo "- Pentru producție, folosește certificat SSL valid"
echo "- Configurează firewall și router după nevoie"
