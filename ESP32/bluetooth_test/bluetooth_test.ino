#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// Set the UUID you want to search for
#define TARGET_UUID "feed"

class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    // Check if the advertised device has service UUIDs
    if (advertisedDevice.haveServiceUUID()) {
      // Check if the device has the target UUID
      if (advertisedDevice.getServiceUUID().toString().find(TARGET_UUID) != std::string::npos) {
        Serial.printf("Found Tile Tag with Address: %s, RSSI: %d\n", advertisedDevice.getAddress().toString().c_str(), advertisedDevice.getRSSI());
      }
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Scanning for Tile Tags with UUID FEED...");

  // Initialize BLE
  BLEDevice::init("");
  BLEScan *pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  // Start scanning for BLE devices
  BLEScan *pBLEScan = BLEDevice::getScan();
  pBLEScan->start(5, false);
  pBLEScan->clearResults();
  delay(1000);
}
