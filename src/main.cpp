#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
Adafruit_MPU6050 mpu;

const int potPin = 32;
const int pinSuhu = 34;
const float BETA = 3950;

// --- New Agentic AI Pins ---
const int BUZZER_PIN = 25;
const int LED_WARNING_PIN = 26;
const int BTN_FAULT_PIN = 27;

// --- Agent Control Variables ---
int agent_rpm_limit = -1; // -1 means no limit
bool agent_alarm_active = false;
String current_dtc_code = "0x00";

// --- WiFi & MQTT Configuration ---
const char* ssid = "Wokwi-GUEST";
const char* password = "";
const char* mqtt_server = "test.mosquitto.org";

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("\nConnecting to WiFi...");
  WiFi.begin(ssid, password, 6); // Channel 6 specifically for Wokwi
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  if (String(topic) == "terracortex/command") {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, message);
    if (!error) {
      if (doc["limit_rpm"].is<int>()) {
        agent_rpm_limit = doc["limit_rpm"];
      }
      if (doc["trigger_alarm"].is<bool>()) {
        agent_alarm_active = doc["trigger_alarm"];
      }
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT Broker...");
    
    // Update OLED biar kelihatan gak nge-hang
    display.clearDisplay();
    display.setTextColor(WHITE);
    display.setCursor(0,0);
    display.println("WiFi: Connected!");
    display.println("Connecting MQTT...");
    display.display();

    String clientId = "TerraCortex-EX01-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT!");
      client.subscribe("terracortex/command"); // Listen to Agent AI Commands
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" Trying again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  
  pinMode(pinSuhu, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_WARNING_PIN, OUTPUT);
  pinMode(BTN_FAULT_PIN, INPUT_PULLUP); // Use internal pullup for button

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("OLED Error"));
    for(;;);
  }
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.print("Booting System...");
  display.display();
  delay(1000);

  if (!mpu.begin()) {
    Serial.println("MPU6050 Error!");
    while (1) { delay(10); }
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(mqtt_callback); // Set callback function
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); 

  // Read Fault Button (Active Low)
  if (digitalRead(BTN_FAULT_PIN) == LOW) {
    current_dtc_code = "J1939-SPN94"; // Fuel Delivery Pressure Critical
  } else {
    current_dtc_code = "0x00";
  }

  // 1. Read Sensors
  int potValue = analogRead(potPin);
  float pressure_bar = map(potValue, 0, 4095, 120, 350); 

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  float imu_vibration = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z)) / 9.81;

  int nilaiAnalogSuhu = analogRead(pinSuhu);
  float oil_temp = 1 / (log(1 / (4095. / max(nilaiAnalogSuhu, 1) - 1)) / BETA + 1.0 / 298.15) - 273.15;


  bool is_high_load = (pressure_bar >= 285.0);
  int engine_rpm = is_high_load ? map((int)pressure_bar, 285, 350, 1750, 1900) : map((int)pressure_bar, 120, 284, 1100, 1300);
  int bucket_angle = is_high_load ? map((int)pressure_bar, 285, 350, 70, 85) : map((int)pressure_bar, 120, 284, 30, 45);

  if (agent_rpm_limit != -1 && engine_rpm > agent_rpm_limit) {
    engine_rpm = agent_rpm_limit; // Override physical mapping
  }

  if (agent_alarm_active) {
    if (millis() % 500 < 250) {
      digitalWrite(LED_WARNING_PIN, HIGH);
      tone(BUZZER_PIN, 1000); 
    } else {
      digitalWrite(LED_WARNING_PIN, LOW);
      tone(BUZZER_PIN, 800);  
    }
  } else {
    digitalWrite(LED_WARNING_PIN, LOW);
    noTone(BUZZER_PIN); 
  }

  // 3. Build JSON Payload
  String payload = "{";
  payload += "\"excavator_id\": \"XCMG-EX-01\",";
  payload += "\"timestamp\": " + String(millis()) + ","; 
  payload += "\"dtc_code\": \"" + current_dtc_code + "\",";
  payload += "\"sensors\": {";
  payload += "\"hydraulic_pressure_bar\": " + String(pressure_bar, 1) + ",";
  payload += "\"imu_vibration\": " + String(imu_vibration, 2) + ",";
  payload += "\"oil_temperature_c\": " + String(oil_temp, 1) + ",";
  payload += "\"engine_rpm\": " + String(engine_rpm) + ",";
  payload += "\"bucket_angle\": " + String(bucket_angle);
  payload += "}}";
  
  // 4. Publish via MQTT
  Serial.println("Sending data to MQTT: " + payload);
  client.publish("terracortex/telemetry", payload.c_str());

  // 5. Update OLED Display
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("= TERRACORTEX LIVE =");
  display.print("Press: "); display.print(pressure_bar, 1); display.println(" bar");
  display.print("RPM:   "); display.println(engine_rpm);
  display.print("Bucket: "); display.print(bucket_angle); display.println(" deg");
  
  display.setCursor(0, 40);
  if (agent_alarm_active) {
    display.setTextColor(BLACK, WHITE); // Invert text for alarm
    display.println("! AGENT OVERRIDE !");
    display.setTextColor(WHITE, BLACK); // Reset color
  } else if (is_high_load) {
    display.println("STATUS: HIGH LOAD");
  } else {
    display.println("STATUS: NORMAL");
  }
  display.display();

  delay(2500);
}