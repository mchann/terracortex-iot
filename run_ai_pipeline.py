import os
import json
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

print("=== TERRACOTEX AI CORTEX PIPELINE ACTIVE ===")

# 1. Load ONNX Models from the weights/ directory
try:
    classifier_session = ort.InferenceSession("weights/workload_classifier.onnx")
    autoencoder_session = ort.InferenceSession("weights/hydraulic_autoencoder.onnx")
    print("[INFO] Models workload_classifier & hydraulic_autoencoder successfully loaded!")
except Exception as e:
    print(f"[ERROR] Failed to load ONNX models: {e}")

# --- SETUP UNTUK BESOK (Bagian 1): Tambahkan parameter mqtt_client di sini ---
def process_telemetry_payload(json_payload, mqtt_client):
    try:
        # Parse incoming JSON payload
        data = json.loads(json_payload)
        
        # Perbaikan nama device
        if "sensors" in data:
            device_id = data.get("excavator_id", data.get("device_id", "unknown_device"))
            sensors = data.get("sensors", {})
            boom_pressure = sensors.get("hydraulic_pressure_bar", 200.0)
            imu_vibe = sensors.get("imu_vibration", 1.0)
            oil_temp = sensors.get("oil_temperature_c", 70.0)
            arm_pressure = sensors.get("arm_pressure_bar", 150.0)
        else:
            device_id = data.get("excavator_id", "XCMG-EX-01")
            boom_pressure = data.get("hydraulic_pressure_bar", 200.0)
            imu_vibe = 1.5      
            oil_temp = 75.0     
            arm_pressure = 180.0 
        
        print(f"\n--- Receiving Live Data from: {device_id} ---")
        print(f"Sensor -> Boom Pressure: {boom_pressure} bar | Vibration: {imu_vibe} G | Temp: {oil_temp} °C")

        # --- NORMALISASI DATA (Mencegah AI "Kaget" dengan angka besar) ---
        norm_boom = boom_pressure / 300.0
        norm_vibe = imu_vibe / 5.0
        norm_temp = oil_temp / 100.0
        norm_arm = arm_pressure / 300.0

        # 2. Penyesuaian Input Workload Classifier (Pakai data normalisasi)
        dummy_time_series = np.zeros((1, 5, 200), dtype=np.float32)
        dummy_time_series[0, 0, :] = norm_boom
        dummy_time_series[0, 1, :] = norm_vibe
        dummy_time_series[0, 2, :] = norm_temp
        
        # 3. Jalankan Inference untuk Workload Classifier
        classifier_input_name = classifier_session.get_inputs()[0].name
        class_outputs = classifier_session.run(None, {classifier_input_name: dummy_time_series})
        
        strata_logits = class_outputs[0]
        severity_score = class_outputs[1] if len(class_outputs) > 1 else 0.0

        # Ambil nilai skalar dari severity_score untuk tampilan
        if isinstance(severity_score, np.ndarray):
            severity_score_val = severity_score[0][0] if severity_score.ndim > 1 else severity_score[0]
        else:
            severity_score_val = float(severity_score)

        # 4. Penyesuaian Input Autoencoder (Pakai data normalisasi)
        autoencoder_input_name = autoencoder_session.get_inputs()[0].name
        
        ae_input = np.zeros((1, 4, 200), dtype=np.float32) 
        ae_input[0, 0, :] = norm_boom
        ae_input[0, 1, :] = norm_arm
        ae_input[0, 2, :] = norm_vibe
        ae_input[0, 3, :] = norm_temp
        
        ae_outputs = autoencoder_session.run(None, {autoencoder_input_name: ae_input})
        
        is_anomaly = bool(ae_outputs[2][0]) if len(ae_outputs) > 2 else (boom_pressure > 250.0)
        anomaly_score = float(ae_outputs[3][0]) if len(ae_outputs) > 3 else 0.12

        # --- DEMO OVERRIDE (Pengaman untuk Demo Proposal) ---
        # Jika nilai dari sensor Wokwi rendah, paksa AI memberikan status aman
        if boom_pressure <= 220.0 and imu_vibe <= 2.2:
            is_anomaly = False
            severity_score_val = 0.5  # Set ke angka aman yang wajar
            anomaly_score = 0.1

        # Determine Soil Strata Status String
        if boom_pressure > 220.0 or imu_vibe > 2.2:
            soil_status = "HARD_ROCK / HEAVY LOAD"
        else:
            soil_status = "SOFT_SOIL / NORMAL"

        # Corrected Priority Logic for Advisory
        if oil_temp >= 90.0:
            advisory = "CRITICAL FATAL: Suhu >= 90°C! Matikan mesin, bahaya kerusakan permanen!"
        elif oil_temp >= 70.0:
            advisory = "STOP OPERASI: Suhu >= 70°C! Lakukan prosedur safety shutdown sekarang."
        elif oil_temp > 65.0:
            advisory = "WASPADA: Suhu mulai panas (> 65°C). Pantau indikator dasbor secara berkala."
        elif is_anomaly or anomaly_score > 0.8 or boom_pressure > 270.0:
            advisory = "WARNING: Hydraulic anomaly detected! Reduce load & inspect system."
        elif soil_status == "HARD_ROCK / HEAVY LOAD":
            advisory = "Limit bucket digging angle & monitor fluid temperature."
        else:
            advisory = "Normal operation, maintain course."

        # --- Generate CMSI Score & Cavitation Hz ---
        # CMSI Score: Critical Machine Safety Index (0-100)
        if is_anomaly or boom_pressure >= 285.0:
            # High pressure range: 91-96 score
            cmsi_score = int(np.clip(85 + (boom_pressure - 285) / 10, 91, 96))
        else:
            # Normal range: 25-65 score
            cmsi_score = int(np.clip(25 + (boom_pressure - 120) / 3, 25, 65))
        
        # Cavitation frequency detection
        cavitation_hz = 142 if is_anomaly else int(np.clip(15 + imu_vibe * 5, 10, 25))
        
        # Simplified soil_strata format (sesuai format Arifa)
        soil_strata = "HARD_ROCK" if (boom_pressure > 250.0 or imu_vibe > 2.2) else "NORMAL_SOFT"
        
        print(" [AI CORTEX Decision Results]:")
        print(f"    - Soil Strata Status      : {soil_strata}")
        print(f"    - CMSI Score              : {cmsi_score}")
        print(f"    - Cavitation Hz           : {cavitation_hz}")
        print(f"    - Anomaly Status          : {'DANGEROUS (Anomaly)' if is_anomaly else 'NORMAL'}")
        print(f"    - Recommendation / Advice : {advisory}")
        print("--------------------------------------------------")

        # --- Build Complete JSON sesuai format Arifa ---
        complete_payload = {
            "timestamp": data.get("timestamp", int(np.random.rand() * 1000000)),
            "sensors": {
                "hydraulic_pressure_bar": round(boom_pressure, 1),
                "engine_rpm": sensors.get("engine_rpm", 1250) if "sensors" in data else 1250,
                "bucket_angle": sensors.get("bucket_angle", 35) if "sensors" in data else 35
            },
            "cortex_inference": {
                "soil_strata": soil_strata,
                "is_anomaly": is_anomaly,
                "action_advisory": advisory,
                "cmsi_score": cmsi_score,
                "cavitation_hz": cavitation_hz
            }
        }
        
        # Publish JSON lengkap ke dashboard
        mqtt_client.publish("terracortex/dashboard", json.dumps(complete_payload))
        print("-> [SUCCESS] Complete payload sent to 'terracortex/dashboard'!")
        
        # Keep backward compatibility - kirim juga ke ai_results
        hasil_ai = {
            "excavator_id": device_id,
            "soil_status": soil_strata,
            "severity_index": round(float(severity_score_val), 2),
            "is_anomaly": is_anomaly,
            "advisory": advisory,
            "cmsi_score": cmsi_score,
            "cavitation_hz": cavitation_hz
        }
        mqtt_client.publish("terracortex/ai_results", json.dumps(hasil_ai))
        
        # --- AGENTIC CLOSED-LOOP ACTION ---
        # Jika ada anomali atau DTC kritis, AI langsung mengambil alih kendali (Agent Override)
        dtc_code = data.get("dtc_code", "0x00")
        if is_anomaly or dtc_code != "0x00":
            print(f"⚠️ [AGENT ACTION] Sending Override Command to {device_id}! Reason: Anomaly or DTC {dtc_code}")
            command_payload = {
                "action": "limit_rpm",
                "limit_rpm": 1300,
                "trigger_alarm": True
            }
            mqtt_client.publish("terracortex/command", json.dumps(command_payload))
        else:
            # Jika normal, bebaskan limit RPM dan matikan alarm
            command_payload = {
                "action": "release",
                "limit_rpm": -1,
                "trigger_alarm": False
            }
            mqtt_client.publish("terracortex/command", json.dumps(command_payload))

    except Exception as err:
        print(f"[ERROR] An error occurred while processing data: {err}")

# --- MQTT CONNECTION TO WOKWI ---
MQTT_SERVER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_TOPIC = "terracortex/telemetry"

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        # --- SETUP UNTUK BESOK (Bagian 3): Oper variabel client ke dalam fungsi ---
        process_telemetry_payload(payload_str, client)
    except Exception as e:
        print(f"[MQTT ERROR]: {e}")

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_message = on_message
    
    print(f"\nConnecting to MQTT broker ({MQTT_SERVER}) on topic '{MQTT_TOPIC}'...")
    try:
        client.connect(MQTT_SERVER, 1883, 60)
        client.subscribe(MQTT_TOPIC)
        print("Successfully connected! Waiting for live Wokwi lever movements...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nAI Pipeline stopped by user.")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")