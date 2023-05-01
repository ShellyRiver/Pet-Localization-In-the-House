/* 
   This device collects bluetooth low energy signal from tile tags and sends it to Raspberry Pi through Wi-Fi
*/

#include <WiFi.h>
#include <NimBLEDevice.h>
#include <NimBLEScan.h>
#include <NimBLEAdvertisedDevice.h>

// UUID of the tile tag, to search for target bluetooth low energy signal
#define TILE_UUID "FEED"

// Wi-Fi ssid and password
const char* ssid     = "smartmirror";
const char* password = "oooooooo";

// Raspberry Pi IP address and port
const char *raspberryPiIP = "192.168.10.33";
const int raspberryPiPort = 2333;

IPAddress local_IP(192, 168, 10, 100); // Replace with your desired static IP address
IPAddress gateway(192, 168, 10, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8); // Google DNS
IPAddress secondaryDNS(8, 8, 4, 4); // Google DNS

// Time interval to send data to Raspberry Pi
const unsigned long sendDataInterval = 10000; // 10s

// Data structure to store found Tile Tags
struct TileTag {
  String address;
  int rssi;
};
std::vector<TileTag> foundTileTags;

class MyAdvertisedDeviceCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice *advertisedDevice) {
    // Check if the advertised device has service UUIDs
    if (advertisedDevice->haveServiceUUID()) {
      // Check if the device has the target UUID
      if (advertisedDevice->getServiceUUID().toString().find(TILE_UUID) != std::string::npos) {
        TileTag tag;
        tag.address = advertisedDevice->getAddress().toString().c_str();
        tag.rssi = advertisedDevice->getRSSI();
        Serial.println(tag.address + String(tag.rssi));
        foundTileTags.push_back(tag);
      }
    }
  }
};

void setup() {
  Serial.begin(115200);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("Connecting to Wi-Fi..."));
    delay(500);
  }

  // Configure static IP address
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("Failed to configure static IP");
  }

  // Initialize BLE
  Serial.println(F("Scanning for Tile Tags..."));
  NimBLEDevice::init("");
  NimBLEScan *pBLEScan = NimBLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  static unsigned long lastSendData = 0;

  // Start scanning for BLE devices
  NimBLEScan *pBLEScan = NimBLEDevice::getScan();
  pBLEScan->start(5, false);
  pBLEScan->clearResults();
  delay(1000);

  // Check if it's time to send data to Raspberry Pi
  if (millis() - lastSendData > sendDataInterval) {
    lastSendData = millis();

    WiFiClient client;
    if (client.connect(raspberryPiIP, raspberryPiPort)) {
      // Send RSSI data to Raspberry Pi
      for (const TileTag &tag : foundTileTags) {
        String dataToSend = tag.address + ", " + String(tag.rssi);
        client.println(dataToSend);
      }
      client.stop();

      // Clear the found Tile Tags list
      foundTileTags.clear();
    } 
  }
}

