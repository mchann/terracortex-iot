# 📨 Pesan untuk Tim (Copy-Paste Ready)

---

## Untuk Arifa (Frontend - Tablet In-Cab)

**Subject:** Update Format JSON untuk Tablet TerraCortex - Semua Fitur Sudah Ready! 🚀

Halo Rifa! 

Good news, sistem backend ESP32 + AI pipeline-nya udah selesai dan siap integrasi dengan tablet-mu! Semua field yang kamu butuhin untuk **RPM gauge, bucket angle, alarm overload, dan advisory message** udah tersedia.

### **MQTT Topic yang Harus Kamu Subscribe:**
```javascript
mqtt.subscribe("terracortex/dashboard");
```

### **Format JSON yang Akan Kamu Terima:**

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

### **Mapping ke UI Components Tablet-mu:**

✅ **Gauge Tekanan Hidrolik:**
- Field: `sensors.hydraulic_pressure_bar`
- Range: 120-350 bar
- Zona merah trigger: >= 285 bar

✅ **RPM Bar Gauge (Yang kamu tanya!):**
- Field: `sensors.engine_rpm`
- Range: 1100-1900 RPM
- Sekarang udah **dynamic** berdasarkan load, bukan random lagi!

✅ **Bucket Angle Pointer (Jarum Target):**
- Field: `sensors.bucket_angle`
- Range: 30-85 degrees
- Bergerak sesuai pressure hidrolik

✅ **Kotak Peringatan Overload Merah:**
- Trigger: `cortex_inference.is_anomaly === true`
- Tampilkan text: `cortex_inference.action_advisory`

✅ **Alarm Buzzer/Sirine:**
- Kondisi: `cortex_inference.cmsi_score >= 94` **DAN** `sensors.hydraulic_pressure_bar > 280`
- Play sound effect danger

✅ **Status Tanah:**
- Display: `cortex_inference.soil_strata`
- Nilai: "HARD_ROCK" atau "NORMAL_SOFT"

### **Testing:**
Begitu sistem ESP32 + Python AI jalan, semua data akan otomatis stream ke topic `terracortex/dashboard` setiap ~2.5 detik. Tinggal subscribe dan map ke component UI-mu!

File dokumentasi lengkap ada di: **INTEGRATION_GUIDE.md**

Ada yang perlu disesuaikan lagi dari sisi format JSON-nya? Kabari yaa! 😊

---

## Untuk Putra (Backend - Dashboard Komando)

**Subject:** Update Integrasi AI Pipeline - Format JSON Baru untuk Dashboard 🖥️

Halo Put!

Sistem AI pipeline-nya udah di-update sesuai diskusi kemarin. Sekarang ESP32 kirim data sensor mentah, terus Python AI yang proses dan kirim hasil lengkap ke dashboard-mu.

### **Arsitektur Update:**

```
ESP32 → MQTT "terracortex/telemetry" → Python AI Pipeline
                                              ↓
                          MQTT "terracortex/dashboard" → Dashboard Kamu
```

### **MQTT Topic untuk Dashboard Kamu:**
```python
mqtt.subscribe("terracortex/dashboard")  # Topic baru, data lengkap AI inference
mqtt.subscribe("terracortex/ai_results") # Backup, backward compatibility
```

### **Format JSON yang Dashboard Kamu Terima:**

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

### **Field Baru untuk Dashboard Analytics:**

✅ **CMSI Score (Critical Machine Safety Index):**
- Field: `cortex_inference.cmsi_score`
- Range: 0-100
- Zona bahaya: >= 91
- Bisa untuk graph trend over time

✅ **Cavitation Frequency:**
- Field: `cortex_inference.cavitation_hz`
- Unit: Hertz
- Indikator kesehatan sistem hidrolik

✅ **Real-time Anomaly Flag:**
- Field: `cortex_inference.is_anomaly`
- Type: Boolean
- Untuk trigger alert di dashboard

✅ **Dynamic Engine RPM & Bucket Angle:**
- Fields: `sensors.engine_rpm`, `sensors.bucket_angle`
- Sekarang udah korelasi dengan pressure, bukan random

### **Update Python AI Pipeline:**
File `run_ai_pipeline.py` udah di-update dengan:
- ONNX model inference (workload classifier + autoencoder)
- CMSI score calculation
- Cavitation frequency detection
- Dual publish: `terracortex/dashboard` + `terracortex/ai_results`

### **Cara Test:**
1. Jalanin Python AI: `python run_ai_pipeline.py`
2. Start ESP32 simulator
3. Monitor topic dengan:
   ```bash
   mosquitto_sub -h test.mosquitto.org -t "terracortex/dashboard" -v
   ```

Dashboard-mu tinggal subscribe ke topic `terracortex/dashboard` dan semua data real-time + AI inference langsung masuk!

Dokumentasi lengkap di: **INTEGRATION_GUIDE.md**

Kalau ada yang perlu disesuaikan lagi, langsung chat aja Put! 🚀

---

## Summary Changes untuk Semua Tim

### ✅ Yang Sudah Dikerjakan:

1. **ESP32 (main.cpp):**
   - Update pressure mapping: 120-350 bar
   - Dynamic RPM generation: 1100-1900 based on load
   - Dynamic bucket angle: 30-85 degrees
   - Improved JSON structure dengan object "sensors"

2. **Python AI Pipeline (run_ai_pipeline.py):**
   - Tambah field `cmsi_score` (Critical Machine Safety Index)
   - Tambah field `cavitation_hz` (Cavitation frequency)
   - Simplified `soil_strata` format: "HARD_ROCK" atau "NORMAL_SOFT"
   - Generate `cortex_inference` object lengkap
   - Dual publish: `terracortex/dashboard` + `terracortex/ai_results`

3. **Dokumentasi:**
   - INTEGRATION_GUIDE.md → Panduan lengkap untuk semua tim
   - Format JSON contract yang jelas
   - Testing scenarios
   - Troubleshooting guide

### 🎯 Next Steps:

**Untuk Arifa:**
- Subscribe tablet ke `terracortex/dashboard`
- Map JSON fields ke UI components
- Test alarm trigger dengan `is_anomaly`

**Untuk Putra:**
- Subscribe dashboard ke `terracortex/dashboard`
- Integrate real-time telemetry display
- Setup historical logging & analytics

**Untuk Testing Bersama:**
- Koordinasi waktu untuk integration test
- Validate semua UI components menyala dengan benar
- Ensure MQTT broker stability

---

**Dokumentasi Lengkap:** `INTEGRATION_GUIDE.md`  
**Contact Person:** Echa (Hardware/IoT + AI Pipeline)  
**Status:** ✅ Ready for Integration Testing

Kalau ada pertanyaan atau butuh adjustment, langsung chat yaa! 🚀
