import os
import time
import random
import json
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

print("=== TERRACOTEX INTEGRATED SIMULATOR & AI CORTEX ===")

# --- 1. KONFIGURASI MQTT ---
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_TOPIC = "terracortex/telemetry"

mqtt_client = mqtt.Client(client_id="terracortex_python_simulator")
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
    print(f"[INFO] Berhasil terhubung ke MQTT Broker: {MQTT_BROKER}")
except Exception as e:
    print(f"[ERROR] Gagal terhubung ke broker MQTT: {e}")

# --- 2. LOAD MODEL ONNX ---
try:
    classifier_session = ort.InferenceSession("weights/workload_classifier.onnx")
    autoencoder_session = ort.InferenceSession("weights/hydraulic_autoencoder.onnx")
    print("[INFO] Model ONNX (Classifier & Autoencoder) berhasil dimuat!\n" + "="*50)
except Exception as e:
    print(f"[ERROR] Gagal memuat model ONNX: {e}")
    exit()

try:
    while True:
        # Simulasi pembacaan sensor mentah
        im_vibration = round(random.uniform(0.5, 3.5), 2)
        pressure = round(random.uniform(120.0, 290.0), 1)
        temp = round(random.uniform(65.0, 85.0), 1)
        
        # --- 3. EKSEKUSI MODEL AI (ONNX) ---
        try:
            # Input untuk Workload Classifier (5 Fitur, 200 Timesteps)
            cls_input = np.random.randn(1, 5, 200).astype(np.float32)
            cls_input[0, 0, -1] = pressure
            cls_input[0, 1, -1] = im_vibration
            cls_input[0, 2, -1] = temp
            
            cls_name = classifier_session.get_inputs()[0].name
            class_outputs = classifier_session.run(None, {cls_name: cls_input})
            
            strata_logits = class_outputs[0]
            severity_score = float(class_outputs[1][0]) if len(class_outputs) > 1 else 0.0

            # Input untuk Hydraulic Autoencoder (4 Fitur, 200 Timesteps)
            ae_input = np.random.randn(1, 4, 200).astype(np.float32)
            ae_input[0, 0, -1] = pressure
            ae_input[0, 1, -1] = 150.0  # arm pressure dummy
            ae_input[0, 2, -1] = im_vibration
            ae_input[0, 3, -1] = temp
            
            ae_name = autoencoder_session.get_inputs()[0].name
            ae_outputs = autoencoder_session.run(None, {ae_name: ae_input})
            
            # Ambil output anomali dari index ke-2 dan ke-3 sesuai arahan Putra
            is_anomaly = bool(ae_outputs[2][0]) if len(ae_outputs) > 2 else False
            anomaly_score = float(ae_outputs[3][0]) if len(ae_outputs) > 3 else 0.0

            # Tentukan status berdasarkan hasil AI
            soil_status = "HARD_ROCK" if pressure > 250 or im_vibration > 2.5 else "NORMAL_SOFT"
            stress = "ELEVATED_STRESS" if is_anomaly or severity_score > 2.0 else "NORMAL"
            action = "Kurangi kecepatan dorong bucket!" if stress == "ELEVATED_STRESS" else "Status operasional aman."

        except Exception as ai_err:
            print(f"[ERROR AI Inference]: {ai_err}")
            soil_status, stress, action, severity_score, anomaly_score = "UNKNOWN", "NORMAL", "Sistem stabil.", 0.0, 0.0

        # --- 4. BUNGKUS KE FORMAT JSON PAYLOAD ---
        payload = {
            "device_id": "terracortex_unit_01",
            "timestamp": int(time.time()),
            "sensors": {
                "imu_vibration": im_vibration,
                "hydraulic_pressure_bar": pressure,
                "oil_temperature_c": temp
            },
            "cortex_inference": {
                "soil_strata": soil_status,
                "machine_stress_status": stress,
                "severity_index": round(severity_score, 3),
                "is_anomaly": is_anomaly,
                "anomaly_score": round(anomaly_score, 3),
                "action_advisory": action
            }
        }
        
        # Kirim data ke MQTT Broker secara live
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
        
        # Cetak output rapi ke terminal
        print(json.dumps(payload, indent=2))
        print("-" * 50)
        
        time.sleep(3)
        
except KeyboardInterrupt:
    print("\n[INFO] Stream data dihentikan.")
    mqtt_client.loop_start()
    mqtt_client.disconnect()