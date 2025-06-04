#include <ArduinoBLE.h>
#include "Arduino_BMI270_BMM150.h"
#include <LiquidCrystal_I2C.h>
#include <string>

constexpr char *BLE_UUID_MESSAGE_SERVICE            = "9A48ECBA-2E92-082F-C079-9E75AAE428B1";
constexpr char *BLE_UUID_PREDICTION_CHARACTERISTIC  = "2D2F88C4-F244-5A80-21F1-EE0224E80658";
constexpr char *BLE_UUID_SENTENCE_CHARACTERISTIC    = "19B10001-E8F2-537E-4F6C-D104768A1214";

constexpr char BACKSPACE      = '*';
constexpr char DELETE         = '!';

constexpr int ROWS            = 2;
constexpr int COLS            = 16;

short fingers[6];
char c;
std::string sentence = "";
bool on = true;

LiquidCrystal_I2C lcd(0x27, COLS, ROWS);

BLEService messageService(BLE_UUID_MESSAGE_SERVICE);
BLEStringCharacteristic predictionCharacteristic(BLE_UUID_PREDICTION_CHARACTERISTIC, BLENotify, 1);
BLEStringCharacteristic sentenceCharacteristic(BLE_UUID_SENTENCE_CHARACTERISTIC, BLENotify, COLS);

void dumpData(){

  std::string readString, send;
  float x_dps, y_dps, z_dps, x_g, y_g, z_g;

  fingers[0] = analogRead(A0);
  fingers[1] = analogRead(A1);
  fingers[2] = analogRead(A2);
  fingers[3] = analogRead(A3);
  fingers[4] = analogRead(A6);
  fingers[5] = analogRead(A7);

  if(IMU.gyroscopeAvailable() && IMU.accelerationAvailable()){
    IMU.readGyroscope(x_dps, y_dps, z_dps);
    IMU.readAcceleration(x_g, y_g, z_g);

    send = std::to_string(fingers[0]) + ',' + std::to_string(fingers[1]) + ',' 
    + std::to_string(fingers[2]) + ',' + std::to_string(fingers[3]) + ',' 
    + std::to_string(fingers[4]) + ',' + std::to_string(fingers[5]) + ','
    + std::to_string(x_dps) + ',' + std::to_string(y_dps) + ',' + std::to_string(z_dps) + ',' 
    + std::to_string(x_g) + ',' + std::to_string(y_g) + ',' + std::to_string(z_g);

    Serial.println(send.c_str());
    Serial.flush();
  }

  on = !on;
  digitalWrite(LED_BUILTIN, on);
  delay(100);

  while(Serial.available() > 0){
    c = Serial.read();
    readString += c;
  }

  if(readString.length() >= 2 && readString.find(',') != std::string::npos){
    lcd.clear();
    lcd.home();

    lcd.setCursor(14, 1);
    lcd.print(char(readString[0] - 'a' + 'A'));
    lcd.setCursor(15, 1);
    lcd.print(readString[0]);

    if(readString.substr(2, readString.length() - 2).length() == 1){
      c = readString[2];

      if(c == BACKSPACE ){
        if(sentence.length() > 0)
          sentence.pop_back();

      }else if(c == DELETE){
        sentence = "";

      }else{
        sentence += c;
      }
    }

    lcd.setCursor(0, 0);
    predictionCharacteristic.writeValue(readString.substr(0, 1).c_str());

    if(sentence.length() && sentence[sentence.length() - 1] == ' '){
      lcd.print((sentence.substr(0, sentence.length() - 1) + '_').c_str());
      sentenceCharacteristic.writeValue((sentence.substr(0, sentence.length() - 1) + '_').c_str());

    }else{
      lcd.print(sentence.c_str());
      sentenceCharacteristic.writeValue(sentence.c_str());
    }
  }
}

void setup() {

  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);
  Serial.println("Started");

  if(!IMU.begin()){
    Serial.println("IMU failed to initialize");
    while(1);
  }

  Serial.println("IMU ON");

  lcd.init();
  lcd.backlight();
  lcd.home();
  lcd.print("Waiting...");

  BLE.begin();
  BLE.setDeviceName("Nano_33_BLE");
  BLE.setLocalName("Nano_33_BLE");

  BLE.setAdvertisedService(messageService);
  messageService.addCharacteristic(predictionCharacteristic);
  messageService.addCharacteristic(sentenceCharacteristic);

  BLE.addService(messageService);
  predictionCharacteristic.writeValue("");
  sentenceCharacteristic.writeValue("");

  BLE.advertise();
  delay(1000);
}

void loop() {
  lcd.home();
  BLEDevice central = BLE.central();

  dumpData();

  if (central) {
    lcd.home();
    lcd.print("Connected");

    lcd.setCursor(0, 1);
    lcd.print(central.address());

    while (central.connected()) {
      dumpData();
    }
    lcd.clear();
    lcd.home();
  }
}