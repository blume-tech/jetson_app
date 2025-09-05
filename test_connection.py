#!/usr/bin/env python3
"""
Test Script pentru Jetson IP Camera Server
Acest script poate fi folosit pentru a testa conexiunea și funcționalitatea serverului
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_connection(server_url="https://localhost:8080", verify_ssl=False):
    """
    Testează conexiunea cu serverul Jetson
    
    Args:
        server_url: URL-ul serverului (default: https://localhost:8080)
        verify_ssl: Verifică certificatul SSL (default: False pentru self-signed)
    """
    
    print("🧪 === TEST CONEXIUNE JETSON IP CAMERA SERVER ===")
    print(f"🌐 Server: {server_url}")
    print(f"🕐 Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    test_results = {
        "server_url": server_url,
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test 1: Ping simplu
    print("🏓 Test 1: Ping...")
    try:
        response = requests.get(f"{server_url}/ping", verify=verify_ssl, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ping OK - Server: {data.get('server', 'unknown')}")
            print(f"   📅 Server timestamp: {data.get('timestamp', 'N/A')}")
            test_results["tests"]["ping"] = {"status": "success", "data": data}
        else:
            print(f"❌ Ping failed - Status: {response.status_code}")
            test_results["tests"]["ping"] = {"status": "failed", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Ping error: {e}")
        test_results["tests"]["ping"] = {"status": "error", "error": str(e)}
    
    # Test 2: Status general
    print("\n📊 Test 2: Status general...")
    try:
        response = requests.get(f"{server_url}/status", verify=verify_ssl, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status OK")
            print(f"   🔧 Service: {data.get('service_status', 'unknown')}")
            print(f"   📝 Version: {data.get('version', 'unknown')}")
            print(f"   ⏱️ Uptime: {data.get('uptime_seconds', 0):.1f} secunde")
            print(f"   🔐 SSL: {'✅ Enabled' if data.get('ssl_enabled') else '❌ Disabled'}")
            print(f"   📹 Camere: {data.get('cameras_discovered', 0)}")
            print(f"   📊 Jetson monitoring: {'✅' if data.get('jtop_available') else '❌'}")
            test_results["tests"]["status"] = {"status": "success", "data": data}
        else:
            print(f"❌ Status failed - HTTP {response.status_code}")
            test_results["tests"]["status"] = {"status": "failed", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Status error: {e}")
        test_results["tests"]["status"] = {"status": "error", "error": str(e)}
    
    # Test 3: Test conexiune complet
    print("\n🔍 Test 3: Test conexiune complet...")
    try:
        response = requests.get(f"{server_url}/test-connection", verify=verify_ssl, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test conexiune complet")
            print(f"   🎯 Overall status: {data.get('overall_status', 'unknown')}")
            print(f"   💬 Message: {data.get('message', 'N/A')}")
            
            # Detalii teste
            test_details = data.get('test_details', {})
            
            # Server status
            server_status = test_details.get('server_status', {})
            if server_status:
                print(f"   🖥️ Server uptime: {server_status.get('uptime_seconds', 0):.1f}s")
                print(f"   🔌 Ports: Flask={server_status.get('flask_port')}, WebRTC={server_status.get('websocket_port')}")
            
            # Performance
            performance = test_details.get('performance', {})
            if performance:
                print(f"   ⚡ CPU usage: {performance.get('cpu_usage_percent', 0):.1f}%")
            
            memory = test_details.get('memory', {})
            if memory:
                print(f"   💾 RAM usage: {memory.get('ram_usage_percent', 0):.1f}%")
            
            # Camere
            cameras = test_details.get('camera_discovery', {})
            if cameras:
                print(f"   📹 Camere găsite: {cameras.get('cameras_found', 0)}")
                for cam in cameras.get('cameras', []):
                    print(f"      - {cam.get('manufacturer', 'unknown')}: {cam.get('ip', 'N/A')} ({cam.get('type', 'N/A')})")
            
            # Issues
            issues = data.get('issues', [])
            if issues:
                print(f"   ⚠️ Issues: {', '.join(issues)}")
            
            test_results["tests"]["full_connection"] = {"status": "success", "data": data}
        else:
            print(f"❌ Test conexiune failed - HTTP {response.status_code}")
            test_results["tests"]["full_connection"] = {"status": "failed", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ Test conexiune error: {e}")
        test_results["tests"]["full_connection"] = {"status": "error", "error": str(e)}
    
    # Test 4: System info
    print("\n🖥️ Test 4: System info...")
    try:
        response = requests.get(f"{server_url}/system-info", verify=verify_ssl, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System info OK")
            
            platform_info = data.get('platform', {})
            if platform_info:
                print(f"   🖥️ OS: {platform_info.get('system', 'unknown')} {platform_info.get('release', '')}")
                print(f"   🏗️ Architecture: {platform_info.get('machine', 'unknown')}")
                print(f"   🎯 Jetson: {'✅' if data.get('is_jetson') else '❌'}")
            
            python_info = data.get('python', {})
            if python_info:
                print(f"   🐍 Python: {python_info.get('version', 'unknown')}")
            
            resources = data.get('resources', {})
            if resources:
                print(f"   📊 Resources: CPU={resources.get('cpu_percent', 0):.1f}%, RAM={resources.get('memory_percent', 0):.1f}%")
            
            test_results["tests"]["system_info"] = {"status": "success", "data": data}
        else:
            print(f"❌ System info failed - HTTP {response.status_code}")
            test_results["tests"]["system_info"] = {"status": "failed", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ System info error: {e}")
        test_results["tests"]["system_info"] = {"status": "error", "error": str(e)}
    
    # Sumar final
    print("\n" + "=" * 60)
    print("📋 SUMAR TESTE:")
    
    total_tests = len(test_results["tests"])
    successful_tests = sum(1 for test in test_results["tests"].values() if test["status"] == "success")
    
    print(f"✅ Teste reușite: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 TOATE TESTELE AU REUȘIT! Serverul Jetson funcționează perfect!")
        result_code = 0
    elif successful_tests >= total_tests * 0.75:
        print("⚠️ Majoritatea testelor au reușit. Serverul funcționează dar are probleme minore.")
        result_code = 1
    else:
        print("❌ Multe teste au eșuat. Serverul are probleme serioase.")
        result_code = 2
    
    # Salvează rezultatele
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jetson_test_results_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(test_results, f, indent=2)
        print(f"📁 Rezultate salvate în: {filename}")
    except Exception as e:
        print(f"⚠️ Nu s-au putut salva rezultatele: {e}")
    
    return result_code

def main():
    """Funcția principală"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test conexiune Jetson IP Camera Server')
    parser.add_argument('--url', default='https://localhost:8080', 
                       help='URL server (default: https://localhost:8080)')
    parser.add_argument('--http', action='store_true', 
                       help='Folosește HTTP în loc de HTTPS')
    parser.add_argument('--verify-ssl', action='store_true', 
                       help='Verifică certificatul SSL')
    
    args = parser.parse_args()
    
    # Construiește URL-ul
    if args.http:
        server_url = args.url.replace('https://', 'http://')
    else:
        server_url = args.url
    
    # Rulează testele
    try:
        result_code = test_connection(server_url, args.verify_ssl)
        sys.exit(result_code)
    except KeyboardInterrupt:
        print("\n🛑 Test întrerupt de utilizator")
        sys.exit(3)
    except Exception as e:
        print(f"\n❌ Eroare fatală: {e}")
        sys.exit(4)

if __name__ == "__main__":
    main()
