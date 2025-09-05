# Test Endpoints pentru Jetson IP Camera Server

Serverul Jetson IP Camera oferă mai multe endpoint-uri pentru testarea conexiunii și verificarea funcționalității din platforma externă.

## 🔗 Endpoint-uri de Test

### 1. `/ping` - Test Rapid
**Metoda:** GET  
**Descriere:** Verificare rapidă că serverul răspunde  
**Răspuns:** Status simplu cu timestamp

```bash
curl -k https://localhost:8080/ping
```

**Răspuns exemplu:**
```json
{
  "status": "pong",
  "timestamp": "2025-09-05T10:30:00.123456",
  "server": "jetson-ip-camera-server",
  "version": "2.0.0-ssl"
}
```

### 2. `/test-connection` - Test Complet
**Metoda:** GET/POST  
**Descriere:** Test complet al tuturor componentelor sistemului  
**Răspuns:** Raport detaliat cu statusul fiecărei componente

```bash
curl -k https://localhost:8080/test-connection
```

**Răspuns exemplu:**
```json
{
  "timestamp": "2025-09-05T10:30:00.123456",
  "jetson_status": "online",
  "connection_test": "success",
  "overall_status": "excellent",
  "message": "Toate sistemele funcționează perfect!",
  "test_details": {
    "server_status": {
      "status": "running",
      "uptime_seconds": 3600,
      "flask_port": 8080,
      "websocket_port": 8081,
      "ssl_enabled": true
    },
    "jetson_monitoring": {
      "status": "active",
      "jtop_available": true,
      "last_update": "2025-09-05T10:29:59.000000",
      "data_points": 3600
    },
    "performance": {
      "cpu_usage_percent": 25.5,
      "status": "good"
    },
    "memory": {
      "ram_usage_percent": 45.2,
      "ram_used_mb": 2048,
      "ram_total_mb": 4096,
      "status": "good"
    },
    "temperature": {
      "max_temperature_c": 45.0,
      "status": "good"
    },
    "camera_discovery": {
      "cameras_found": 3,
      "cameras": [
        {
          "ip": "192.168.1.100",
          "type": "mjpeg",
          "manufacturer": "hikvision"
        }
      ],
      "scanning_active": true
    },
    "network": {
      "external_connectivity": "ok",
      "dns_resolution": "ok"
    },
    "video_devices": {
      "devices_found": 2,
      "devices": [
        {
          "device": "/dev/video0",
          "status": "available"
        }
      ]
    }
  },
  "issues": []
}
```

### 3. `/status` - Status Server
**Metoda:** GET  
**Descriere:** Status general al serverului și componentelor

```bash
curl -k https://localhost:8080/status
```

### 4. `/system-info` - Informații Sistem
**Metoda:** GET  
**Descriere:** Informații detaliate despre hardware și OS

```bash
curl -k https://localhost:8080/system-info
```

## 🛠️ Scripturi de Test

### 1. Test Python Complet
```bash
# Test cu HTTPS (default)
python3 test_connection.py

# Test cu HTTP
python3 test_connection.py --http

# Test cu URL custom
python3 test_connection.py --url https://192.168.1.50:8080

# Test cu verificare SSL
python3 test_connection.py --verify-ssl
```

### 2. Test Bash Rapid
```bash
# Test local
./quick_test.sh

# Test server remote
./quick_test.sh https://192.168.1.50:8080
```

## 📱 Integrare în Platformă

### JavaScript/React Example
```javascript
// Test rapid ping
async function testJetsonConnection(serverUrl) {
  try {
    const response = await fetch(`${serverUrl}/ping`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('Jetson online:', data.server);
      return true;
    }
    return false;
  } catch (error) {
    console.error('Jetson connection failed:', error);
    return false;
  }
}

// Test complet
async function fullJetsonTest(serverUrl) {
  try {
    const response = await fetch(`${serverUrl}/test-connection`, {
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
        cameras: data.test_details?.camera_discovery?.cameras_found || 0,
        performance: data.test_details?.performance,
        issues: data.issues || []
      };
    }
    return { online: false, error: 'HTTP Error' };
  } catch (error) {
    return { online: false, error: error.message };
  }
}
```

### Python Example
```python
import requests

def test_jetson_connection(server_url, verify_ssl=False):
    """Test conexiune Jetson din platformă"""
    try:
        # Test rapid
        ping_response = requests.get(f"{server_url}/ping", 
                                   verify=verify_ssl, timeout=5)
        if ping_response.status_code != 200:
            return {"online": False, "error": "Ping failed"}
        
        # Test complet
        test_response = requests.get(f"{server_url}/test-connection", 
                                   verify=verify_ssl, timeout=15)
        if test_response.status_code == 200:
            data = test_response.json()
            return {
                "online": True,
                "status": data.get("overall_status"),
                "message": data.get("message"),
                "details": data.get("test_details", {}),
                "issues": data.get("issues", [])
            }
        
        return {"online": False, "error": "Test failed"}
        
    except Exception as e:
        return {"online": False, "error": str(e)}
```

## 🔐 Securitate

- Toate endpoint-urile suportă HTTPS cu certificat self-signed
- CORS activat pentru cross-origin requests
- Rate limiting recomandat în producție
- Pentru producție, folosește certificat SSL valid

## 📊 Status Codes

- **200:** Success - toate testele au trecut
- **500:** Server Error - probleme pe server
- **404:** Endpoint nu există
- **Timeout:** Server nu răspunde

## 🎯 Exemple de Răspunsuri Status

### Excellent (toate OK)
```json
{
  "overall_status": "excellent",
  "message": "Toate sistemele funcționează perfect!",
  "issues": []
}
```

### Good (probleme minore)
```json
{
  "overall_status": "good", 
  "message": "Sistemul funcționează bine cu 1 probleme minore",
  "issues": ["no_cameras_found"]
}
```

### Issues (probleme serioase)
```json
{
  "overall_status": "issues",
  "message": "Găsite 3 probleme care necesită atenție", 
  "issues": ["jtop_not_available", "no_cameras_found", "no_video_devices"]
}
```

### Error (server down)
```json
{
  "jetson_status": "error",
  "connection_test": "failed",
  "error": "Connection timeout"
}
```
