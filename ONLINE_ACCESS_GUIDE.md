# 🌐 JETSON ONLINE ACCESS GUIDE

Complete guide to expose your Jetson IP Camera Server online for website access.

## 🎯 Quick Setup Summary

### 1. **Configure Your Network**
```bash
# Run the network setup script
chmod +x network_setup.sh
./network_setup.sh
```

### 2. **Start Server**
```bash
# Generate SSL certificate (if needed)
./generate_ssl.sh

# Start the enhanced server
python3 server_ip_camera.py
```

### 3. **Configure Router Port Forwarding**
Access your router (usually `192.168.1.1`) and add:

| Service | External Port | Internal IP | Internal Port | Protocol |
|---------|---------------|-------------|---------------|----------|
| Jetson-HTTPS | 8080 | [Jetson IP] | 8080 | TCP |
| Jetson-WSS | 8081 | [Jetson IP] | 8081 | TCP |

### 4. **Test Access**
```bash
# Local test
curl -k https://localhost:8080/test-connection

# External test (replace YOUR_PUBLIC_IP)
curl -k https://YOUR_PUBLIC_IP:8080/test-connection
```

## 🔧 Method 1: Router Port Forwarding (Recommended)

### Step 1: Find Your Network Info
```bash
# Get local IP
hostname -I | awk '{print $1}'

# Get public IP
curl ifconfig.me
```

### Step 2: Configure Router
1. Access router admin panel (`192.168.1.1` or `192.168.0.1`)
2. Find "Port Forwarding" or "Virtual Server" section
3. Add the forwarding rules shown above
4. Save and restart router

### Step 3: Test External Access
```bash
# Replace YOUR_PUBLIC_IP with your actual public IP
curl -k https://YOUR_PUBLIC_IP:8080/ping
```

## 🐳 Method 2: Docker with Port Mapping

```bash
# Build and run with explicit port mapping
docker-compose up -d

# Or run directly
docker run -d \
  --name jetson-server \
  --privileged \
  --device=/dev/video0:/dev/video0 \
  -p 8080:8080 \
  -p 8081:8081 \
  -v /sys:/sys:ro \
  -v /proc:/proc:ro \
  jetson-ip-camera-server
```

## 🚇 Method 3: SSH Tunnel (Temporary Access)

```bash
# On your local computer, create tunnel to Jetson
ssh -L 8080:localhost:8080 -L 8081:localhost:8081 user@jetson-public-ip

# Then access via localhost
curl -k https://localhost:8080/test-connection
```

## 📡 Method 4: ngrok (Quick Testing)

```bash
# Install ngrok
./network_setup.sh  # Choose option 5

# Terminal 1: Start server
python3 server_ip_camera.py

# Terminal 2: Create tunnel
ngrok http 8080
```

ngrok will provide a public URL like: `https://abc123.ngrok.io`

## 🔥 Firewall Configuration

### Ubuntu/Debian (ufw)
```bash
sudo ufw allow 8080/tcp
sudo ufw allow 8081/tcp
sudo ufw enable
```

### RHEL/CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --reload
```

### iptables
```bash
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
```

## 💻 Website Integration

### JavaScript Example
```javascript
const JETSON_URL = 'https://YOUR_JETSON_IP:8080';

// Test connection
async function testJetsonConnection() {
    try {
        const response = await fetch(`${JETSON_URL}/test-connection`, {
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
                performance: data.test_details?.performance
            };
        }
        return { online: false, error: 'Connection failed' };
    } catch (error) {
        return { online: false, error: error.message };
    }
}

// Usage
testJetsonConnection().then(result => {
    if (result.online) {
        console.log(`Jetson is ${result.status}: ${result.message}`);
        console.log(`Cameras found: ${result.cameras}`);
    } else {
        console.error('Jetson offline:', result.error);
    }
});
```

### React Component Example
```jsx
import React, { useState, useEffect } from 'react';

const JetsonStatus = () => {
    const [status, setStatus] = useState({ online: false, loading: true });
    const JETSON_URL = 'https://YOUR_JETSON_IP:8080';

    useEffect(() => {
        const checkJetson = async () => {
            try {
                const response = await fetch(`${JETSON_URL}/test-connection`);
                const data = await response.json();
                setStatus({
                    online: true,
                    loading: false,
                    status: data.overall_status,
                    message: data.message,
                    cameras: data.test_details?.camera_discovery?.cameras_found || 0
                });
            } catch (error) {
                setStatus({
                    online: false,
                    loading: false,
                    error: error.message
                });
            }
        };

        checkJetson();
        const interval = setInterval(checkJetson, 30000); // Check every 30s
        return () => clearInterval(interval);
    }, []);

    if (status.loading) return <div>Checking Jetson...</div>;

    return (
        <div className={`jetson-status ${status.online ? 'online' : 'offline'}`}>
            <h3>Jetson Status: {status.online ? '🟢 Online' : '🔴 Offline'}</h3>
            {status.online && (
                <div>
                    <p>Status: {status.status}</p>
                    <p>Message: {status.message}</p>
                    <p>Cameras: {status.cameras}</p>
                </div>
            )}
            {!status.online && <p>Error: {status.error}</p>}
        </div>
    );
};

export default JetsonStatus;
```

## 🔐 Security Considerations

### SSL Certificate
- **Development**: Use self-signed certificate (auto-generated)
- **Production**: Use valid SSL certificate from Let's Encrypt or CA

### HTTPS in Production
```bash
# For production, get Let's Encrypt certificate
sudo certbot certonly --standalone -d your-domain.com
```

### Firewall Rules
- Only expose necessary ports (8080, 8081)
- Consider IP whitelisting for production
- Use strong authentication if needed

## 🧪 Testing Endpoints

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `/ping` | Quick connectivity test | `curl -k https://IP:8080/ping` |
| `/test-connection` | Full system test | `curl -k https://IP:8080/test-connection` |
| `/status` | Server status | `curl -k https://IP:8080/status` |
| `/network-info` | Network debugging | `curl -k https://IP:8080/network-info` |

## 🔧 Troubleshooting

### Common Issues

**Connection Refused:**
- Check if server is running: `python3 server_ip_camera.py`
- Check firewall: `sudo ufw status`
- Check ports: `netstat -tuln | grep 8080`

**SSL Certificate Errors:**
- Generate certificate: `./generate_ssl.sh`
- For browsers: Accept self-signed certificate

**Router Issues:**
- Verify port forwarding rules
- Check router firewall settings
- Restart router after configuration

**Docker Issues:**
- Use bridge network instead of host mode
- Check port mapping: `docker ps`
- Check logs: `docker logs jetson-ip-camera-server`

### Network Debugging
```bash
# Check if server responds locally
curl -k https://localhost:8080/network-info

# Check from external IP
curl -k https://YOUR_PUBLIC_IP:8080/network-info

# Check WebRTC port
nc -zv YOUR_PUBLIC_IP 8081
```

## 📱 Mobile Access

The server also works on mobile devices. Make sure to:
1. Accept the SSL certificate in mobile browser
2. Use the correct public IP or domain
3. Test with the `/ping` endpoint first

## 🎯 Final Checklist

- [ ] Server running with SSL
- [ ] Firewall configured  
- [ ] Router port forwarding setup
- [ ] Public IP known
- [ ] Local test successful
- [ ] External test successful
- [ ] Website integration complete

Your Jetson IP Camera Server is now accessible from your website! 🚀
