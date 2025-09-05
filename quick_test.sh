#!/bin/bash

# Quick Test Script pentru Jetson IP Camera Server
# Usage: ./quick_test.sh [server_url]

SERVER_URL=${1:-"https://localhost:8080"}

echo "🧪 === QUICK TEST JETSON SERVER ==="
echo "🌐 Server: $SERVER_URL"
echo "🕐 $(date)"
echo "================================="

# Test 1: Ping
echo "🏓 Test Ping..."
if curl -s -k "$SERVER_URL/ping" >/dev/null 2>&1; then
    echo "✅ Ping OK"
    PING_DATA=$(curl -s -k "$SERVER_URL/ping" | jq -r '.server // "unknown"' 2>/dev/null || echo "unknown")
    echo "   📡 Server: $PING_DATA"
else
    echo "❌ Ping FAILED"
fi

echo ""

# Test 2: Status
echo "📊 Test Status..."
if curl -s -k "$SERVER_URL/status" >/dev/null 2>&1; then
    echo "✅ Status OK"
    STATUS_DATA=$(curl -s -k "$SERVER_URL/status" 2>/dev/null)
    if command -v jq >/dev/null 2>&1; then
        VERSION=$(echo "$STATUS_DATA" | jq -r '.version // "unknown"')
        UPTIME=$(echo "$STATUS_DATA" | jq -r '.uptime_seconds // 0')
        CAMERAS=$(echo "$STATUS_DATA" | jq -r '.cameras_discovered // 0')
        SSL=$(echo "$STATUS_DATA" | jq -r '.ssl_enabled // false')
        echo "   📝 Version: $VERSION"
        echo "   ⏱️ Uptime: ${UPTIME}s"
        echo "   📹 Cameras: $CAMERAS"
        echo "   🔐 SSL: $SSL"
    fi
else
    echo "❌ Status FAILED"
fi

echo ""

# Test 3: Full Connection Test
echo "🔍 Test Connection..."
if curl -s -k "$SERVER_URL/test-connection" >/dev/null 2>&1; then
    echo "✅ Connection Test OK"
    CONN_DATA=$(curl -s -k "$SERVER_URL/test-connection" 2>/dev/null)
    if command -v jq >/dev/null 2>&1; then
        OVERALL=$(echo "$CONN_DATA" | jq -r '.overall_status // "unknown"')
        MESSAGE=$(echo "$CONN_DATA" | jq -r '.message // "N/A"')
        echo "   🎯 Overall: $OVERALL"
        echo "   💬 Message: $MESSAGE"
    fi
else
    echo "❌ Connection Test FAILED"
fi

echo ""

# Test 4: WebRTC Port Check
WEBSOCKET_PORT=$(echo "$SERVER_URL" | sed 's/8080/8081/')
WEBSOCKET_PORT=$(echo "$WEBSOCKET_PORT" | sed 's/https/wss/' | sed 's/http/ws/')

echo "📹 Test WebRTC Port..."
if timeout 5 bash -c "</dev/tcp/localhost/8081" 2>/dev/null; then
    echo "✅ WebRTC Port 8081 is open"
else
    echo "❌ WebRTC Port 8081 not accessible"
fi

echo ""
echo "================================="
echo "🎯 Test complet!"
echo "💡 Pentru test detaliat folosește: python3 test_connection.py"
echo "🌐 Acces server: $SERVER_URL"
