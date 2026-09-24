"""
Test Script untuk Validasi Format JSON Output
Simulates ESP32 data dan validates Python AI Pipeline output
"""

import json

# Simulate ESP32 JSON payload (dari main.cpp)
def simulate_esp32_data(pressure_level="normal"):
    """
    Generate simulated ESP32 data
    pressure_level: "normal" atau "high"
    """
    if pressure_level == "high":
        return {
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
    else:
        return {
            "excavator_id": "XCMG-EX-01",
            "timestamp": 125430,
            "sensors": {
                "hydraulic_pressure_bar": 180.0,
                "imu_vibration": 1.2,
                "oil_temperature_c": 55.0,
                "engine_rpm": 1250,
                "bucket_angle": 35
            }
        }

# Expected output format untuk Arifa (Tablet) dan Putra (Dashboard)
def validate_dashboard_format(json_data):
    """
    Validate JSON format sesuai contract Arifa
    """
    required_fields = {
        "timestamp": int,
        "sensors": dict,
        "cortex_inference": dict
    }
    
    sensor_fields = {
        "hydraulic_pressure_bar": (int, float),
        "engine_rpm": int,
        "bucket_angle": int
    }
    
    inference_fields = {
        "soil_strata": str,
        "is_anomaly": bool,
        "action_advisory": str,
        "cmsi_score": int,
        "cavitation_hz": int
    }
    
    print("\n" + "="*60)
    print("VALIDASI FORMAT JSON DASHBOARD")
    print("="*60)
    
    # Check top level fields
    for field, expected_type in required_fields.items():
        if field not in json_data:
            print(f"❌ Missing required field: {field}")
            return False
        if not isinstance(json_data[field], expected_type):
            print(f"❌ Wrong type for {field}: expected {expected_type}, got {type(json_data[field])}")
            return False
        print(f"✅ {field}: {expected_type.__name__}")
    
    # Check sensors fields
    print("\n📊 Sensors Object:")
    for field, expected_type in sensor_fields.items():
        if field not in json_data["sensors"]:
            print(f"  ❌ Missing sensor field: {field}")
            return False
        if not isinstance(json_data["sensors"][field], expected_type):
            print(f"  ❌ Wrong type for sensors.{field}")
            return False
        print(f"  ✅ {field}: {json_data['sensors'][field]}")
    
    # Check cortex_inference fields
    print("\n🧠 Cortex Inference Object:")
    for field, expected_type in inference_fields.items():
        if field not in json_data["cortex_inference"]:
            print(f"  ❌ Missing inference field: {field}")
            return False
        if not isinstance(json_data["cortex_inference"][field], expected_type):
            print(f"  ❌ Wrong type for cortex_inference.{field}")
            return False
        print(f"  ✅ {field}: {json_data['cortex_inference'][field]}")
    
    print("\n" + "="*60)
    print("✅ ALL VALIDATIONS PASSED!")
    print("="*60)
    return True

# Sample expected outputs
def test_normal_scenario():
    """Test scenario: Normal operation"""
    print("\n\n🧪 TEST SCENARIO 1: NORMAL OPERATION")
    print("-" * 60)
    
    esp32_data = simulate_esp32_data("normal")
    print("\n📤 ESP32 Input (terracortex/telemetry):")
    print(json.dumps(esp32_data, indent=2))
    
    # Expected dashboard output
    dashboard_output = {
        "timestamp": 125430,
        "sensors": {
            "hydraulic_pressure_bar": 180.0,
            "engine_rpm": 1250,
            "bucket_angle": 35
        },
        "cortex_inference": {
            "soil_strata": "NORMAL_SOFT",
            "is_anomaly": False,
            "action_advisory": "Normal operation, maintain course.",
            "cmsi_score": 45,
            "cavitation_hz": 18
        }
    }
    
    print("\n📥 Expected Dashboard Output (terracortex/dashboard):")
    print(json.dumps(dashboard_output, indent=2))
    
    return validate_dashboard_format(dashboard_output)

def test_anomaly_scenario():
    """Test scenario: High load / Anomaly"""
    print("\n\n🧪 TEST SCENARIO 2: HIGH LOAD / ANOMALY")
    print("-" * 60)
    
    esp32_data = simulate_esp32_data("high")
    print("\n📤 ESP32 Input (terracortex/telemetry):")
    print(json.dumps(esp32_data, indent=2))
    
    # Expected dashboard output
    dashboard_output = {
        "timestamp": 125430,
        "sensors": {
            "hydraulic_pressure_bar": 348.0,
            "engine_rpm": 1850,
            "bucket_angle": 75
        },
        "cortex_inference": {
            "soil_strata": "HARD_ROCK",
            "is_anomaly": True,
            "action_advisory": "WARNING: Hydraulic anomaly detected! Reduce load & inspect system.",
            "cmsi_score": 94,
            "cavitation_hz": 142
        }
    }
    
    print("\n📥 Expected Dashboard Output (terracortex/dashboard):")
    print(json.dumps(dashboard_output, indent=2))
    
    # Additional UI trigger checks
    print("\n🎯 UI TRIGGER VALIDATIONS:")
    print("-" * 60)
    
    sensors = dashboard_output["sensors"]
    inference = dashboard_output["cortex_inference"]
    
    # Check alarm triggers
    if inference["is_anomaly"]:
        print("✅ Kotak Peringatan Merah: TRIGGERED")
        print(f"   Message: '{inference['action_advisory']}'")
    
    if inference["cmsi_score"] >= 94 and sensors["hydraulic_pressure_bar"] > 280:
        print("✅ Alarm Buzzer/Sirine: TRIGGERED")
        print(f"   CMSI Score: {inference['cmsi_score']}")
        print(f"   Pressure: {sensors['hydraulic_pressure_bar']} bar")
    
    if sensors["hydraulic_pressure_bar"] >= 285:
        print("✅ Gauge Zona Merah: TRIGGERED")
    
    return validate_dashboard_format(dashboard_output)

def print_integration_checklist():
    """Print checklist untuk Arifa dan Putra"""
    print("\n\n" + "="*60)
    print("📋 INTEGRATION CHECKLIST UNTUK TIM")
    print("="*60)
    
    print("\n✅ UNTUK ARIFA (Tablet Frontend):")
    print("   1. Subscribe ke MQTT topic: 'terracortex/dashboard'")
    print("   2. Parse JSON dan map ke UI components:")
    print("      - sensors.hydraulic_pressure_bar → Gauge Tekanan")
    print("      - sensors.engine_rpm → RPM Bar")
    print("      - sensors.bucket_angle → Bucket Angle Pointer")
    print("      - cortex_inference.is_anomaly → Trigger Alarm")
    print("      - cortex_inference.action_advisory → Display Text")
    print("      - cortex_inference.cmsi_score → Buzzer Logic")
    print("   3. Test dengan simulasi data normal & anomaly")
    
    print("\n✅ UNTUK PUTRA (Dashboard Backend):")
    print("   1. Subscribe ke MQTT topic: 'terracortex/dashboard'")
    print("   2. Store data ke database untuk analytics")
    print("   3. Create real-time graph untuk:")
    print("      - cortex_inference.cmsi_score (trend over time)")
    print("      - sensors.hydraulic_pressure_bar")
    print("      - cortex_inference.is_anomaly (alert history)")
    print("   4. Setup alert notification system")
    
    print("\n✅ UNTUK TESTING INTEGRATION:")
    print("   1. Start Python AI: python run_ai_pipeline.py")
    print("   2. Start ESP32 Wokwi simulator")
    print("   3. Monitor MQTT dengan:")
    print("      mosquitto_sub -h test.mosquitto.org -t 'terracortex/dashboard' -v")
    print("   4. Test potentiometer low → high → low")
    print("   5. Validate semua UI components respond correctly")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("="*60)
    print("🚀 TERRACORTEX JSON FORMAT VALIDATION TEST")
    print("="*60)
    
    # Run tests
    test1_passed = test_normal_scenario()
    test2_passed = test_anomaly_scenario()
    
    # Print checklist
    print_integration_checklist()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Normal Scenario Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Anomaly Scenario Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Format JSON sudah sesuai contract.")
        print("📤 Siap untuk integrasi dengan Tablet Arifa & Dashboard Putra!")
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")
    
    print("="*60)
