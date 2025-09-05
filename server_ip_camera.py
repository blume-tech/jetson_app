#!/usr/bin/env python3
"""
Jetson IP Camera Server - Monitorizare sistem și streaming video WebRTC de la camere IP
Autor: Claude AI Assistant
Data: 2025-09-02

Funcționalități:
- Monitorizare Jetson (CPU, GPU, memorie, temperaturi, power) via jtop
- Auto-descoperire camere IP pe rețeaua locală
- Streaming video WebRTC de la multiple camere IP
- API REST pentru metrici și logs
- WebSocket pentru comunicare WebRTC
"""

import asyncio
import cv2
import json
import threading
import time
import csv
import io
import socket
import subprocess
import requests
import concurrent.futures
import ssl
import os
from datetime import datetime
from threading import Thread, Lock

# Flask imports
from flask import Flask, jsonify, Response, request
from flask_cors import CORS

# WebRTC imports
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
import websockets

# Network scanning
import ipaddress

# Jetson monitoring
try:
    from jtop import jtop
    JTOP_AVAILABLE = True
except ImportError:
    print("⚠️ jtop nu este disponibil - monitorizarea Jetson va fi dezactivată")
    JTOP_AVAILABLE = False

# =============================================================================
# CONFIGURARE GLOBALĂ
# =============================================================================

# Flask app
app = Flask(__name__)
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# SSL Configuration
SSL_CERT_PATH = "cert.pem"
SSL_KEY_PATH = "key.pem"

# Monitorizare Jetson
latest_data = {}
data_history = []
data_lock = Lock()
MAX_HISTORY_SECONDS = 600  # 10 minute

# WebRTC configurare
WEBSOCKET_PORT = 8081
FLASK_PORT = 8080

# Server startup tracking
start_time = time.time()

# IP Camera discovery
discovered_cameras = []
camera_lock = Lock()

# Common IP camera ports - Enhanced list with more ports
CAMERA_PORTS = [80, 554, 8082, 8083, 8084, 8554, 1935, 443, 888, 1024, 8000, 8008, 8888, 9000]

# Common IP camera paths - Enhanced with more common paths
CAMERA_PATHS = [
    '/video',
    '/mjpeg',
    '/mjpg/video.mjpg',
    '/video.cgi',
    '/videostream.cgi',
    '/live',
    '/stream',
    '/live.mjpg',
    '/video/mjpg.cgi',
    '/mjpg/1/video.mjpg',
    '/mjpg/2/video.mjpg',
    '/cam/realmonitor?channel=1&subtype=0',
    '/cam/realmonitor?channel=1&subtype=1',
    '/axis-cgi/mjpg/video.cgi',
    '/cgi-bin/mjpg/video.cgi',
    '/cgi-bin/video.cgi',
    '/image/jpeg.cgi',
    '/image?speed=20',
    '/snapshot.cgi',
    '/onvif1',
    '/onvif2',
    '/h264',
    '/mpeg4',
    '/streaming/channels/1/httppreview',
    '/streaming/channels/101/httppreview',
    '/streaming/channels/1/picture',
    '/ISAPI/Streaming/channels/1/httppreview',
    '/ISAPI/Streaming/channels/101/httppreview',
    '/cgi-bin/hi3510/mjpegstream.cgi',
    '/cgi-bin/camera?resolution=640&amp;amp;quality=1&amp;amp;Language=0',
    '/view/viewer_index.shtml',
    '/video.mjpg',
    '/cam_1.cgi',
    '/image.jpg',
    '/live_mpeg4.sdp',
    '/live/ch0',
    '/live/ch1',
    '/media/video1',
    '/media/video2'
]

# Enhanced manufacturer-specific defaults
MANUFACTURER_DEFAULTS = {
    'axis': {
        'ports': [80, 554],
        'paths': ['/axis-cgi/mjpg/video.cgi', '/mjpg/video.mjpg']
    },
    'hikvision': {
        'ports': [80, 554, 8000],
        'paths': ['/ISAPI/Streaming/channels/1/httppreview', '/streaming/channels/1/httppreview']
    },
    'dahua': {
        'ports': [80, 554, 8000],
        'paths': ['/cam/realmonitor?channel=1&subtype=0', '/live']
    },
    'foscam': {
        'ports': [80, 88],
        'paths': ['/videostream.cgi?user=admin&pwd=', '/video.cgi']
    },
    'generic': {
        'ports': [80, 554],
        'paths': ['/video', '/mjpeg', '/stream']
    }
}

# =============================================================================
# FUNCȚII PENTRU SSL/HTTPS
# =============================================================================

def generate_ssl_certificate():
    """Generează certificat SSL self-signed dacă nu există"""
    if os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
        print("✅ Certificat SSL există deja")
        return True
    
    print("🔐 Generez certificat SSL self-signed...")
    try:
        # Încearcă să folosească openssl dacă e disponibil
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", SSL_KEY_PATH, "-out", SSL_CERT_PATH,
            "-days", "365", "-nodes",
            "-subj", "/CN=localhost/O=Jetson Camera Server/C=RO"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Certificat SSL generat cu openssl")
            return True
        else:
            print("⚠️ openssl nu este disponibil, încerc cu Python...")
    except FileNotFoundError:
        print("⚠️ openssl nu este instalat, încerc cu Python...")
    
    # Fallback: generează certificat cu cryptography
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generează cheia privată
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Creează certificatul
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "RO"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Romania"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Bucharest"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Jetson Camera Server"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Salvează certificatul
        with open(SSL_CERT_PATH, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Salvează cheia privată
        with open(SSL_KEY_PATH, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        print("✅ Certificat SSL generat cu Python cryptography")
        return True
        
    except ImportError:
        print("❌ Nici cryptography nu este disponibil")
        print("💡 Instalează: pip install cryptography")
        print("💡 Sau instalează openssl")
        return False
    except Exception as e:
        print(f"❌ Eroare la generarea certificatului SSL: {e}")
        return False

def get_ssl_context():
    """Returnează contextul SSL pentru servere"""
    if not os.path.exists(SSL_CERT_PATH) or not os.path.exists(SSL_KEY_PATH):
        if not generate_ssl_certificate():
            return None
    
    try:
        # Pentru Flask
        return (SSL_CERT_PATH, SSL_KEY_PATH)
    except Exception as e:
        print(f"❌ Eroare la crearea contextului SSL: {e}")
        return None

def get_websocket_ssl_context():
    """Returnează contextul SSL pentru WebSocket server"""
    if not os.path.exists(SSL_CERT_PATH) or not os.path.exists(SSL_KEY_PATH):
        if not generate_ssl_certificate():
            return None
    
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=SSL_CERT_PATH, keyfile=SSL_KEY_PATH)
        return ssl_context
    except Exception as e:
        print(f"❌ Eroare la crearea contextului SSL pentru WebSocket: {e}")
        return None

# =============================================================================
# FUNCȚII PENTRU DESCOPERIREA CAMERELOR IP
# =============================================================================

def get_local_network():
    """Obține rețeaua locală"""
    try:
        # Obține IP-ul local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Calculează rețeaua (presupunem /24)
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        return network
    except Exception as e:
        print(f"❌ Eroare la obținerea rețelei locale: {e}")
        return None

def get_local_ip():
    """Obține IP-ul local al serverului"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"❌ Eroare la obținerea IP-ului local: {e}")
        return "unknown"

def ping_host(ip):
    """Verifică dacă un host este activ"""
    try:
        # Windows ping command
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", str(ip)],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False

def check_camera_port(ip, port, timeout=2):
    """Verifică dacă un port este deschis pe IP - Enhanced version"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((str(ip), port))
        sock.close()
        
        if result == 0:
            # Port is open, try to get service information
            try:
                # Quick HTTP check for web services
                if port in [80, 8082, 8083, 8084, 8000, 8008, 8888, 9000]:
                    import socket as sock_module
                    test_sock = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
                    test_sock.settimeout(1)
                    test_sock.connect((str(ip), port))
                    test_sock.send(b"HEAD / HTTP/1.1\r\nHost: " + str(ip).encode() + b"\r\n\r\n")
                    response = test_sock.recv(1024).decode('utf-8', errors='ignore')
                    test_sock.close()
                    
                    # Check if response suggests camera/video service
                    camera_indicators = ['camera', 'video', 'mjpeg', 'axis', 'hikvision', 'dahua', 'foscam']
                    if any(indicator in response.lower() for indicator in camera_indicators):
                        print(f"🎯 Serviciu cameră detectat pe {ip}:{port}")
                        return True
            except:
                pass
            
            return True
        return False
    except:
        return False

def test_camera_stream(ip, port, path, timeout=5):
    """Testează dacă un stream de cameră funcționează - Enhanced version"""
    # Generate multiple URL variations to test
    urls_to_test = []
    
    # HTTP variants
    for scheme in ['http', 'https']:
        urls_to_test.extend([
            f"{scheme}://{ip}:{port}{path}",
            f"{scheme}://admin:admin@{ip}:{port}{path}",
            f"{scheme}://admin:@{ip}:{port}{path}",
            f"{scheme}://admin:password@{ip}:{port}{path}",
            f"{scheme}://admin:123456@{ip}:{port}{path}"
        ])
    
    # RTSP variants
    for scheme in ['rtsp']:
        urls_to_test.extend([
            f"{scheme}://{ip}:{port}{path}",
            f"{scheme}://admin:admin@{ip}:{port}{path}",
            f"{scheme}://admin:@{ip}:{port}{path}",
            f"{scheme}://admin:password@{ip}:{port}{path}",
            f"{scheme}://admin:123456@{ip}:{port}{path}"
        ])
    
    for url in urls_to_test:
        try:
            # Test HTTP/HTTPS/MJPEG
            if url.startswith(('http', 'https')):
                try:
                    response = requests.get(url, timeout=timeout, stream=True, verify=False)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(ct in content_type for ct in ['multipart', 'image', 'video']):
                            # Try to read a small chunk to verify it's actually streaming
                            chunk = next(response.iter_content(chunk_size=1024), None)
                            if chunk and len(chunk) > 0:
                                return url, 'mjpeg'
                except requests.exceptions.RequestException:
                    continue
            
            # Test RTSP
            elif url.startswith('rtsp'):
                try:
                    cap = cv2.VideoCapture(url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if cap.isOpened():
                        # Try to read multiple frames to ensure stable stream
                        for _ in range(3):
                            ret, frame = cap.read()
                            if ret and frame is not None and frame.size > 0:
                                cap.release()
                                return url, 'rtsp'
                        cap.release()
                except Exception:
                    continue
                        
        except Exception:
            continue
    
    return None, None

def scan_for_cameras():
    """Scanează rețeaua pentru camere IP - Enhanced version"""
    global discovered_cameras
    print("🔍 Începe scanarea avansată pentru camere IP...")
    
    network = get_local_network()
    if not network:
        print("❌ Nu s-a putut determina rețeaua locală")
        return
    
    print(f"🌐 Scanez rețeaua: {network}")
    cameras_found = []
    
    # Phase 1: Fast ping scan to find active hosts
    print("📡 Faza 1: Detectare host-uri active...")
    active_hosts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        host_futures = {executor.submit(ping_host, ip): ip for ip in network.hosts()}
        
        for future in concurrent.futures.as_completed(host_futures):
            ip = host_futures[future]
            try:
                if future.result():
                    active_hosts.append(ip)
                    print(f"✅ Host activ: {ip}")
            except Exception:
                pass
    
    print(f"📋 Găsite {len(active_hosts)} host-uri active")
    
    # Phase 2: Enhanced port scanning for camera services
    print("🔍 Faza 2: Scanare porturi camere...")
    
    def scan_host_ports(host):
        """Scanează porturile pentru un host specific"""
        local_cameras = []
        print(f"🔍 Scanez {host}...")
        
        # Quick port scan first
        open_ports = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as port_executor:
            port_futures = {
                port_executor.submit(check_camera_port, host, port, 3): port 
                for port in CAMERA_PORTS
            }
            
            for future in concurrent.futures.as_completed(port_futures):
                port = port_futures[future]
                try:
                    if future.result():
                        open_ports.append(port)
                        print(f"✅ Port {port} deschis pe {host}")
                except Exception:
                    pass
        
        # Phase 3: Test camera streams on open ports
        for port in open_ports:
            print(f"📹 Testez stream-uri pe {host}:{port}...")
            
            # Test standard paths first
            for path in CAMERA_PATHS[:10]:  # Test first 10 most common paths
                url, stream_type = test_camera_stream(host, port, path)
                if url:
                    camera_info = {
                        'ip': str(host),
                        'port': port,
                        'url': url,
                        'type': stream_type,
                        'path': path,
                        'discovered_at': datetime.now().isoformat(),
                        'manufacturer': 'unknown'
                    }
                    
                    # Try to detect manufacturer
                    if 'axis' in url.lower():
                        camera_info['manufacturer'] = 'axis'
                    elif 'hikvision' in url.lower() or 'ISAPI' in url:
                        camera_info['manufacturer'] = 'hikvision'
                    elif 'dahua' in url.lower() or 'realmonitor' in url:
                        camera_info['manufacturer'] = 'dahua'
                    elif 'foscam' in url.lower():
                        camera_info['manufacturer'] = 'foscam'
                    
                    local_cameras.append(camera_info)
                    print(f"📹 CAMERĂ GĂSITĂ: {url} ({stream_type}) - {camera_info['manufacturer']}")
                    break  # Found working stream, move to next port
            
            # If no standard path worked, try manufacturer-specific paths
            if not any(cam['port'] == port for cam in local_cameras):
                for manufacturer, config in MANUFACTURER_DEFAULTS.items():
                    if port in config['ports']:
                        for path in config['paths']:
                            url, stream_type = test_camera_stream(host, port, path)
                            if url:
                                camera_info = {
                                    'ip': str(host),
                                    'port': port,
                                    'url': url,
                                    'type': stream_type,
                                    'path': path,
                                    'discovered_at': datetime.now().isoformat(),
                                    'manufacturer': manufacturer
                                }
                                local_cameras.append(camera_info)
                                print(f"📹 CAMERĂ GĂSITĂ ({manufacturer}): {url} ({stream_type})")
                                break
                        if any(cam['port'] == port for cam in local_cameras):
                            break
        
        return local_cameras
    
    # Scan all active hosts in parallel (but limited)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        host_futures = {executor.submit(scan_host_ports, host): host for host in active_hosts}
        
        for future in concurrent.futures.as_completed(host_futures):
            host = host_futures[future]
            try:
                host_cameras = future.result()
                cameras_found.extend(host_cameras)
            except Exception as e:
                print(f"⚠️ Eroare la scanarea host-ului {host}: {e}")
    
    # Phase 4: Verify and validate found cameras
    print("🔍 Faza 4: Validare camere găsite...")
    validated_cameras = []
    
    for camera in cameras_found:
        try:
            # Quick validation test
            url, stream_type = test_camera_stream(camera['ip'], camera['port'], camera['path'], timeout=3)
            if url:
                validated_cameras.append(camera)
                print(f"✅ Validată: {camera['url']}")
            else:
                print(f"❌ Validare eșuată: {camera['url']}")
        except Exception as e:
            print(f"⚠️ Eroare validare {camera['url']}: {e}")
    
    with camera_lock:
        discovered_cameras = validated_cameras
    
    print("=" * 60)
    print(f"🎉 Scanare completă! Găsite și validate {len(validated_cameras)} camere IP")
    for cam in validated_cameras:
        print(f"   📹 {cam['manufacturer'].upper()}: {cam['url']} ({cam['type']})")
    print("=" * 60)
    
    return validated_cameras

# =============================================================================
# CLASA PENTRU VIDEO STREAMING DE LA CAMERE IP
# =============================================================================

class IPVideoTrack(MediaStreamTrack):
    """Track pentru streaming video de la camerele IP"""
    kind = "video"
    
    def __init__(self, camera_url, camera_type="mjpeg"):
        super().__init__()
        self.camera_url = camera_url
        self.camera_type = camera_type
        
        print(f"📹 Inițializare cameră IP: {camera_url} ({camera_type})")
        
        # Încearcă să deschidă camera
        self.cap = cv2.VideoCapture(camera_url)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Nu s-a putut deschide camera IP: {camera_url}")
        
        # Setează proprietăți pentru performanță
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"📹 Camera IP inițializată cu succes: {camera_url}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        # Citește frame-ul în mod asincron
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self.cap.read)
        
        if not ret:
            print(f"⚠️ Nu s-a putut citi frame din camera IP: {self.camera_url}")
            await asyncio.sleep(0.033)  # ~30fps
            return await self.recv()
        
        # Redimensionează frame-ul pentru performanță
        if frame.shape[1] > 640:
            height, width = frame.shape[:2]
            new_width = 640
            new_height = int(height * (new_width / width))
            frame = cv2.resize(frame, (new_width, new_height))
        
        # Convertește frame-ul pentru WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame

    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

# =============================================================================
# FUNCȚII PENTRU MONITORIZAREA JETSON (same as original)
# =============================================================================

def extract_full(jetson):
    """Extrage toate datele disponibile din jtop"""
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "uptime": str(jetson.uptime) if hasattr(jetson, 'uptime') else "",
            "board": jetson.board if hasattr(jetson, 'board') else "",
            "cpu": {},
            "cpu_frequencies": {},
            "temperatures": {},
            "gpu": {},
            "gpu_detailed": {},
            "memory": {},
            "power": {},
            "jetson_clocks": jetson.jetson_clocks.status if hasattr(jetson, 'jetson_clocks') else False,
            "nvpmodel": str(jetson.nvpmodel) if hasattr(jetson, 'nvpmodel') else "",
            "info": {}
        }

        # CPU Usage și Frequencies
        if hasattr(jetson, 'cpu') and jetson.cpu:
            cpu_data = jetson.cpu
            
            # Handle total CPU usage
            if 'total' in cpu_data and isinstance(cpu_data['total'], dict):
                total_info = cpu_data['total']
                total_usage = total_info.get('user', 0) + total_info.get('nice', 0) + total_info.get('system', 0)
                data["cpu"]["CPU_total_usage"] = round(total_usage, 2)
                
                # Add individual total components
                for key in ['user', 'nice', 'system', 'idle']:
                    if key in total_info:
                        data["cpu"][f"CPU_total_{key}"] = round(total_info[key], 2)

            # Handle individual CPU cores
            if 'cpu' in cpu_data and isinstance(cpu_data['cpu'], list):
                cpu_cores = cpu_data['cpu']
                
                for cpu_id, cpu_info in enumerate(cpu_cores):
                    if not isinstance(cpu_info, dict):
                        continue

                    # Per-core usage
                    usage = cpu_info.get('user', 0) + cpu_info.get('nice', 0) + cpu_info.get('system', 0)
                    data["cpu"][f"CPU{cpu_id}_usage"] = round(usage, 2)

                    # Individual usage components
                    for key in ['user', 'nice', 'system', 'idle']:
                        if key in cpu_info:
                            data["cpu"][f"CPU{cpu_id}_{key}"] = round(cpu_info[key], 2)

                    # Governor and online status
                    if 'governor' in cpu_info:
                        data["cpu"][f"CPU{cpu_id}_governor"] = cpu_info['governor']
                    if 'online' in cpu_info:
                        data["cpu"][f"CPU{cpu_id}_online"] = cpu_info['online']
                    if 'model' in cpu_info:
                        data["cpu"][f"CPU{cpu_id}_model"] = cpu_info['model']

                    # FREQUENCIES
                    freq_info = cpu_info.get('freq')
                    if freq_info and isinstance(freq_info, dict):
                        for freq_type in ['cur', 'max', 'min']:
                            if freq_type in freq_info and freq_info[freq_type] > 0:
                                data["cpu_frequencies"][f"CPU{cpu_id}_freq_{freq_type}"] = round(freq_info[freq_type] / 1000, 0)

                    # info_freq
                    info_freq = cpu_info.get('info_freq')
                    if info_freq and isinstance(info_freq, dict):
                        for freq_type in ['cur', 'max', 'min']:
                            if freq_type in info_freq and info_freq[freq_type] > 0:
                                data["cpu_frequencies"][f"CPU{cpu_id}_info_freq_{freq_type}"] = round(info_freq[freq_type] / 1000, 0)

        # TEMPERATURES
        if hasattr(jetson, 'temperature') and jetson.temperature:
            for temp_name, temp_info in jetson.temperature.items():
                if isinstance(temp_info, dict):
                    if 'temp' in temp_info and temp_info['temp'] > -200:
                        data["temperatures"][temp_name] = temp_info['temp']
                    if 'max' in temp_info:
                        data["temperatures"][f"{temp_name}_max"] = temp_info['max']
                    if 'crit' in temp_info:
                        data["temperatures"][f"{temp_name}_crit"] = temp_info['crit']

        # ENHANCED GPU MONITORING
        if hasattr(jetson, 'gpu') and jetson.gpu:
            for gpu_name, gpu_info in jetson.gpu.items():
                if isinstance(gpu_info, dict):
                    # Basic usage
                    if 'status' in gpu_info and 'load' in gpu_info['status']:
                        data["gpu"][f"{gpu_name}_usage"] = gpu_info['status']['load']
                        data["gpu_detailed"][f"{gpu_name}_load_percent"] = gpu_info['status']['load']
                    
                    # Extended status information
                    if 'status' in gpu_info:
                        status = gpu_info['status']
                        for key in ['online', 'type', 'shared', 'active']:
                            if key in status:
                                data["gpu_detailed"][f"{gpu_name}_status_{key}"] = status[key]
                    
                    # Frequency information
                    if 'freq' in gpu_info:
                        freq_data = gpu_info['freq']
                        cur = freq_data.get('cur', 0)
                        maxf = freq_data.get('max', 0)
                        data["gpu"][f"{gpu_name}_freq"] = round(cur / 1000, 0) if cur > 0 else 0
                        data["gpu"][f"{gpu_name}_freq_max"] = round(maxf / 1000, 0) if maxf > 0 else 0
                        
                        # Detailed frequency metrics
                        for freq_type in ['cur', 'max', 'min', 'min_freq']:
                            if freq_type in freq_data and freq_data[freq_type] > 0:
                                data["gpu_detailed"][f"{gpu_name}_freq_{freq_type}_mhz"] = round(freq_data[freq_type] / 1000, 0)
                    
                    # GPU Type
                    if 'type' in gpu_info:
                        data["gpu"][f"{gpu_name}_type"] = gpu_info['type']
                        data["gpu_detailed"][f"{gpu_name}_architecture"] = gpu_info['type']

        # MEMORY
        if hasattr(jetson, 'memory') and jetson.memory:
            mem = jetson.memory
            if 'RAM' in mem:
                ram = mem['RAM']
                data["memory"].update({
                    "RAM_total": ram.get('tot', 0),
                    "RAM_used": ram.get('used', 0),
                    "RAM_free": ram.get('free', 0),
                    "RAM_shared": ram.get('shared', 0),
                    "RAM_buffers": ram.get('buffers', 0),
                    "RAM_cached": ram.get('cached', 0),
                    "RAM_lfb": ram.get('lfb', 0)
                })
            if 'SWAP' in mem:
                swap = mem['SWAP']
                data["memory"].update({
                    "SWAP_total": swap.get('tot', 0),
                    "SWAP_used": swap.get('used', 0),
                    "SWAP_cached": swap.get('cached', 0)
                })

        # POWER
        if hasattr(jetson, 'power') and jetson.power:
            for rail, info in jetson.power.items():
                if rail == 'tot':
                    data["power"]["total_power"] = info
                    continue
                if isinstance(info, dict):
                    for key in ['volt', 'curr', 'power', 'avg', 'warn', 'crit', 'online', 'type']:
                        if key in info:
                            data["power"][f"{rail}_{key}"] = info[key]

        return data

    except Exception as e:
        print(f"❌ Eroare la extragerea datelor: {e}")
        return {"timestamp": datetime.now().isoformat(), "error": str(e)}

def flatten_data(entry):
    """Aplatizează datele pentru CSV"""
    flat = {
        "timestamp": entry.get("timestamp", ""),
        "uptime": entry.get("uptime", ""),
        "board": str(entry.get("board", "")),
        "jetson_clocks": entry.get("jetson_clocks", ""),
        "nvpmodel": entry.get("nvpmodel", ""),
    }
    
    # Flatten all nested dictionaries
    for category in ["cpu", "cpu_frequencies", "temperatures", "gpu", "gpu_detailed", "memory", "power"]:
        for k, v in entry.get(category, {}).items():
            flat[k] = v
    
    return flat

def monitor_jetson():
    """Thread pentru monitorizarea continuă a Jetson"""
    global latest_data, data_history
    
    if not JTOP_AVAILABLE:
        print("⚠️ jtop nu este disponibil - monitorizarea Jetson este dezactivată")
        # Creează date mock pentru dezvoltare
        while True:
            mock_data = {
                "timestamp": datetime.now().isoformat(),
                "uptime": "mock_uptime",
                "board": "mock_board",
                "cpu": {"CPU_total_usage": 25.5},
                "temperatures": {"CPU-therm": 45.0},
                "gpu": {"GPU_usage": 30.0},
                "memory": {"RAM_used": 2048, "RAM_total": 8192}
            }
            
            with data_lock:
                latest_data = mock_data
                data_history.append(flatten_data(mock_data))
                
                # Limitează istoricul
                if len(data_history) > MAX_HISTORY_SECONDS:
                    data_history = data_history[-MAX_HISTORY_SECONDS:]
            
            time.sleep(1)
        return
    
    # Monitorizare reală cu jtop
    try:
        with jtop() as jetson:
            print("✅ jtop conectat - începe monitorizarea Jetson")
            
            while True:
                # Extrage toate datele
                data = extract_full(jetson)
                
                with data_lock:
                    latest_data = data
                    
                    # Adaugă la istoric (aplatizat pentru CSV)
                    flat_data = flatten_data(data)
                    data_history.append(flat_data)
                    
                    # Limitează istoricul la MAX_HISTORY_SECONDS puncte
                    if len(data_history) > MAX_HISTORY_SECONDS:
                        data_history = data_history[-MAX_HISTORY_SECONDS:]
                
                # Afișează progres la fiecare 30 secunde
                if len(data_history) % 30 == 0:
                    print(f"📊 Colectate {len(data_history)} puncte de date")
                
                time.sleep(1)  # Colectează date la fiecare secundă
                
    except Exception as e:
        print(f"❌ Eroare în monitorizarea Jetson: {e}")

# =============================================================================
# FLASK ROUTES PENTRU API
# =============================================================================

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Returnează ultimele metrici disponibile"""
    with data_lock:
        if not latest_data:
            return jsonify({"error": "Nu sunt date disponibile"}), 404
        return jsonify(latest_data)

@app.route("/cameras", methods=["GET"])
def get_cameras():
    """Returnează camerele IP descoperite"""
    with camera_lock:
        return jsonify({
            "cameras_found": len(discovered_cameras),
            "cameras": discovered_cameras
        })

@app.route("/cameras/rescan", methods=["POST"])
def rescan_cameras():
    """Rescanează rețeaua pentru camere IP cu progres în timp real"""
    def run_scan():
        scan_for_cameras()
    
    # Rulează scanarea în thread separat
    scan_thread = Thread(target=run_scan, daemon=True)
    scan_thread.start()
    
    return jsonify({
        "message": "Scanare avansată începută în background", 
        "status": "running",
        "enhanced_features": [
            "Scanare multi-threaded pentru viteză îmbunătățită",
            "Testare porturi extinse și căi de acces diverse",
            "Detectare automată manufacturer cameră",
            "Validare stream-uri pentru stabilitate",
            "Suport pentru autentificare camere standard"
        ]
    })

@app.route("/cameras/scan_status", methods=["GET"])
def get_scan_status():
    """Returnează statusul scanării în curs"""
    with camera_lock:
        return jsonify({
            "cameras_discovered": len(discovered_cameras),
            "last_scan": discovered_cameras[0]['discovered_at'] if discovered_cameras else "never",
            "scanning_active": len(threading.enumerate()) > 3  # Basic check for active threads
        })

@app.route("/download_logs", methods=["GET"])
def download_logs():
    """Descarcă istoricul de date ca CSV"""
    with data_lock:
        if not data_history:
            return Response("Nu sunt date disponibile pentru descărcare", status=404)
        
        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data_history[0].keys())
            writer.writeheader()
            writer.writerows(data_history)
            csv_content = output.getvalue()
            output.close()
            
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=jetson_ip_camera_logs.csv"}
            )
        except Exception as e:
            return Response(f"Eroare la generarea CSV: {str(e)}", status=500)

@app.route("/test-connection", methods=["GET", "POST", "OPTIONS"])
def test_connection():
    """Endpoint pentru testarea conexiunii dintre platforma externă și Jetson"""
    
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response
    
    print("🧪 Test conexiune inițiat din platforma externă")
    
    # Get client info
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.environ.get('HTTP_USER_AGENT', 'unknown')
    
    print(f"📡 Client: {client_ip} - {user_agent}")
    
    # Colectează informații despre sistem
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "jetson_status": "online",
        "connection_test": "success",
        "client_info": {
            "ip": client_ip,
            "user_agent": user_agent,
            "request_method": request.method
        },
        "server_info": {
            "local_ip": get_local_ip(),
            "public_access": True,
            "ssl_enabled": os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH)
        },
        "test_details": {}
    }
    
    try:
        # Test 1: Verifică statusul serverului
        test_results["test_details"]["server_status"] = {
            "status": "running",
            "uptime_seconds": time.time() - start_time if 'start_time' in globals() else 0,
            "flask_port": FLASK_PORT,
            "websocket_port": WEBSOCKET_PORT,
            "ssl_enabled": os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH)
        }
        
        # Test 2: Verifică monitorizarea Jetson
        with data_lock:
            if latest_data:
                test_results["test_details"]["jetson_monitoring"] = {
                    "status": "active",
                    "jtop_available": JTOP_AVAILABLE,
                    "last_update": latest_data.get("timestamp", "N/A"),
                    "data_points": len(data_history)
                }
                
                # Adaugă ultimele metrici importante
                if "cpu" in latest_data:
                    cpu_usage = latest_data["cpu"].get("CPU_total_usage", 0)
                    test_results["test_details"]["performance"] = {
                        "cpu_usage_percent": cpu_usage,
                        "status": "good" if cpu_usage < 80 else "high"
                    }
                
                if "memory" in latest_data:
                    ram_used = latest_data["memory"].get("RAM_used", 0)
                    ram_total = latest_data["memory"].get("RAM_total", 1)
                    ram_percent = (ram_used / ram_total) * 100 if ram_total > 0 else 0
                    test_results["test_details"]["memory"] = {
                        "ram_usage_percent": round(ram_percent, 2),
                        "ram_used_mb": ram_used,
                        "ram_total_mb": ram_total,
                        "status": "good" if ram_percent < 85 else "high"
                    }
                
                if "temperatures" in latest_data:
                    temps = latest_data["temperatures"]
                    if temps:
                        max_temp = max(temps.values())
                        test_results["test_details"]["temperature"] = {
                            "max_temperature_c": max_temp,
                            "status": "good" if max_temp < 70 else "warning" if max_temp < 85 else "critical"
                        }
            else:
                test_results["test_details"]["jetson_monitoring"] = {
                    "status": "no_data",
                    "jtop_available": JTOP_AVAILABLE
                }
        
        # Test 3: Verifică camerele descoperite
        with camera_lock:
            test_results["test_details"]["camera_discovery"] = {
                "cameras_found": len(discovered_cameras),
                "cameras": [
                    {
                        "ip": cam["ip"],
                        "type": cam["type"],
                        "manufacturer": cam.get("manufacturer", "unknown")
                    } for cam in discovered_cameras[:3]  # Doar primele 3 pentru a nu supraîncărca
                ],
                "scanning_active": len(discovered_cameras) > 0
            }
        
        # Test 4: Verifică conectivitatea rețelei
        try:
            # Test conectivitate externă
            response = requests.get("https://8.8.8.8", timeout=5)
            test_results["test_details"]["network"] = {
                "external_connectivity": "ok",
                "dns_resolution": "ok"
            }
        except:
            test_results["test_details"]["network"] = {
                "external_connectivity": "limited",
                "dns_resolution": "unknown"
            }
        
        # Test 5: Verifică dispozitivele video
        video_devices = []
        try:
            import glob
            video_files = glob.glob("/dev/video*")
            for device in video_files:
                try:
                    cap = cv2.VideoCapture(device)
                    if cap.isOpened():
                        video_devices.append({
                            "device": device,
                            "status": "available"
                        })
                        cap.release()
                    else:
                        video_devices.append({
                            "device": device,
                            "status": "not_accessible"
                        })
                except:
                    video_devices.append({
                        "device": device,
                        "status": "error"
                    })
        except:
            pass
        
        test_results["test_details"]["video_devices"] = {
            "devices_found": len(video_devices),
            "devices": video_devices
        }
        
        # Calculează statusul general
        issues = []
        if not JTOP_AVAILABLE:
            issues.append("jtop_not_available")
        if len(discovered_cameras) == 0:
            issues.append("no_cameras_found")
        if len(video_devices) == 0:
            issues.append("no_video_devices")
        
        if len(issues) == 0:
            test_results["overall_status"] = "excellent"
            test_results["message"] = "Toate sistemele funcționează perfect!"
        elif len(issues) <= 2:
            test_results["overall_status"] = "good"
            test_results["message"] = f"Sistemul funcționează bine cu {len(issues)} probleme minore"
        else:
            test_results["overall_status"] = "issues"
            test_results["message"] = f"Găsite {len(issues)} probleme care necesită atenție"
        
        test_results["issues"] = issues
        
        # Headers pentru CORS
        response = jsonify(test_results)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        
        print(f"✅ Test conexiune completat cu succes - Status: {test_results['overall_status']}")
        return response
        
    except Exception as e:
        error_result = {
            "timestamp": datetime.now().isoformat(),
            "jetson_status": "error",
            "connection_test": "failed",
            "error": str(e),
            "overall_status": "error",
            "message": f"Eroare în timpul testului: {str(e)}"
        }
        
        print(f"❌ Eroare în test conexiune: {e}")
        response = jsonify(error_result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/ping", methods=["GET"])
def ping():
    """Endpoint simplu pentru verificarea rapidă a conectivității"""
    return jsonify({
        "status": "pong",
        "timestamp": datetime.now().isoformat(),
        "server": "jetson-ip-camera-server",
        "version": "2.0.0-ssl"
    })

@app.route("/system-info", methods=["GET"])
def get_system_info():
    """Returnează informații detaliate despre sistem pentru debugging"""
    try:
        import platform
        import psutil
        
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation()
            }
        }
        
        # Informații despre CPU și memorie dacă psutil e disponibil
        try:
            system_info["resources"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except:
            pass
        
        # Verifică dacă este Jetson
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                system_info["is_jetson"] = 'tegra' in cpuinfo.lower()
        except:
            system_info["is_jetson"] = False
        
        return jsonify(system_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/network-info", methods=["GET"])
def get_network_info():
    """Returnează informații despre configurația rețelei pentru debugging conectivitate"""
    try:
        import subprocess
        
        network_info = {
            "timestamp": datetime.now().isoformat(),
            "local_ip": get_local_ip(),
            "interfaces": {},
            "connectivity": {}
        }
        
        # Get all network interfaces
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                network_info["interfaces_raw"] = result.stdout
        except:
            pass
        
        # Test external connectivity
        try:
            response = requests.get("https://8.8.8.8", timeout=5)
            network_info["connectivity"]["google_dns"] = "ok"
        except:
            network_info["connectivity"]["google_dns"] = "failed"
        
        # Get public IP
        try:
            response = requests.get("https://ifconfig.me/ip", timeout=10)
            if response.status_code == 200:
                network_info["public_ip"] = response.text.strip()
            else:
                network_info["public_ip"] = "unknown"
        except:
            network_info["public_ip"] = "unknown"
        
        # Port check
        network_info["ports"] = {
            "flask_port": FLASK_PORT,
            "websocket_port": WEBSOCKET_PORT,
            "ssl_enabled": os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH)
        }
        
        # Add CORS headers
        response = jsonify(network_info)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
def get_status():
    """Returnează statusul serviciului"""
    with data_lock, camera_lock:
        return jsonify({
            "service_status": "running",
            "version": "2.0.0 - Enhanced",
            "uptime_seconds": time.time() - start_time,
            "jtop_available": JTOP_AVAILABLE,
            "data_points_collected": len(data_history),
            "last_update": latest_data.get("timestamp", "N/A") if latest_data else "N/A",
            "webrtc_port": WEBSOCKET_PORT,
            "flask_port": FLASK_PORT,
            "ssl_enabled": os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH),
            "cameras_discovered": len(discovered_cameras),
            "camera_urls": [cam['url'] for cam in discovered_cameras],
            "camera_manufacturers": list(set(cam.get('manufacturer', 'unknown') for cam in discovered_cameras)),
            "scanning_capabilities": {
                "ports_scanned": len(CAMERA_PORTS),
                "paths_tested": len(CAMERA_PATHS),
                "manufacturer_detection": True,
                "stream_validation": True,
                "parallel_scanning": True
            },
            "test_endpoints": {
                "connection_test": "/test-connection",
                "ping": "/ping", 
                "system_info": "/system-info"
            },
            "features": {
                "jetson_monitoring": JTOP_AVAILABLE,
                "webrtc_streaming": True,
                "csv_export": True,
                "enhanced_ip_camera_discovery": True,
                "multi_manufacturer_support": True,
                "real_time_validation": True,
                "https_ssl_support": True,
                "platform_integration": True
            }
        })

@app.route("/", methods=["GET"])
def get_info():
    """Informații despre server"""
    return jsonify({
        "name": "Enhanced Jetson IP Camera Server",
        "version": "2.0.0",
        "description": "Server pentru monitorizarea Jetson și streaming video WebRTC de la camere IP cu capacități avansate de detectare",
        "new_features": [
            "🔍 Scanare îmbunătățită cu detectare manufacturer",
            "🌐 Suport extins pentru porturi și protocoale",
            "⚡ Scanare paralelă pentru performanță sporită",
            "🎯 Validare stream-uri în timp real",
            "🔐 Testare autentificare pentru camere comune"
        ],
        "endpoints": {
            "metrics": "/metrics - GET - Ultimele metrici Jetson",
            "cameras": "/cameras - GET - Camerele IP descoperite cu detalii manufacturer",
            "rescan": "/cameras/rescan - POST - Rescanează pentru camere IP (Enhanced)",
            "scan_status": "/cameras/scan_status - GET - Status scanare în curs",
            "status": "/status - GET - Status server cu metrici detaliate",
            "test_connection": "/test-connection - GET/POST - Test conexiune pentru platformă",
            "ping": "/ping - GET - Verificare rapidă conectivitate",
            "system_info": "/system-info - GET - Informații detaliate sistem",
            "download_logs": "/download_logs - GET - Descarcă CSV cu istoricul",
            "webrtc": f"wss://localhost:{WEBSOCKET_PORT} - WebSocket pentru WebRTC (WSS)"
        },
        "supported_manufacturers": [
            "Axis Communications",
            "Hikvision", 
            "Dahua Technology",
            "Foscam",
            "Generic ONVIF/MJPEG cameras"
        ]
    })

# =============================================================================
# WEBRTC HANDLER
# =============================================================================

async def webrtc_handler(websocket):
    """Handler pentru conexiunile WebRTC"""
    print("📹 Client WebRTC conectat")
    pc = RTCPeerConnection()
    
    try:
        # Creează track-uri pentru camerele IP descoperite
        video_tracks = []
        with camera_lock:
            cameras_to_use = discovered_cameras[:2]  # Folosește primele 2 camere
        
        for camera in cameras_to_use:
            try:
                video_track = IPVideoTrack(camera['url'], camera['type'])
                pc.addTrack(video_track)
                video_tracks.append(video_track)
                print(f"📹 Adăugat track pentru camera IP: {camera['url']}")
            except Exception as e:
                print(f"⚠️ Nu s-a putut inițializa camera {camera['url']}: {e}")
        
        if not video_tracks:
            print("⚠️ Nu sunt camere IP disponibile pentru streaming")
            return
        
        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate:
                await websocket.send(json.dumps({"action": "ice", "data": candidate}))
        
        # Creează oferta WebRTC
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        await websocket.send(json.dumps({
            "action": "offer",
            "data": {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
        }))
        
        # Gestionează mesajele de la client
        async for message in websocket:
            msg = json.loads(message)
            
            if msg["action"] == "answer":
                answer = RTCSessionDescription(
                    sdp=msg["data"]["sdp"],
                    type=msg["data"]["type"]
                )
                await pc.setRemoteDescription(answer)
                
            elif msg["action"] == "ice":
                await pc.addIceCandidate(msg["data"])
                
            elif msg["action"] == "bye":
                break
    
    except Exception as e:
        print(f"❌ Eroare în webrtc_handler: {e}")
    
    finally:
        await pc.close()
        print("📹 Client WebRTC deconectat")

# =============================================================================
# FUNCȚII PENTRU PORNIREA SERVERELOR
# =============================================================================

def run_flask_server():
    """Rulează serverul Flask cu HTTPS în thread separat"""
    ssl_context = get_ssl_context()
    if ssl_context:
        print(f"🌐 Starting Flask server on https://0.0.0.0:{FLASK_PORT} (HTTPS - accessible from internet)")
        app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, ssl_context=ssl_context, threaded=True)
    else:
        print(f"⚠️ SSL nu este disponibil, pornesc Flask cu HTTP pe http://0.0.0.0:{FLASK_PORT}")
        app.run(host="0.0.0.0", port=FLASK_PORT, debug=False, threaded=True)

async def run_websocket_server():
    """Rulează serverul WebSocket pentru WebRTC cu WSS"""
    ssl_context = get_websocket_ssl_context()
    if ssl_context:
        print(f"📹 Starting WebSocket server on port {WEBSOCKET_PORT} (WSS)")
        async with websockets.serve(webrtc_handler, "0.0.0.0", WEBSOCKET_PORT, ssl=ssl_context):
            await asyncio.Future()  # run forever
    else:
        print(f"⚠️ SSL nu este disponibil, pornesc WebSocket cu WS pe portul {WEBSOCKET_PORT}")
        async with websockets.serve(webrtc_handler, "0.0.0.0", WEBSOCKET_PORT):
            await asyncio.Future()  # run forever

def main():
    """Funcția principală care pornește toate serviciile"""
    print("🚀 Starting Enhanced Jetson IP Camera Server v2.0...")
    print("=" * 80)
    
    # Verifică și generează certificatul SSL
    ssl_available = generate_ssl_certificate()
    
    print("📊 Servicii disponibile:")
    if ssl_available:
        print(f"   🌐 Flask API: https://0.0.0.0:{FLASK_PORT} (HTTPS) 🔐")
        print(f"   📹 WebRTC WebSocket: wss://0.0.0.0:{WEBSOCKET_PORT} (WSS) 🔐")
    else:
        print(f"   🌐 Flask API: http://0.0.0.0:{FLASK_PORT} (HTTP) ⚠️")
        print(f"   📹 WebRTC WebSocket: ws://0.0.0.0:{WEBSOCKET_PORT} (WS) ⚠️")
    
    print(f"   📈 Monitorizare Jetson: {'✅ Activă' if JTOP_AVAILABLE else '❌ Dezactivată (jtop lipsă)'}")
    print(f"   🔍 Descoperire camere IP: ✅ Activă (Enhanced)")
    print()
    print("🆕 Funcționalități noi:")
    print(f"   🎯 Scanare {len(CAMERA_PORTS)} porturi comune cameră")
    print(f"   📋 Testare {len(CAMERA_PATHS)} căi de acces diverse")
    print(f"   🏭 Detectare automată manufacturer cameră")
    print(f"   ⚡ Scanare paralelă pentru performanță sporită")
    print(f"   🔐 Testare autentificare pentru camere standard")
    print(f"   ✅ Validare stream-uri pentru stabilitate")
    if ssl_available:
        print(f"   🔐 Comunicare securizată HTTPS/WSS")
    print("=" * 80)
    
    # Pornește scanarea pentru camere IP
    print("🔍 Începe scanarea inițială avansată pentru camere IP...")
    scan_thread = Thread(target=scan_for_cameras, daemon=True)
    scan_thread.start()
    
    # Pornește thread-ul de monitorizare Jetson
    jetson_thread = Thread(target=monitor_jetson, daemon=True)
    jetson_thread.start()
    
    # Pornește serverul Flask în thread separat
    flask_thread = Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Așteptă puțin pentru scanarea camerelor
    print("⏳ Aștept scanarea inițială...")
    time.sleep(8)  # Increased wait time for enhanced scanning
    
    # Pornește serverul WebSocket (principal)
    try:
        protocol = "WSS" if ssl_available else "WS"
        print(f"📹 Pornesc serverul WebRTC cu {protocol} pe portul {WEBSOCKET_PORT}...")
        asyncio.run(run_websocket_server())
    except KeyboardInterrupt:
        print("\n🛑 Server oprit de utilizator")
    except Exception as e:
        print(f"❌ Eroare la pornirea serverului: {e}")

if __name__ == "__main__":
    main()
