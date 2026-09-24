# 🚀 TerraCortex IoT Integration Guide

## Arsitektur Sistem

```
ESP32 (Wokwi Simulator)
    ├─ Baca Sensor Fisik (Pressure, Vibration, Temperature)
    ├─ Generate dynamic RPM & Bucket Angle
    └─ Publish JSON → MQTT Topic: "terracortex/telemetry"
         │
         ↓
Python AI Pipeline (run_ai_pipeline.py)
    ├─ Subscribe "terracortex/telemetry"
    ├─ Run ONNX Model Inference
    │   ├─ Workload Classifier
    │   └─ Hydraulic Autoencoder (Anomaly Detection)
    ├─ Generate cortex_inference object
    │   ├─ soil_strata
    │   ├─ is_anomaly (boolean)
    │   ├─ action_advisory (string)
    │   ├─ cmsi_score (0-100)
    │   └─ cavitation_hz (integer)
    └─ Publish JSON Lengkap → MQTT Topics:
        ├─ "terracortex/dashboard" (untuk Tablet Arifa & Dashboard Putra)
        └─ "terracortex/ai_results" (backward compatibility)
```

---

## 📋 Format JSON Contract

### Input dari ESP32 → Python AI

**Topic MQTT:** `terracortex/telemetry`

```json
{
  "excavator_id": "XCMG-EX-01",
  "timestamp": 125430,
  "sensors": {
    "hydraulic_pressure_bar": 348.0,
    "imu_vibration": 2.45,
    "oil_temperature_c": 72.5,
    "engine_rpm": 1850,
    "bucket_angle": 75
  }
}
```

### Output dari Python AI → Dashboard/Tablet

**Topic MQTT:** `terracortex/dashboard`

```json
{
  "timestamp": 125430,
  "sensors": {
    "hydraulic_pressure_bar": 348.0,
    "engine_rpm": 1850,
    "bucket_angle": 75
  },
  "cortex_inference": {
    "soil_strata": "HARD_ROCK",
    "is_anomaly": true,
    "action_advisory": "WARNING: Hydraulic anomaly detected! Reduce load & inspect system.",
    "cmsi_score": 94,
    "cavitation_hz": 142
  }
}
```

---

## 🎯 Untuk Tim Frontend (Arifa - Tablet In-Cab)

### Subscribe ke Topic:
```javascript
// Subscribe ke topic ini untuk mendapatkan data lengkap
mqtt.subscribe("terracortex/dashboard");
```

### Mapping Data ke UI Components:

1. **Gauge Tekanan Hidrolik**
   - Field: `sensors.hydraulic_pressure_bar`
   - Range: 120-350 bar
   - Zona merah: >= 285 bar

2. **RPM Gauge**
   - Field: `sensors.engine_rpm`
   - Range: 1100-1900 RPM
   - Animasi bar bergerak sesuai nilai

3. **Bucket Angle Indicator**
   - Field: `sensors.bucket_angle`
   - Range: 30-85 degrees
   - Jarum pointer bergerak

4. **Alarm Peringatan Overload**
   - Trigger: `cortex_inference.is_anomaly === true`
   - Display: Kotak merah dengan teks `action_advisory`
   - Jika `cmsi_score >= 94` DAN `hydraulic_pressure_bar > 280` → Play buzzer/sirine

5. **Advisory Message**
   - Display: `cortex_inference.action_advisory`
   - Color: Merah jika anomaly, hijau jika normal

6. **Soil Status**
   - Display: `cortex_inference.soil_strata`
   - Icon berbeda untuk "HARD_ROCK" vs "NORMAL_SOFT"

---

## 🖥️ Untuk Tim Dashboard (Putra - Komando Center)

### Subscribe ke Topic:
```python
# Python/Node.js backend
mqtt.subscribe("terracortex/dashboard")

# atau untuk backward compatibility
mqtt.subscribe("terracortex/ai_results")
```

### Data yang Tersedia:

1. **Real-time Telemetry**
   - `sensors.*` → Semua sensor readings
   - Update setiap ~2.5 detik

2. **AI Insights**
   - `cortex_inference.cmsi_score` → Critical Safety Index (0-100)
   - `cortex_inference.cavitation_hz` → Frekuensi kavitasi hidrolik
   - `cortex_inference.is_anomaly` → Boolean flag untuk dashboard alert

3. **Historical Logging**
   - Simpan semua JSON message untuk analytics
   - Graph trend `cmsi_score` over time
   - Alert history dari `action_advisory`

---

## 🔧 Cara Menjalankan Sistem

### 1. Start ESP32 Simulator (Wokwi)
```bash
# Buka Wokwi.com atau VS Code Wokwi Extension
# Upload file: src/main.cpp
# Klik "Start Simulation"
```

### 2. Start Python AI Pipeline
```bash
# Install dependencies
pip install numpy onnxruntime paho-mqtt

# Run AI pipeline
python run_ai_pipeline.py
```

Output yang diharapkan:
```
=== TERRACOTEX AI CORTEX PIPELINE ACTIVE ===
[INFO] Models workload_classifier & hydraulic_autoencoder successfully loaded!

Connecting to MQTT broker (test.mosquitto.org) on topic 'terracortex/telemetry'...
Successfully connected! Waiting for live Wokwi lever movements...

--- Receiving Live Data from: XCMG-EX-01 ---
Sensor -> Boom Pressure: 348.0 bar | Vibration: 2.45 G | Temp: 72.5 °C
 [AI CORTEX Decision Results]:
    - Soil Strata Status      : HARD_ROCK
    - CMSI Score              : 94
    - Cavitation Hz           : 142
    - Anomaly Status          : DANGEROUS (Anomaly)
    - Recommendation / Advice : WARNING: Hydraulic anomaly detected! Reduce load & inspect system.
--------------------------------------------------
-> [SUCCESS] Complete payload sent to 'terracortex/dashboard'!
```

---

## 🧪 Testing Scenarios

### Scenario 1: Normal Operation
- **Action:** Geser potentiometer ke posisi rendah (< 40%)
- **Expected:**
  - `hydraulic_pressure_bar`: 120-220 bar
  - `engine_rpm`: 1100-1300
  - `bucket_angle`: 30-45°
  - `is_anomaly`: false
  - `cmsi_score`: 25-65
  - `soil_strata`: "NORMAL_SOFT"

### Scenario 2: High Load / Anomaly
- **Action:** Geser potentiometer ke posisi tinggi (> 80%)
- **Expected:**
  - `hydraulic_pressure_bar`: 285-350 bar
  - `engine_rpm`: 1750-1900
  - `bucket_angle`: 70-85°
  - `is_anomaly`: true
  - `cmsi_score`: 91-96
  - `soil_strata`: "HARD_ROCK"
  - `action_advisory`: "WARNING: Hydraulic anomaly detected!..."

---

## 🐛 Troubleshooting

### Problem: AI Pipeline tidak menerima data
**Solution:**
1. Cek ESP32 sudah connect ke WiFi (Serial Monitor)
2. Pastikan MQTT broker `test.mosquitto.org` accessible
3. Verify topic name: `terracortex/telemetry`

### Problem: Dashboard tidak update
**Solution:**
1. Subscribe ke topic yang benar: `terracortex/dashboard`
2. Cek Python AI pipeline masih running
3. Test dengan MQTT client (mosquitto_sub):
   ```bash
   mosquitto_sub -h test.mosquitto.org -t "terracortex/dashboard" -v
   ```

### Problem: Nilai sensor tidak realistis
**Solution:**
1. Cek mapping di `main.cpp` line 87-89
2. Pastikan potentiometer range: 0-4095 → 120-350 bar
3. Restart Wokwi simulator

---

## 📞 Kontak Tim

- **Hardware/IoT (ESP32):** Echa
- **AI/ML (Python Pipeline):** Echa (dengan model dari tim AI)
- **Frontend (Tablet):** Arifa
- **Backend (Dashboard):** Putra

---

## 📝 Changelog

### v2.0 - Advanced AI Integration
- ✅ Implementasi ONNX model inference
- ✅ Dynamic RPM & bucket angle generation
- ✅ CMSI score & cavitation frequency
- ✅ Dual MQTT topic (dashboard + ai_results)
- ✅ Format JSON sesuai contract Arifa

### v1.0 - Basic Telemetry
- ✅ ESP32 sensor reading
- ✅ MQTT publish basic data
- ✅ OLED display local

---

**Last Updated:** 2026-09-23  
**System Status:** ✅ Production Ready
