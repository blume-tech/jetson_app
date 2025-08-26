#!/usr/bin/env python3
"""
Jetson Server - Monitorizare sistem și streaming video WebRTC
Autor: Claude AI Assistant
Data: 2025-08-26

Funcționalități:
- Monitorizare Jetson (CPU, GPU, memorie, temperaturi, power) via jtop
- Streaming video WebRTC de la multiple camere USB
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
from datetime import datetime
from threading import Thread, Lock

# Flask imports
from flask import Flask, jsonify, Response
from flask_cors import CORS

# WebRTC imports
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
import websockets

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
CORS(app)

# Monitorizare Jetson
latest_data = {}
data_history = []
data_lock = Lock()
MAX_HISTORY_SECONDS = 600  # 10 minute

# WebRTC configurare
WEBSOCKET_PORT = 8081
FLASK_PORT = 8080
VIDEO_DEVICES = ["/dev/video0", "/dev/video1"]  # Camerele USB

# =============================================================================
# CLASA PENTRU VIDEO STREAMING
# =============================================================================

class USBVideoTrack(MediaStreamTrack):
    """Track pentru streaming video de la camerele USB"""
    kind = "video"
    
    def __init__(self, device_path):
        super().__init__()
        # Pentru USB cameras folosim device index (0, 1, 2, etc.) sau path-ul
        if device_path.startswith("/dev/video"):
            # Extrage numărul din /dev/videoX
            device_index = int(device_path.split("video")[1])
        else:
            device_index = int(device_path)
            
        self.cap = cv2.VideoCapture(device_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Nu s-a putut deschide camera USB: {device_path}")
        
        # Setează rezoluția și frame rate pentru performanță mai bună
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"📹 Camera USB inițializată: {device_path}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        # Citește frame-ul în mod asincron
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self.cap.read)
        
        if not ret:
            print("⚠️ Nu s-a putut citi frame din camera USB")
            await asyncio.sleep(0.033)  # ~30fps
            return await self.recv()
        
        # Convertește frame-ul pentru WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame

    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

# =============================================================================
# FUNCȚII PENTRU MONITORIZAREA JETSON
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
            "gpu_detailed": {},  # Detailed GPU metrics
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
                "cpu": {"CPU0_usage": 25.5, "CPU1_usage": 30.2},
                "temperatures": {"CPU-therm": 45.2, "GPU-therm": 42.1},
                "gpu": {"GPU_usage": 15.3},
                "memory": {"RAM_used": 2048, "RAM_total": 8192},
                "power": {"total_power": 12.5}
            }
            
            with data_lock:
                latest_data = mock_data
                data_history.append(flatten_data(mock_data))
                if len(data_history) > MAX_HISTORY_SECONDS:
                    data_history = data_history[-MAX_HISTORY_SECONDS:]
            
            time.sleep(1)
        return
    
    try:
        with jtop(interval=1.0) as jetson:
            print("✅ Conexiune stabilită cu jtop")
            while jetson.ok():
                data = extract_full(jetson)
                flat = flatten_data(data)
                
                with data_lock:
                    latest_data = data
                    data_history.append(flat)
                    
                    # Păstrăm doar ultimele 10 minute de date
                    if len(data_history) > MAX_HISTORY_SECONDS:
                        data_history = data_history[-MAX_HISTORY_SECONDS:]
                
                time.sleep(1)
                
    except Exception as e:
        print(f"❌ Eroare în monitor_jetson: {e}")

# =============================================================================
# WEBSOCKET HANDLER PENTRU WEBRTC
# =============================================================================

async def webrtc_handler(websocket):
    """Handler pentru conexiunile WebRTC"""
    print("📹 Client WebRTC conectat")
    pc = RTCPeerConnection()
    
    try:
        # Creează track-uri pentru camerele USB
        video_tracks = []
        for device in VIDEO_DEVICES:
            try:
                video_track = USBVideoTrack(device)
                pc.addTrack(video_track)
                video_tracks.append(video_track)
                print(f"📹 Adăugat track pentru {device}")
            except Exception as e:
                print(f"⚠️ Nu s-a putut inițializa camera {device}: {e}")
        
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
# FLASK ROUTES PENTRU API
# =============================================================================

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Returnează ultimele metrici disponibile"""
    with data_lock:
        if not latest_data:
            return jsonify({"error": "Nu sunt date disponibile"}), 404
        return jsonify(latest_data)

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
                headers={"Content-Disposition": "attachment; filename=jetson_complete_logs.csv"}
            )
        except Exception as e:
            return Response(f"Eroare la generarea CSV: {str(e)}", status=500)

@app.route("/status", methods=["GET"])
def get_status():
    """Returnează statusul serviciului"""
    with data_lock:
        return jsonify({
            "service_status": "running",
            "jtop_available": JTOP_AVAILABLE,
            "data_points_collected": len(data_history),
            "last_update": latest_data.get("timestamp", "N/A") if latest_data else "N/A",
            "webrtc_port": WEBSOCKET_PORT,
            "flask_port": FLASK_PORT,
            "video_devices": VIDEO_DEVICES,
            "features": {
                "jetson_monitoring": JTOP_AVAILABLE,
                "webrtc_streaming": True,
                "csv_export": True
            }
        })

@app.route("/", methods=["GET"])
def get_info():
    """Informații despre server"""
    return jsonify({
        "name": "Jetson Server",
        "version": "1.0.0",
        "description": "Server pentru monitorizarea Jetson și streaming video WebRTC",
        "endpoints": {
            "metrics": "/metrics - GET - Ultimele metrici Jetson",
            "status": "/status - GET - Status server",
            "download_logs": "/download_logs - GET - Descarcă CSV cu istoricul",
            "webrtc": f"ws://localhost:{WEBSOCKET_PORT} - WebSocket pentru WebRTC"
        }
    })

# =============================================================================
# FUNCȚII PENTRU PORNIREA SERVERELOR
# =============================================================================

def run_flask_server():
    """Rulează serverul Flask în thread separat"""
    print(f"🌐 Starting Flask server on port {FLASK_PORT}")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)

async def run_websocket_server():
    """Rulează serverul WebSocket pentru WebRTC"""
    print(f"📹 Starting WebSocket server on port {WEBSOCKET_PORT}")
    async with websockets.serve(webrtc_handler, "0.0.0.0", WEBSOCKET_PORT):
        await asyncio.Future()  # run forever

def main():
    """Funcția principală care pornește toate serviciile"""
    print("🚀 Starting Jetson Server...")
    print("=" * 60)
    print("📊 Servicii disponibile:")
    print(f"   🌐 Flask API: http://0.0.0.0:{FLASK_PORT}")
    print(f"   📹 WebRTC WebSocket: ws://0.0.0.0:{WEBSOCKET_PORT}")
    print(f"   📈 Monitorizare Jetson: {'✅ Activă' if JTOP_AVAILABLE else '❌ Dezactivată (jtop lipsă)'}")
    print("=" * 60)
    
    # Pornește thread-ul de monitorizare Jetson
    jetson_thread = Thread(target=monitor_jetson, daemon=True)
    jetson_thread.start()
    
    # Pornește serverul Flask în thread separat
    flask_thread = Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Pornește serverul WebSocket (principal)
    try:
        asyncio.run(run_websocket_server())
    except KeyboardInterrupt:
        print("\n🛑 Server oprit de utilizator")
    except Exception as e:
        print(f"❌ Eroare la pornirea serverului: {e}")

if __name__ == "__main__":
    main()
