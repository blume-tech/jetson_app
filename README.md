# Unified Jetson Server

🚀 **Server unificat pentru monitorizarea sistemului Jetson și streaming video WebRTC**

Un server Python complet care combină monitorizarea detaliată a sistemului Jetson (CPU, GPU, memorie, temperaturi, power) cu capacități de streaming video WebRTC de la multiple camere USB.

## ✨ Funcționalități

### 📊 Monitorizare Jetson
- **CPU**: Usage per core, frequencies, governors, idle states
- **GPU**: Usage, frequencies, detailed metrics, memory usage
- **Temperaturi**: Toate senzorii disponibili cu limite max/critical
- **Memorie**: RAM, SWAP, EMC, IRAM cu detalii complete
- **Power**: Toate rail-urile de alimentare cu volt/curr/power
- **Export CSV**: Istoricul complet al datelor pentru analiză

### 📹 Streaming Video WebRTC
- Streaming în timp real de la multiple camere USB
- Protocoal WebRTC pentru latență minimă
- Suport pentru `/dev/video0`, `/dev/video1`, etc.
- Configurare automată rezoluție și frame rate

### 🌐 API REST
- `/metrics` - Ultimele metrici în timp real
- `/status` - Status server și funcționalități
- `/download_logs` - Export CSV complet
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

---

**Autor**: Claude AI Assistant  
**Versiune**: 1.0.0  
**Data**: August 26, 2025
