#!/bin/bash

# Script pentru generarea certificatelor SSL pentru Jetson IP Camera Server
# Usage: ./generate_ssl.sh

echo "🔐 === GENERARE CERTIFICAT SSL PENTRU JETSON CAMERA SERVER ==="

# Verifică dacă certificatele există deja
if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
    echo "✅ Certificatele SSL există deja:"
    echo "   📄 cert.pem"
    echo "   🔑 key.pem"
    
    # Verifică validitatea certificatului
    if openssl x509 -in cert.pem -noout -checkend 86400 > /dev/null 2>&1; then
        echo "✅ Certificatul este valid (nu expiră în următoarele 24h)"
        
        # Afișează informații despre certificat
        echo ""
        echo "📋 Informații certificat:"
        openssl x509 -in cert.pem -noout -subject -dates -issuer
        
        read -p "🔄 Vrei să regenerezi certificatul? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "ℹ️  Certificatul existent va fi folosit"
            exit 0
        fi
    else
        echo "⚠️  Certificatul a expirat - va fi regenerat"
    fi
    
    # Backup certificatele existente
    echo "📦 Backup certificate existente..."
    mv cert.pem cert.pem.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null
    mv key.pem key.pem.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null
fi

# Verifică dacă openssl este instalat
if ! command -v openssl &> /dev/null; then
    echo "❌ openssl nu este instalat"
    echo "📦 Instalează cu: sudo apt-get install openssl"
    exit 1
fi

# Generează certificatul SSL
echo "🔐 Generez certificat SSL self-signed..."
echo "📝 Configurare certificat:"
echo "   🌐 Common Name: localhost"
echo "   🏢 Organization: Jetson Camera Server"
echo "   🌍 Country: RO"
echo "   ⏰ Validitate: 365 zile"

# Generează certificatul
openssl req -x509 \
    -newkey rsa:4096 \
    -keyout key.pem \
    -out cert.pem \
    -days 365 \
    -nodes \
    -subj "/CN=localhost/O=Jetson Camera Server/C=RO" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    2>/dev/null

# Verifică dacă generarea a reușit
if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
    echo "✅ Certificat SSL generat cu succes!"
    
    # Setează permisiuni corecte
    chmod 644 cert.pem
    chmod 600 key.pem
    
    echo ""
    echo "📋 Fișiere generate:"
    ls -la cert.pem key.pem
    
    echo ""
    echo "📋 Informații certificat:"
    openssl x509 -in cert.pem -noout -subject -dates -issuer
    
    echo ""
    echo "🎯 Certificatul poate fi folosit pentru:"
    echo "   🌐 HTTPS Flask API pe portul 8080"
    echo "   📹 WSS WebRTC pe portul 8081"
    echo "   🐳 Docker containers"
    
    echo ""
    echo "⚠️  IMPORTANT pentru browser:"
    echo "   📱 Prima dată va afișa avertisment de securitate"
    echo "   🔐 Acceptă certificatul pentru a continua"
    echo "   💡 Pentru producție, folosește certificat semnat de CA"
    
else
    echo "❌ Eroare la generarea certificatului SSL"
    exit 1
fi

echo ""
echo "✨ Setup SSL complet! Server poate folosi HTTPS/WSS! 🔐🚀"
