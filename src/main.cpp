#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
Adafruit_MPU6050 mpu;

const int potPin = 32;
const int pinSuhu = 34;
const float BETA = 3950;

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

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT Broker...");
    String clientId = "TerraCortex-EX01-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT!");
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
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); 

  // 1. Read Sensors - Updated mapping sesuai saran Putra
  int potValue = analogRead(potPin);
  float pressure_bar = map(potValue, 0, 4095, 120, 350); 

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  float imu_vibration = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z)) / 9.81;

  int nilaiAnalogSuhu = analogRead(pinSuhu);
  float oil_temp = 1 / (log(1 / (4095. / max(nilaiAnalogSuhu, 1) - 1)) / BETA + 1.0 / 298.15) - 273.15;

  // 2. Generate dynamic engine_rpm dan bucket_angle berbasis pressure
  bool is_high_load = (pressure_bar >= 285.0);
  int engine_rpm = is_high_load ? map((int)pressure_bar, 285, 350, 1750, 1900) : map((int)pressure_bar, 120, 284, 1100, 1300);
  int bucket_angle = is_high_load ? map((int)pressure_bar, 285, 350, 70, 85) : map((int)pressure_bar, 120, 284, 30, 45);

  // 3. Build JSON Payload - Format minimal untuk AI Pipeline
  String payload = "{";
  payload += "\"excavator_id\": \"XCMG-EX-01\",";
  payload += "\"timestamp\": " + String(millis()) + ","; 
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
  // Display status sederhana
  if (is_high_load) {
    display.println("STATUS: HIGH LOAD");
    display.println("Waiting AI analysis...");
  } else {
    display.println("STATUS: NORMAL");
  }
  display.display();

  delay(2500);
}