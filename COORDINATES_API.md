# 📍 API COORDONATE CAMERE - DOCUMENTAȚIE

## Funcționalitate

Serverul primește și salvează **4 coordonate** pentru fiecare cameră (Camera 1 și Camera 2). Coordonatele reprezintă 4 puncte din imagine și sunt salvate în fișiere separate.

## 📡 Endpoint-uri

### 1. POST /camera1/coordinates
**Salvează coordonatele pentru Camera 1**

**Request:**
```json
{
    "coordinates": [
        [x1, y1],
        [x2, y2], 
        [x3, y3],
        [x4, y4]
    ],
    "metadata": {
        "image_info": "opțional",
        "user_id": "opțional",
        "timestamp_web": "opțional"
    }
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "Coordonate salvate pentru Camera 1",
    "data": {
        "camera": "Camera 1",
        "coordinates": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
        "points_count": 4,
        "timestamp": "2025-09-05 14:30:25",
        "file": "camera1_coordinates.txt"
    }
}
```

### 2. POST /camera2/coordinates
**Salvează coordonatele pentru Camera 2**

**Request:** (același format ca Camera 1)
**Response:** (același format, dar pentru Camera 2)

### 3. GET /coordinates/history
**Returnează istoricul coordonatelor de la ambele camere**

**Response:**
```json
{
    "success": true,
    "data": {
        "camera1": [
            {
                "timestamp": "2025-09-05 14:30:25",
                "camera": "Camera 1", 
                "coordinates": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
                "metadata": {}
            }
        ],
        "camera2": [
            {
                "timestamp": "2025-09-05 14:25:10",
                "camera": "Camera 2",
                "coordinates": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]], 
                "metadata": {}
            }
        ]
    },
    "stats": {
        "camera1_total": 5,
        "camera2_total": 3,
        "total_coordinates": 8
    }
}
```

### 4. POST /coordinates/clear
**Șterge coordonatele salvate**

**Request:**
```json
{
    "camera": "all"  // "camera1", "camera2", sau "all"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Coordonate șterse pentru all",
    "files_cleared": ["camera1_coordinates.txt", "camera2_coordinates.txt"]
}
```

## 💾 Format Salvare

### Fișiere generate:
- `camera1_coordinates.txt` - Coordonate Camera 1
- `camera2_coordinates.txt` - Coordonate Camera 2

### Format în fișier (o linie per set de coordonate):
```json
{"timestamp": "2025-09-05 14:30:25", "camera": "Camera 1", "coordinates": [[150, 200], [300, 200], [300, 400], [150, 400]], "metadata": {}}
```

## 📝 Exemple de utilizare

### JavaScript - Trimitere coordonate Camera 1
```javascript
const JETSON_URL = 'https://YOUR_JETSON_IP:8080';

async function sendCamera1Coordinates(points) {
    try {
        const response = await fetch(`${JETSON_URL}/camera1/coordinates`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                coordinates: points,  // [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                metadata: {
                    user_id: "user123",
                    image_info: "detection_area"
                }
            })
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Coordonate Camera 1 salvate:', result.data);
        } else {
            console.error('Eroare:', result.error);
        }
    } catch (error) {
        console.error('Eroare conexiune:', error);
    }
}

// Exemplu de utilizare
const coordonate = [
    [100, 150],  // punct 1: top-left
    [400, 150],  // punct 2: top-right  
    [400, 350],  // punct 3: bottom-right
    [100, 350]   // punct 4: bottom-left
];

sendCamera1Coordinates(coordonate);
```

### cURL - Test endpoint
```bash
# Testare Camera 1
curl -k -X POST https://YOUR_JETSON_IP:8080/camera1/coordinates \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [[100, 150], [400, 150], [400, 350], [100, 350]],
    "metadata": {"test": true}
  }'

# Testare Camera 2  
curl -k -X POST https://YOUR_JETSON_IP:8080/camera2/coordinates \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [[50, 100], [300, 100], [300, 250], [50, 250]],
    "metadata": {"user": "test_user"}
  }'

# Verificare istoric
curl -k https://YOUR_JETSON_IP:8080/coordinates/history
```

## ⚠️ Validări

1. **Numărul punctelor:** Exact 4 puncte pentru fiecare cameră
2. **Format puncte:** Fiecare punct trebuie să fie `[x, y]`
3. **Tipul coordonatelor:** `x` și `y` trebuie să fie numere (int sau float)
4. **Request format:** JSON valid cu cheia `coordinates`

## 🔍 Debugging

### Verificare fișiere generate:
```bash
# Pe Jetson
ls -la camera*.txt
cat camera1_coordinates.txt
cat camera2_coordinates.txt
```

### Verificare logs server:
```bash
# Coordonatele sunt afișate în consolă
# Format: "📍 Camera X - Coordonate salvate: [[x1,y1],...] la timestamp"
```

## 🎯 Cazuri de utilizare

1. **Detectare zone:** Definirea zonelor de interes în imaginile camerelor
2. **Tracking obiecte:** Salvarea coordonatelor obiectelor detectate
3. **Calibrare:** Puncte de referință pentru calibrarea camerelor
4. **ROI (Region of Interest):** Definirea zonelor pentru procesare
5. **Geometrie:** Forme geometrice în spațiul camerei

## 📊 Statistici

Endpoint-ul `/coordinates/history` oferă statistici:
- Numărul total de seturi de coordonate per cameră
- Numărul total general
- Coordonatele sunt sortate descrescător după timestamp (cele mai recente primul)

Serverul este gata să primească și să salveze coordonatele de la site-ul tău web! 🚀
