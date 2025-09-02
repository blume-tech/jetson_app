# Unified Jetson Server

🚀 **Server unificat pentru monitorizarea sistemului Jetson și streaming video WebRTC**

Un server Python complet care combină monitorizarea detaliată a sistemului Jetson (CPU, GPU, memorie, temperaturi, power) cu capacități de streaming video WebRTC de la multiple camere USB și camere IP.

## 📁 Fișiere Disponibile

- **`server.py`** - Server original pentru camere USB
- **`server_ip_camera.py`** - Server nou cu auto-descoperire camere IP
- **`test_ip_cameras.py`** - Script de test pentru descoperirea camerelor IP

## ✨ Funcționalități

### 📊 Monitorizare Jetson
- **CPU**: Usage per core, frequencies, governors, idle states
- **GPU**: Usage, frequencies, detailed metrics, memory usage
- **Temperaturi**: Toate senzorii disponibili cu limite max/critical
- **Memorie**: RAM, SWAP, EMC, IRAM cu detalii complete
- **Power**: Toate rail-urile de alimentare cu volt/curr/power
- **Export CSV**: Istoricul complet al datelor pentru analiză

### 📹 Streaming Video WebRTC
- Streaming în timp real de la multiple camere USB **SAU** camere IP
- Protocoal WebRTC pentru latență minimă
- **USB**: Suport pentru `/dev/video0`, `/dev/video1`, etc.
- **IP**: Auto-descoperire camere IP pe rețeaua locală
- Configurare automată rezoluție și frame rate

### 🔍 Descoperire Camere IP (NOU!)
- **Scanare automată** a rețelei locale pentru camere IP
- **Auto-detectare** protocoale MJPEG și RTSP
- **Testare stream-uri** pentru validarea camerelor
- **API endpoints** pentru management camere
- **Suport multiple formate** de camere IP comerciale

### 🌐 API REST
- `/metrics` - Ultimele metrici în timp real
- `/status` - Status server și funcționalități
- `/download_logs` - Export CSV complet
- `/cameras` - Camerele IP descoperite (doar server_ip_camera.py)
- `/cameras/rescan` - Rescanează pentru camere IP (doar server_ip_camera.py)
- `/` - Informații generale despre server

## 🔧 Instalare și Configurare

### Prerechizite

**Pe sistemul Jetson:**
```bash
# Instalează jtop pentru monitorizare
sudo -H pip3 install jetson-stats
sudo jtop  # Verifică că funcționează

# Verifică camerele USB
ls -la /dev/video*
v4l2-ctl --list-devices
```

### Instalare Rapidă cu Docker

1. **Clonează sau descarcă fișierele:**
```bash
# Asigură-te că ai toate fișierele:
# - server.py
# - Dockerfile  
# - requirements.txt
# - README.md
```

2. **Construiește imaginea Docker:**
```bash
docker build -t unified-jetson-server .
```

3. **Rulează containerul:**
```bash
docker run -d \
  --name jetson-server \
  --privileged \
  --device=/dev/video0:/dev/video0 \
  --device=/dev/video1:/dev/video1 \
  -p 8080:8080 \
  -p 8081:8081 \
  -v /sys:/sys:ro \
  -v /proc:/proc:ro \
  unified-jetson-server
```

### Instalare Manuală

1. **Instalează dependențele:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-opencv v4l-utils

# Instalează dependențele Python
pip3 install -r requirements.txt

# Pe Jetson - instalează jtop
sudo -H pip3 install jetson-stats
```

2. **Rulează serverul:**
```bash
python3 server.py
```

## 🚀 Utilizare

### Pornirea Serverului
```bash
# Metoda 1: Docker (recomandat)
docker run --privileged --device=/dev/video0 -p 8080:8080 -p 8081:8081 unified-jetson-server

# Metoda 2: Direct
python3 server.py
```

### Accesarea Serviciilor

**API REST (Port 8080):**
```bash
# Status general
curl http://localhost:8080/status

# Metrici în timp real
curl http://localhost:8080/metrics

# Descarcă logs CSV
curl http://localhost:8080/download_logs -o jetson_logs.csv
```

**WebRTC Streaming (Port 8081):**
```javascript
// Conectare WebSocket pentru WebRTC
const ws = new WebSocket('ws://localhost:8081');

// Exemplu de client WebRTC (vezi documentația aiortc)
```

### Exemplu Date Returnate

**GET /metrics:**
```json
{
  "timestamp": "2025-08-26T10:30:45.123456",
  "uptime": "2 days, 3:45:12",
  "board": "NVIDIA Jetson Nano Developer Kit",
  "cpu": {
    "CPU0_usage": 25.5,
    "CPU1_usage": 30.2,
    "CPU_total_usage": 27.8
  },
  "cpu_frequencies": {
    "CPU0_freq_cur": 1479,
    "CPU0_freq_max": 1479,
    "CPU1_freq_cur": 1479
  },
  "temperatures": {
    "CPU-therm": 45.2,
    "GPU-therm": 42.1,
    "AUX-therm": 38.5
  },
  "gpu": {
    "GPU_usage": 15.3,
    "GPU_freq": 921,
    "GPU_freq_max": 921
  },
  "memory": {
    "RAM_total": 8192,
    "RAM_used": 2048,
    "RAM_free": 6144,
    "SWAP_total": 4096
  },
  "power": {
    "total_power": 12.5,
    "CPU_power": 4.2,
    "GPU_power": 3.1
  }
}
```

## ⚙️ Configurare

### Variabile de Mediu
```bash
# Porturile serverelor
export FLASK_PORT=8080      # API REST
export WEBSOCKET_PORT=8081  # WebRTC

# Dispozitivele video
export VIDEO_DEVICES="/dev/video0,/dev/video1"

# Setări monitorizare
export MAX_HISTORY_SECONDS=600  # 10 minute de istoric
```

### Camerele USB
```bash
# Verifică dispozitivele disponibile
ls -la /dev/video*
v4l2-ctl --list-devices

# Testează o cameră
ffplay /dev/video0
# sau
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

## 📹 Server cu Camere IP (server_ip_camera.py)

### 🆕 Funcționalități Noi
- **Auto-descoperire camere IP** pe rețeaua locală
- **Suport protocoale multiple**: MJPEG, RTSP
- **Scanare inteligentă** cu verificare stream-uri
- **API dedicat** pentru management camere IP

### 🚀 Utilizare Server IP Camera

#### Pornirea Serverului
```bash
# Rulează serverul cu descoperire IP camere
python3 server_ip_camera.py
```

#### Testarea Descoperirii Camerelor
```bash
# Testează doar funcția de descoperire
python3 test_ip_cameras.py
```

#### API Endpoints Specifice Camerelor IP

**Vizualizează camerele descoperite:**
```bash
curl http://localhost:8080/cameras
```

**Rescanează rețeaua pentru camere:**
```bash
curl -X POST http://localhost:8080/cameras/rescan
```

**Exemplu răspuns /cameras:**
```json
{
  "cameras_found": 2,
  "cameras": [
    {
      "ip": "192.168.1.100",
      "port": 80,
      "url": "http://192.168.1.100:80/mjpeg",
      "type": "mjpeg",
      "path": "/mjpeg",
      "discovered_at": "2025-09-02T10:30:45.123456"
    },
    {
      "ip": "192.168.1.101", 
      "port": 554,
      "url": "rtsp://192.168.1.101:554/stream",
      "type": "rtsp",
      "path": "/stream",
      "discovered_at": "2025-09-02T10:30:47.654321"
    }
  ]
}
```

### 🔧 Configurare Camere IP

#### Camere Suportate
Serverul poate descoperi automat:
- **Camere IP standard** cu MJPEG over HTTP
- **Camere RTSP** (majoritatea camerelor IP moderne)
- **Camere Axis** cu endpoint-uri specifice
- **Camere de securitate** cu porturi comune (80, 554, 8080, 8081)

#### Porturi Scanate
```
80, 554, 8080, 8081, 8554, 1935, 443
```

#### Path-uri Testate
```
/video, /mjpeg, /mjpg/video.mjpg, /video.cgi, 
/videostream.cgi, /live, /stream, 
/cam/realmonitor?channel=1&subtype=0,
/axis-cgi/mjpg/video.cgi
```

#### Personalizare Scanare
```python
# În server_ip_camera.py, modifică:
CAMERA_PORTS = [80, 554, 8080]  # Doar porturile dorite
CAMERA_PATHS = ['/video', '/mjpeg']  # Doar path-urile necesare
```

### 🏠 Configurare Rețea

#### Cerințe Rețea
- Jetson și camerele IP în **aceeași rețea locală**
- **Ping enabled** pe camerele IP
- **Porturi deschise** pe camerele IP

#### Verificare Rețea
```bash
# Verifică IP-ul local
ip route | grep default

# Scanează rețeaua manual
nmap -sn 192.168.1.0/24

# Testează o cameră cunoscută
curl -I http://192.168.1.100/mjpeg
```

### Troubleshooting

**Problema: "jtop nu este disponibil"**
```bash
# Soluție:
sudo -H pip3 install jetson-stats
sudo reboot  # Necesar pentru încărcarea modulelor kernel
```

**Problema: "Nu s-a putut deschide camera USB"**
```bash
# Verifică permisiunile
ls -la /dev/video*
sudo chmod 666 /dev/video*

# Verifică că dispozitivul există
v4l2-ctl --list-devices

# Testează manual
ffmpeg -f v4l2 -i /dev/video0 -t 5 test.mp4
```

**Problema: "Eroare la pornirea containerului Docker"**
```bash
# Asigură-te că rulezi cu --privileged
docker run --privileged --device=/dev/video0 ...

# Verifică logs
docker logs unified-jetson-server
```

**Problema: "Nu sunt camere IP găsite"**
```bash
# Verifică rețeaua locală
ip route | grep default
ping 192.168.1.1  # gateway-ul routerului

# Scanează manual rețeaua
nmap -sn 192.168.1.0/24

# Verifică că rutează traficul
sudo tcpdump -i any icmp

# Rulează testul de descoperire
python3 test_ip_cameras.py
```

**Problema: "Stream-ul cameră IP nu funcționează"**
```bash
# Testează manual cu curl
curl -I http://192.168.1.100/mjpeg

# Testează cu ffmpeg
ffmpeg -f mjpeg -i http://192.168.1.100/mjpeg -t 5 test.mp4

# Testează RTSP
ffplay rtsp://192.168.1.100:554/stream

# Verifică firewall-ul pe cameră
telnet 192.168.1.100 80
```

**Problema: "Scanarea durează prea mult"**
```bash
# Reduce porturile scanate în server_ip_camera.py:
CAMERA_PORTS = [80, 554]  # doar porturile principale

# Reduce path-urile testate:
CAMERA_PATHS = ['/mjpeg', '/video']
```

## 📊 Monitorizare și Logs

### Logs în Timp Real
```bash
# Docker logs
docker logs -f jetson-server

# Logs direct
tail -f /var/log/unified-jetson-server.log
```

### Metrici Disponibile
- **CPU**: 30+ metrici per core și totale
- **GPU**: 50+ metrici detaliate (usage, memory, clocks, power states)
- **Temperaturi**: Toate senzorii hardware
- **Memorie**: RAM, SWAP, EMC, IRAM, cached, buffers
- **Power**: Toate rail-urile cu volt/curr/power/warn/crit
- **Sistema**: Board info, uptime, jetson_clocks, nvpmodel

### Export Date
```bash
# Descarcă toate datele ca CSV
curl http://localhost:8080/download_logs -o jetson_complete_data.csv

# Importă în Python pentru analiză
import pandas as pd
df = pd.read_csv('jetson_complete_data.csv')
print(df.describe())
```

## 🐳 Docker Commands Utile

```bash
# Construire
docker build -t unified-jetson-server .

# Rulare cu debugging
docker run -it --privileged --device=/dev/video0 -p 8080:8080 -p 8081:8081 unified-jetson-server

# Rulare în background
docker run -d --name jetson-server --privileged --device=/dev/video0 -p 8080:8080 -p 8081:8081 unified-jetson-server

# Vezi logs
docker logs -f jetson-server

# Oprire și curățare
docker stop jetson-server
docker rm jetson-server
docker rmi unified-jetson-server
```

## 📋 Structura Proiectului

```
aplicatie jetson/
├── server.py                 # Serverul principal unificat
├── Dockerfile                # Configurație Docker
├── requirements.txt          # Dependențe Python
├── README.md                 # Această documentație
├── setup.sh                  # Script setup interactiv
└── test_server.sh            # Script testare funcționalități
```

## 🔧 Dezvoltare

### Rulare în Modul Dezvoltare
```bash
# Cu auto-reload
export FLASK_ENV=development
python3 server.py

# Cu debugging
export PYTHONPATH=/path/to/project
export DEBUG=1
python3 server.py
```

### Testing
```bash
# Testează API-ul
curl -X GET http://localhost:8080/status
curl -X GET http://localhost:8080/metrics

# Testează WebRTC (necesită client WebRTC)
wscat -c ws://localhost:8081
```

## 📄 Licență

Acest proiect este open-source și disponibil sub licența MIT.

## 🤝 Contribuții

Contribuțiile sunt binevenite! Te rog:
1. Fork repository-ul
2. Creează un branch pentru feature-ul tău
3. Commit modificările
4. Creează un Pull Request

## 📞 Support

Pentru probleme și întrebări:
- Verifică secțiunea **Troubleshooting** 
- Deschide un issue pe GitHub
- Consultă documentația NVIDIA Jetson
