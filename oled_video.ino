#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const char* WIFI_SSID = "pandu";
const char* WIFI_PASSWORD = "12345678900";
constexpr uint16_t UDP_PORT = 4210;
constexpr size_t FRAME_SIZE = 1024;

Adafruit_SSD1306 display(128, 64, &Wire, -1);
WiFiUDP udp;
uint8_t packet[4 + FRAME_SIZE];
unsigned long lastFrame = 0;
unsigned long frameCounter = 0;

void showMessage(const char* line1, const String& line2 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(line1);
  display.println();
  display.println(line2);
  display.display();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  Wire.setClock(400000);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed. Check I2C address/wiring.");
    while (true) delay(1000);
  }
  showMessage("Connecting WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print('.');
  }
  if (WiFi.status() != WL_CONNECTED) {
    showMessage("WiFi FAILED", "Check SSID/password");
    Serial.println("WiFi connection failed");
    return;
  }
  if (!udp.begin(UDP_PORT)) {
    showMessage("UDP FAILED");
    Serial.println("UDP bind failed");
    return;
  }
  Serial.printf("ESP32 IP: %s | UDP port: %u\n", WiFi.localIP().toString().c_str(), UDP_PORT);
  showMessage("WAITING FOR VIDEO", WiFi.localIP().toString());
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) return;
  int len = udp.parsePacket();
  if (len <= 0) return;
  if (len != sizeof(packet)) {
    Serial.printf("Ignored UDP packet, size=%d (expected 1028)\n", len);
    while (udp.available()) udp.read();
    return;
  }
  int n = udp.read(packet, sizeof(packet));
  if (n != sizeof(packet)) return;
  if (memcmp(packet, "VID0", 4) != 0) {
    Serial.println("Ignored packet: invalid header");
    return;
  }
  memcpy(display.getBuffer(), packet + 4, FRAME_SIZE);
  display.display();
  frameCounter++;
  lastFrame = millis();
  if (frameCounter % 30 == 0) {
    Serial.printf("Displayed %lu frames, sender=%s\n", frameCounter, udp.remoteIP().toString().c_str());
  }
}
