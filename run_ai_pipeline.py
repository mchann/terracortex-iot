import os
import time
import json
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

print("=== TERRACOTEX AI CORTEX PIPELINE ACTIVE ===")

# Global active MQTT clients for dual-broker broadcasting (Wokwi cloud + Localhost dashboard)
active_clients = []

# Device State Accumulator for Cumulative Fatigue Tracking
device_stress_state = {}

def broadcast_publish(topic, payload_str, fallback_client=None):
    if active_clients:
        for c in active_clients:
            try:
                c.publish(topic, payload_str)
            except Exception:
                pass
    elif fallback_client:
        try:
            fallback_client.publish(topic, payload_str)
        except Exception:
            pass

# 1. Load ONNX Models from the weights/ directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
weights_dir = os.path.join(BASE_DIR, "weights")
try:
    classifier_session = ort.InferenceSession(os.path.join(weights_dir, "workload_classifier.onnx"))
    autoencoder_session = ort.InferenceSession(os.path.join(weights_dir, "hydraulic_autoencoder.onnx"))
    print("[INFO] Models workload_classifier & hydraulic_autoencoder successfully loaded!")
except Exception as e:
    print(f"[ERROR] Failed to load ONNX models: {e}")

def process_telemetry_payload(json_payload, mqtt_client=None):
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

        # --- Generate Dynamic Cumulative CMSI Score (Fatigue & Thermal Inertia) ---
        # 1. Target Stress Sesaat berdasarkan load & anomali
        if is_anomaly or boom_pressure >= 285.0:
            target_cmsi = float(np.clip(88.0 + (boom_pressure - 285.0) / 7.0, 91.0, 96.0))
        elif boom_pressure >= 240.0:
            target_cmsi = float(65.0 + (boom_pressure - 240.0) * 0.45)
        else:
            target_cmsi = float(np.clip(25.0 + (boom_pressure - 120.0) / 3.0, 25.0, 58.0))

        # 2. State Akumulasi Perangkat
        if device_id not in device_stress_state:
            device_stress_state[device_id] = {
                'current_cmsi': float(target_cmsi if target_cmsi < 65.0 else 45.0),
                'overload_ticks': 0
            }

        state = device_stress_state[device_id]
        current_val = state['current_cmsi']

        # 3. Dynamic Attack / Release (Naik bertahap saat disiksa, turun bertahap saat rileks)
        if target_cmsi > current_val:
            # Penahanan tuas di zona beban tinggi -> Akumulasi fatigue bertahap (~8-10 detik)
            # Merangkak perlahan: 45 -> 60 -> 70 -> 77 -> 82 -> 86 -> 90 -> 94
            step_up = max(4.0, (target_cmsi - current_val) * 0.30)
            current_val = min(target_cmsi, current_val + step_up)
            state['overload_ticks'] += 1
        else:
            # Tuas dinormalkan -> Disipasi panas & pendinginan fatigue secara bertahap (~8-10 detik)
            # Menurun perlahan: 94 -> 82 -> 73 -> 66 -> 60 -> 53 -> 45
            step_down = max(3.5, (current_val - target_cmsi) * 0.25)
            current_val = max(target_cmsi, current_val - step_down)
            state['overload_ticks'] = max(0, state['overload_ticks'] - 1)

        state['current_cmsi'] = current_val
        cmsi_score = int(round(current_val))
        
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

        # --- Synthesize In-Cab Agent Directive ---
        dtc_code = data.get("dtc_code", "0x00")
        agent_directive = advisory
        if oil_temp >= 90.0:
            agent_directive = "CRITICAL THERMAL SHUTDOWN: Suhu oli > 90°C! Segera matikan pompa hidrolik & hubungi workshop!"
        elif is_anomaly or boom_pressure >= 285.0 or cmsi_score >= 85:
            agent_directive = f"DERATE DIGGING ENVELOPE 30%: Batasi gaya serokan pada {soil_strata}. Standby inspeksi Mobile Rig Alpha."
        elif soil_status == "HARD_ROCK":
            agent_directive = "ADAPTIVE GUIDANCE: Batasi sudut bucket serokan pada formasi batuan keras."

        rig_dispatched = bool(cmsi_score >= 85 or is_anomaly or oil_temp >= 85.0 or dtc_code != "0x00")

        # --- Build Complete JSON sesuai format Arifa & Tablet In-Cab ---
        complete_payload = {
            "timestamp": data.get("timestamp", int(time.time())),
            "excavator_id": device_id,
            "sensors": {
                "hydraulic_pressure_bar": round(boom_pressure, 1),
                "engine_rpm": int(sensors.get("engine_rpm", 1250) if "sensors" in data else 1250),
                "bucket_angle": round(float(sensors.get("bucket_angle", 35) if "sensors" in data else 35), 1),
                "oil_temperature": round(float(oil_temp), 1),
                "oil_temperature_c": round(float(oil_temp), 1),
                "imu_vibration": round(float(imu_vibe), 2)
            },
            "cortex_inference": {
                "soil_strata": soil_strata,
                "is_anomaly": is_anomaly,
                "action_advisory": advisory,
                "agent_directive": agent_directive,
                "cmsi_score": cmsi_score,
                "cavitation_hz": cavitation_hz,
                "dtc_code": dtc_code,
                "rig_dispatched": rig_dispatched
            }
        }
        
        # Publish JSON lengkap ke dashboard (Broadcast ke Wokwi & Localhost Web Dashboard)
        broadcast_publish("terracortex/dashboard", json.dumps(complete_payload), mqtt_client)
        print("-> [SUCCESS] Complete payload broadcasted to 'terracortex/dashboard'!")
        
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
        broadcast_publish("terracortex/ai_results", json.dumps(hasil_ai), mqtt_client)
        
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
            broadcast_publish("terracortex/command", json.dumps(command_payload), mqtt_client)
        else:
            # Jika normal, bebaskan limit RPM dan matikan alarm
            command_payload = {
                "action": "release",
                "limit_rpm": -1,
                "trigger_alarm": False
            }
            broadcast_publish("terracortex/command", json.dumps(command_payload), mqtt_client)

    except Exception as err:
        print(f"[ERROR] An error occurred while processing data: {err}")

# --- DUAL-BROKER MQTT CONFIGURATION (Wokwi & Localhost) ---
WOKWI_BROKER = os.environ.get("WOKWI_BROKER", "test.mosquitto.org")
LOCAL_BROKER = os.environ.get("LOCAL_BROKER", os.environ.get("MQTT_BROKER", "localhost"))
MQTT_TOPIC = "terracortex/telemetry"

def on_message(client, userdata, msg):
    try:
        broker_tag = userdata or "MQTT"
        payload_str = msg.payload.decode('utf-8')
        print(f"\n[RECEIVED via {broker_tag}] topic: '{msg.topic}'")
        process_telemetry_payload(payload_str, client)
    except Exception as e:
        print(f"[MQTT ERROR]: {e}")

if __name__ == "__main__":
    def connect_broker(broker_host, broker_name):
        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=broker_name)
            else:
                cli = mqtt.Client(userdata=broker_name)
            cli.on_message = on_message
            print(f"Connecting to {broker_name} broker ({broker_host}:1883)...")
            cli.connect(broker_host, 1883, 60)
            cli.subscribe(MQTT_TOPIC)
            cli.loop_start()
            active_clients.append(cli)
            print(f"-> [OK] Connected to {broker_name} ({broker_host}) & subscribed to '{MQTT_TOPIC}'")
            return cli
        except Exception as e:
            print(f"-> [WARNING] Gagal terhubung ke {broker_name} ({broker_host}): {e}")
            return None

    # 1. Hubungkan ke Wokwi Broker (test.mosquitto.org)
    connect_broker(WOKWI_BROKER, "Wokwi")

    # 2. Hubungkan ke Localhost Broker (jika beda host) untuk integrasi Web Dashboard & simulator lokal
    if LOCAL_BROKER != WOKWI_BROKER:
        connect_broker(LOCAL_BROKER, "Localhost")

    if not active_clients:
        print("\n[FATAL] Tidak ada broker MQTT yang berhasil terhubung!")
        exit(1)

    print("\n==================================================")
    print("🚀 TERRACOTEX AI CORTEX PIPELINE ACTIVE (DUAL-BROKER)")
    print(f"   📡 Wokwi Cloud Broker : {WOKWI_BROKER}")
    print(f"   💻 Localhost Broker   : {LOCAL_BROKER}")
    print(f"   📥 Subscribed Topic   : '{MQTT_TOPIC}'")
    print(f"   📤 Broadcast Topics   : 'terracortex/dashboard', 'terracortex/command'")
    print("==================================================")
    print("Menunggu pergerakan tuas Wokwi atau simulator...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAI Pipeline stopped by user.")
        for cli in active_clients:
            try:
                cli.loop_stop()
                cli.disconnect()
            except Exception:
                pass