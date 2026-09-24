# 🚜 TerraCortex IoT - Smart Excavator Monitoring System

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Version](https://img.shields.io/badge/Version-2.0-blue)
![Architecture](https://img.shields.io/badge/Architecture-IoT%20%2B%20AI-orange)

**TerraCortex** adalah sistem monitoring cerdas untuk excavator yang mengintegrasikan IoT sensors, AI inference, dan real-time dashboard untuk meningkatkan safety dan efisiensi operasional.

---

## 📋 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    TERRACORTEX ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ESP32 Hardware           Python AI Pipeline        Frontends  │
│  ┌──────────────┐        ┌────────────────┐      ┌──────────┐ │
│  │ Sensors:     │        │ ONNX Models:   │      │ Tablet   │ │
│  │ - Pressure   │──MQTT──│ - Classifier   │─MQTT─│ (Arifa)  │ │
│  │ - Vibration  │        │ - Autoencoder  │      │          │ │
│  │ - Temp       │        │                │      │ Dashboard│ │
│  │ - RPM        │        │ AI Inference   │──────│ (Putra)  │ │
│  │ - Bucket     │        │ & Analytics    │      │          │ │
│  └──────────────┘        └────────────────┘      └──────────┘ │
│                                                                 │
│  Topic: terracortex/telemetry → terracortex/dashboard          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Features

### ✅ Real-time Sensor Monitoring
- **Hydraulic Pressure** (120-350 bar)
- **Engine RPM** (1100-1900)
- **Bucket Angle** (30-85 degrees)
- **IMU Vibration** (G-force)
- **Oil Temperature** (°C)

### ✅ AI-Powered Inference
- **Anomaly Detection** (ONNX Autoencoder)
- **Workload Classification** (ONNX Classifier)
- **CMSI Score** (Critical Machine Safety Index 0-100)
- **Cavitation Detection** (Frequency Hz)
- **Soil Strata Analysis** (HARD_ROCK / NORMAL_SOFT)

### ✅ Smart Alerts & Advisory
- Real-time overload warnings
- Temperature monitoring
- Advisory messages untuk operator
- Automated buzzer/alarm triggers

---

## 📁 Project Structure

```
TerraCortex-IoT/
├── src/
│   └── main.cpp                 # ESP32 firmware (Arduino)
├── weights/
│   ├── workload_classifier.onnx # AI model - workload
│   └── hydraulic_autoencoder.onnx # AI model - anomaly
├── run_ai_pipeline.py          # Python AI inference pipeline
├── test_json_format.py         # JSON format validation test
├── INTEGRATION_GUIDE.md        # Detailed integration guide
├── MESSAGE_TO_TEAM.md          # Copy-paste messages untuk tim
├── platformio.ini              # PlatformIO configuration
├── diagram.json                # Wokwi circuit diagram
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Setup ESP32 Hardware (Wokwi Simulator)

```bash
# Open Wokwi Simulator atau VS Code dengan Wokwi Extension
# File: src/main.cpp
# Circuit: diagram.json

# Start Simulation → ESP32 akan connect ke WiFi dan publish data
```

### 2. Setup Python AI Pipeline

```bash
# Install dependencies
pip install numpy onnxruntime paho-mqtt

# Run AI pipeline
python run_ai_pipeline.py
```

Expected output:
```
=== TERRACOTEX AI CORTEX PIPELINE ACTIVE ===
[INFO] Models successfully loaded!
Connecting to MQTT broker...
Successfully connected! Waiting for live data...
```

### 3. Test & Validate

```bash
# Run validation test
python test_json_format.py

# Monitor MQTT messages
mosquitto_sub -h test.mosquitto.org -t "terracortex/dashboard" -v
```

---

## 📊 JSON Format Contract

### Input: ESP32 → AI Pipeline
**Topic:** `terracortex/telemetry`

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

### Output: AI Pipeline → Dashboard/Tablet
**Topic:** `terracortex/dashboard`

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

## 🎮 Usage for Frontend Teams

### For Arifa (Tablet In-Cab UI)

```javascript
// Subscribe ke dashboard data
mqtt.subscribe("terracortex/dashboard");

mqtt.on('message', (topic, message) => {
  const data = JSON.parse(message);
  
  // Update UI components
  updatePressureGauge(data.sensors.hydraulic_pressure_bar);
  updateRPMBar(data.sensors.engine_rpm);
  updateBucketAngle(data.sensors.bucket_angle);
  
  // Trigger alarms
  if (data.cortex_inference.is_anomaly) {
    showRedWarningBox(data.cortex_inference.action_advisory);
  }
  
  if (data.cortex_inference.cmsi_score >= 94 && 
      data.sensors.hydraulic_pressure_bar > 280) {
    playAlarmBuzzer();
  }
});
```

### For Putra (Dashboard Backend)

```python
# Subscribe dan store data
mqtt.subscribe("terracortex/dashboard")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    
    # Store to database
    db.insert({
        'timestamp': data['timestamp'],
        'pressure': data['sensors']['hydraulic_pressure_bar'],
        'cmsi_score': data['cortex_inference']['cmsi_score'],
        'is_anomaly': data['cortex_inference']['is_anomaly']
    })
    
    # Real-time graph update
    dashboard.update_chart(data)
```

---

## 🧪 Testing Scenarios

### Scenario 1: Normal Operation
- Potentiometer: **Low** (< 40%)
- Expected:
  - Pressure: 120-220 bar
  - RPM: 1100-1300
  - `is_anomaly`: false
  - `cmsi_score`: 25-65

### Scenario 2: High Load / Anomaly
- Potentiometer: **High** (> 80%)
- Expected:
  - Pressure: 285-350 bar
  - RPM: 1750-1900
  - `is_anomaly`: true
  - `cmsi_score`: 91-96
  - Red warning box triggered
  - Alarm buzzer triggered

---

## 📚 Documentation

- **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - Detailed integration guide
- **[MESSAGE_TO_TEAM.md](./MESSAGE_TO_TEAM.md)** - Copy-paste messages untuk tim
- **[test_json_format.py](./test_json_format.py)** - Validation test script

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Hardware | ESP32 DevKit C V4 |
| Sensors | Potentiometer, MPU6050, NTC Temp |
| Firmware | Arduino C++ (PlatformIO) |
| Communication | MQTT (test.mosquitto.org) |
| AI/ML | ONNX Runtime (Python) |
| Models | Workload Classifier + Autoencoder |
| Frontend | JavaScript/React (Arifa) |
| Backend | Python/Node.js (Putra) |

---

## 👥 Team

- **Hardware/IoT Engineer:** Echa (@Echa)
- **AI/ML Engineer:** Echa + AI Team
- **Frontend Developer (Tablet):** Arifa (@Arifa)
- **Backend Developer (Dashboard):** Putra (@Putra)

---

## 📝 Changelog

### v2.0 - Advanced AI Integration (2026-09-23)
- ✅ Pilihan 2: ESP32 + Python AI Pipeline architecture
- ✅ ONNX model inference (Classifier + Autoencoder)
- ✅ Dynamic RPM & bucket angle generation
- ✅ CMSI score & cavitation frequency
- ✅ Dual MQTT topics (telemetry + dashboard)
- ✅ Complete JSON format contract
- ✅ Validation test suite
- ✅ Comprehensive documentation

### v1.0 - Basic Telemetry (2026-09-20)
- ✅ ESP32 sensor reading
- ✅ MQTT publish basic data
- ✅ OLED display local

---

## 🎯 Next Steps

- [ ] Integration testing dengan Tablet Arifa
- [ ] Integration testing dengan Dashboard Putra
- [ ] Load testing MQTT broker
- [ ] Deploy to production hardware
- [ ] Setup monitoring & logging

---

## 📞 Support

Untuk pertanyaan atau issues:
1. Check [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) terlebih dahulu
2. Run validation test: `python test_json_format.py`
3. Contact tim development

---

## 📄 License

© 2026 TerraCortex Team. All rights reserved.

---

**Status:** ✅ Production Ready  
**Last Updated:** 2026-09-23  
**Version:** 2.0.0
