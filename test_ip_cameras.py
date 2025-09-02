#!/usr/bin/env python3
"""
Test script pentru descoperirea camerelor IP
Testează funcționalitatea de scanare a rețelei pentru camere IP
"""

import time
from server_ip_camera import scan_for_cameras, discovered_cameras

def test_camera_discovery():
    """Testează descoperirea camerelor IP"""
    print("🧪 Test: Descoperire camere IP")
    print("=" * 50)
    
    # Rulează scanarea
    print("🔍 Începe scanarea...")
    start_time = time.time()
    
    cameras = scan_for_cameras()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"⏱️ Scanare completă în {duration:.2f} secunde")
    print(f"📹 Găsite {len(cameras)} camere IP:")
    
    for i, camera in enumerate(cameras, 1):
        print(f"   {i}. {camera['url']}")
        print(f"      Type: {camera['type']}")
        print(f"      IP: {camera['ip']}:{camera['port']}")
        print(f"      Path: {camera['path']}")
        print()
    
    return cameras

if __name__ == "__main__":
    test_camera_discovery()
