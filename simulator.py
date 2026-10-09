import os
import sys
import time
import random
import json
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

print("=== TERRACORTEX INTEGRATED SIMULATOR & AI CORTEX ===")

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
weights_dir = os.path.join(BASE_DIR, "weights")
try:
    classifier_session = ort.InferenceSession(os.path.join(weights_dir, "workload_classifier.onnx"))
    autoencoder_session = ort.InferenceSession(os.path.join(weights_dir, "hydraulic_autoencoder.onnx"))
    print("[INFO] Model ONNX (Classifier & Autoencoder) berhasil dimuat!\n" + "="*50)
except Exception as e:
    print(f"[ERROR] Gagal memuat model ONNX: {e}")
    exit()

def send_telemetry_sample(pressure, im_vibration, temp, dtc_code="0x00"):
    try:
        norm_boom = pressure / 300.0
        norm_vibe = im_vibration / 5.0
        norm_temp = temp / 100.0

        cls_input = np.zeros((1, 5, 200), dtype=np.float32)
        cls_input[0, 0, :] = norm_boom
        cls_input[0, 1, :] = norm_vibe
        cls_input[0, 2, :] = norm_temp
        
        cls_name = classifier_session.get_inputs()[0].name
        class_outputs = classifier_session.run(None, {cls_name: cls_input})
        severity_score = float(class_outputs[1][0]) if len(class_outputs) > 1 else 0.0

        ae_input = np.zeros((1, 4, 200), dtype=np.float32)
        ae_input[0, 0, :] = norm_boom
        ae_input[0, 1, :] = 150.0 / 300.0
        ae_input[0, 2, :] = norm_vibe
        ae_input[0, 3, :] = norm_temp
        
        ae_name = autoencoder_session.get_inputs()[0].name
        ae_outputs = autoencoder_session.run(None, {ae_name: ae_input})
        
        is_anomaly = bool(ae_outputs[2][0]) if len(ae_outputs) > 2 else (pressure > 280.0)
        anomaly_score = float(ae_outputs[3][0]) if len(ae_outputs) > 3 else (0.9 if is_anomaly else 0.1)

        soil_status = "HARD_ROCK" if pressure > 250 or im_vibration > 2.2 else "NORMAL_SOFT"
        stress = "CRITICAL_STRESS" if is_anomaly or pressure >= 285.0 else "NORMAL"
        action = "Kurangi kecepatan dorong bucket! Waspada kavitasi." if stress != "NORMAL" else "Status operasional aman."

    except Exception as ai_err:
        print(f"[ERROR AI Inference]: {ai_err}")
        soil_status, stress, action, severity_score, anomaly_score, is_anomaly = "NORMAL_SOFT", "NORMAL", "Sistem stabil.", 0.0, 0.0, False

    is_high_load = (pressure >= 285.0)
    engine_rpm = int(1750 + (pressure - 285.0) * 2.3) if is_high_load else int(1100 + (pressure - 120.0) * 1.2)
    bucket_angle = int(70 + (pressure - 285.0) * 0.23) if is_high_load else int(30 + (pressure - 120.0) * 0.09)

    payload = {
        "excavator_id": "XCMG-EX-01",
        "timestamp": int(time.time()),
        "dtc_code": dtc_code,
        "sensors": {
            "hydraulic_pressure_bar": round(pressure, 1),
            "imu_vibration": round(im_vibration, 2),
            "oil_temperature_c": round(temp, 1),
            "engine_rpm": engine_rpm,
            "bucket_angle": bucket_angle
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
    
    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
    print(f"\n[LIVE PUBLISH -> {MQTT_TOPIC}] Pressure: {pressure} bar | Vibe: {im_vibration} G | Temp: {temp} °C | Status: {stress}")
    print(json.dumps(payload, indent=2))
    print("-" * 50)

# Mode Manual / Interactive CLI
if "--manual" in sys.argv or "-m" in sys.argv:
    print("\n🎮 MODE MANUAL / DETERMINISTIK DIAKTIFKAN")
    print("Atur sensor tanpa nilai acak:")
    print("  [1] Normal Operation          (180 bar, 55.0°C, 1.2 G)")
    print("  [2] High Load Excavation      (290 bar, 68.0°C, 2.2 G)")
    print("  [3] Critical Cavitation Anomaly (348 bar, 76.5°C, 2.8 G)")
    print("  [4] Trigger DTC Fault Button  (320 bar, J1939-SPN94 Critical)")
    print("  [5] Custom Input Manual")
    print("  [q] Keluar\n")

    while True:
        try:
            choice = input("Pilih skenario [1-5 / q]: ").strip()
            if choice == '1':
                send_telemetry_sample(180.0, 1.2, 55.0)
            elif choice == '2':
                send_telemetry_sample(290.0, 2.2, 68.0)
            elif choice == '3':
                send_telemetry_sample(348.0, 2.8, 76.5)
            elif choice == '4':
                send_telemetry_sample(320.0, 2.5, 74.0, dtc_code="J1939-SPN94")
            elif choice == '5':
                p = float(input("  Tekanan hidrolik bar (120-350): "))
                v = float(input("  Getaran IMU G (0.5-4.0): "))
                t = float(input("  Suhu oli °C (40-95): "))
                send_telemetry_sample(p, v, t)
            elif choice.lower() == 'q':
                break
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"Error input: {e}")

else:
    # Mode interval stream default
    print("\n[INFO] Menjalankan interval stream telemetri (Tekan Ctrl+C untuk berhenti, atau gunakan --manual untuk kontrol pasti)...")
    try:
        while True:
            im_vibration = round(random.uniform(0.5, 3.5), 2)
            pressure = round(random.uniform(120.0, 290.0), 1)
            temp = round(random.uniform(65.0, 85.0), 1)
            send_telemetry_sample(pressure, im_vibration, temp)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[INFO] Stream data dihentikan.")
        mqtt_client.disconnect()
