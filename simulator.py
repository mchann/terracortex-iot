import os
import sys
import time
import random
import json
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

print("=== TERRACORTEX MULTI-SCENARIO SENSOR SIMULATOR & AI CORTEX ===")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_TOPIC = "terracortex/telemetry"

mqtt_client = mqtt.Client(client_id="terracortex_python_simulator")
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
    print("[INFO] Berhasil terhubung ke MQTT Broker: " + MQTT_BROKER + ":" + str(MQTT_PORT))
except Exception as e:
    print("[ERROR] Gagal terhubung ke broker MQTT:", e)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
weights_dir = os.path.join(BASE_DIR, "weights")
classifier_session = None
autoencoder_session = None

try:
    classifier_session = ort.InferenceSession(os.path.join(weights_dir, "workload_classifier.onnx"))
    autoencoder_session = ort.InferenceSession(os.path.join(weights_dir, "hydraulic_autoencoder.onnx"))
    print("[INFO] Model ONNX (Classifier & Autoencoder) berhasil dimuat!")
except Exception as e:
    print("[NOTE] Model ONNX lokal fallback mode:", e)

SCENARIOS = {
    "1": {
        "name": "Operasi Normal (Tanah Lunak / Soft Soil)",
        "unit_id": "XCMG-EX-01",
        "pressure": 180.0,
        "vibration": 1.1,
        "temp": 55.0,
        "rpm": 1200,
        "bucket_angle": 35.0,
        "cavitation_hz": 20.0,
        "dtc_code": "0x00",
        "soil_strata": "NORMAL_SOFT",
        "desc": "Kondisi kerja nominal sehat, CMSI stabil rendah (35-45), bar operator hijau."
    },
    "2": {
        "name": "Beban Berat Batuan Keras (Bukan Kerusakan)",
        "unit_id": "XCMG-EX-01",
        "pressure": 285.0,
        "vibration": 2.0,
        "temp": 64.0,
        "rpm": 1850,
        "bucket_angle": 65.0,
        "cavitation_hz": 35.0,
        "dtc_code": "0x00",
        "soil_strata": "HARD_ROCK",
        "desc": "Mencangkul Hard Basalt. CMSI naik ke ~70-75 (Kuning/Warning). Operator cukup derate 30% tanpa perlu panggil montir."
    },
    "3": {
        "name": "Kavitasi Pompa & Aus Katup Kontrol (Kasus EX-04)",
        "unit_id": "EX-04",
        "pressure": 348.0,
        "vibration": 2.8,
        "temp": 76.5,
        "rpm": 1950,
        "bucket_angle": 85.0,
        "cavitation_hz": 142.0,
        "dtc_code": "SPN 520204 / FMI 14",
        "soil_strata": "HARD_ROCK",
        "desc": "Kavitasi parah 142 Hz. CMSI akumulasi ke >90 (Merah/Kritis). Butuh Parker Spool Valve Seal Kit."
    },
    "4": {
        "name": "Radiator Buntu / Suhu Oli Ekstrem Mendidih (Kasus EX-08)",
        "unit_id": "EX-08",
        "pressure": 200.0,
        "vibration": 1.2,
        "temp": 96.5,
        "rpm": 1250,
        "bucket_angle": 38.0,
        "cavitation_hz": 24.0,
        "dtc_code": "SPN 520301 / FMI 16",
        "soil_strata": "NORMAL_SOFT",
        "desc": "Tekanan normal, getaran rendah, TAPI SUHU 96.5 C MENDIDIH! Hard Safety Shutdown detik ini juga."
    },
    "5": {
        "name": "Katup Pelepas Bergetar / Relief Valve Flutter (Kasus EX-17)",
        "unit_id": "EX-17",
        "pressure": 342.0,
        "vibration": 3.9,
        "temp": 72.0,
        "rpm": 1900,
        "bucket_angle": 82.0,
        "cavitation_hz": 155.0,
        "dtc_code": "SPN 520210 / FMI 08",
        "soil_strata": "HARD_ROCK",
        "desc": "Pulsasi hidrolik 155 Hz pada main relief valve. Butuh Main Relief Valve Cartridge 350-bar."
    },
    "6": {
        "name": "Gigi Pemutar & Bantalan Aus / Slew Pinion Shock (Kasus EX-12 / EX-33)",
        "unit_id": "EX-12",
        "pressure": 220.0,
        "vibration": 4.5,
        "temp": 88.5,
        "rpm": 1350,
        "bucket_angle": 45.0,
        "cavitation_hz": 138.0,
        "dtc_code": "SPN 520198 / FMI 02",
        "soil_strata": "NORMAL_SOFT",
        "desc": "Tekanan hidrolik normal, tapi getaran sasis IMU 4.5 G ekstrem saat swing. RUL 18 Jam. Butuh Slew Pinion Drive Shaft."
    },
    "7": {
        "name": "Silinder Bocor Dalam / Internal Bypass Leakage (Kasus EX-27)",
        "unit_id": "EX-27",
        "pressure": 140.0,
        "vibration": 1.4,
        "temp": 82.0,
        "rpm": 1800,
        "bucket_angle": 30.0,
        "cavitation_hz": 42.0,
        "dtc_code": "SPN 520144 / FMI 07",
        "soil_strata": "NORMAL_SOFT",
        "desc": "RPM digeber tapi tekanan ngempos (140 bar), oli panas gesekan bocor internal. Butuh Boom Cylinder Piston Seal Pack."
    },
    "8": {
        "name": "Pompa Utama Rusak Fatal & Stok Gudang Habis (Kasus EX-31)",
        "unit_id": "EX-31",
        "pressure": 338.0,
        "vibration": 3.8,
        "temp": 85.0,
        "rpm": 1900,
        "bucket_angle": 80.0,
        "cavitation_hz": 98.0,
        "dtc_code": "SPN 520150 / FMI 00",
        "soil_strata": "HARD_ROCK",
        "desc": "Pompa aus berat & stok di gudang 0 unit (Stockout). Agent otomatis terbitkan Emergency Purchase Order (PO-EMG-EX31)."
    }
}

def send_telemetry_sample(pressure, im_vibration, temp, rpm=1400, bucket_angle=45.0, cavitation_hz=25.0, dtc_code="0x00", unit_id="XCMG-EX-01"):
    severity_score = 0.0
    anomaly_score = 0.0
    is_anomaly = False

    if classifier_session and autoencoder_session:
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
        except Exception:
            pass
    else:
        is_anomaly = (pressure >= 285.0 or temp >= 90.0 or im_vibration >= 3.0 or dtc_code != "0x00")
        anomaly_score = 0.92 if is_anomaly else 0.08

    soil_status = "HARD_ROCK" if (pressure > 250.0 or im_vibration > 2.2) else "NORMAL_SOFT"
    stress = "CRITICAL_STRESS" if (is_anomaly or pressure >= 285.0 or temp >= 90.0) else "NORMAL"
    action = "Kurangi beban segera! Anomali terdeteksi." if stress != "NORMAL" else "Status operasional aman."

    payload = {
        "excavator_id": unit_id,
        "timestamp": int(time.time()),
        "dtc_code": dtc_code,
        "sensors": {
            "hydraulic_pressure_bar": round(pressure, 1),
            "imu_vibration": round(im_vibration, 2),
            "oil_temperature_c": round(temp, 1),
            "engine_rpm": int(rpm),
            "bucket_angle": round(bucket_angle, 1),
            "cavitation_freq_hz": round(cavitation_hz, 1)
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
    
    pub_res = mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
    pub_res.wait_for_publish(timeout=1.0)
    print("-> [SENT -> " + MQTT_TOPIC + "] " + unit_id + " | " + str(pressure) + " bar (" + str(round(pressure/10.0, 1)) + " MPa) | " + str(temp) + "C | " + str(im_vibration) + "G | " + str(rpm) + " RPM | " + dtc_code)
    return payload

def run_interactive_menu():
    border = "=" * 65
    print("")
    print(border)
    print(" PILIH SKENARIO UJI MULTI-SENSOR DETERMINISTIK (NO RANDOM)")
    print(border)
    for k, sc in SCENARIOS.items():
        print("  [" + k + "] " + sc["name"])
        print("      -> " + str(sc["pressure"]) + " bar | " + str(sc["temp"]) + "C | " + str(sc["vibration"]) + "G | " + str(sc["rpm"]) + " RPM | " + sc["dtc_code"])
        print("      -> " + sc["desc"])
    print("  [9] Custom Input Manual (Ketik Sendiri Angkanya)")
    print("  [q] Keluar")
    print("")

    while True:
        try:
            choice = input("Pilih skenario [1-9 / q]: ").strip()
            if choice.lower() == "q":
                break
            
            if choice in SCENARIOS:
                sc = SCENARIOS[choice]
                print()
                print(">> Anda memilih: [" + choice + "] " + sc["name"])
                mode = input("   Kirim: [1] Sekali kirim (Single Shot) | [2] Tahan terus (Continuous Loop 1.5s)? [1/2]: ").strip()
                
                if mode == "2":
                    print("   >> Mengirim streaming terus-menerus ke " + sc["unit_id"] + "... Tekan Ctrl+C untuk kembali ke menu.")
                    try:
                        while True:
                            send_telemetry_sample(
                                pressure=sc["pressure"],
                                im_vibration=sc["vibration"],
                                temp=sc["temp"],
                                rpm=sc["rpm"],
                                bucket_angle=sc["bucket_angle"],
                                cavitation_hz=sc["cavitation_hz"],
                                dtc_code=sc["dtc_code"],
                                unit_id=sc["unit_id"]
                            )
                            time.sleep(1.5)
                    except KeyboardInterrupt:
                        print("   [STOP] Streaming skenario dihentikan.")
                else:
                    send_telemetry_sample(
                        pressure=sc["pressure"],
                        im_vibration=sc["vibration"],
                        temp=sc["temp"],
                        rpm=sc["rpm"],
                        bucket_angle=sc["bucket_angle"],
                        cavitation_hz=sc["cavitation_hz"],
                        dtc_code=sc["dtc_code"],
                        unit_id=sc["unit_id"]
                    )
                    print("   [OK] 1 Sampel berhasil dikirim! ")

            elif choice == "9":
                p = float(input("  Tekanan hidrolik bar (100-360): "))
                t = float(input("  Suhu oli C (40-105): "))
                v = float(input("  Getaran IMU G (0.5-5.0): "))
                r = int(input("  RPM Mesin (800-2200): "))
                dtc = input("  Kode DTC (default 0x00): ").strip() or "0x00"
                uid = input("  Unit ID (default EX-04): ").strip() or "EX-04"
                send_telemetry_sample(p, v, t, rpm=r, dtc_code=dtc, unit_id=uid)
                print("   [OK] Sampel kustom berhasil dikirim! ")
            else:
                print("Pilihan tidak valid, pilih 1-9 atau q.")
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print("Error input:", err)

if __name__ == "__main__":
    run_interactive_menu()
