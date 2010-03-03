#include <OneWire.h>
#include <DallasTemperature.h>

/* DS18S20 Temperature chip i/o */

OneWire  ds(8); 
DallasTemperature sensors(&ds);

DeviceAddress insideThermometer = { 0x10, 0xE7, 0x77, 0xD3, 0x01, 0x08, 0x00, 0x3F };

void printTemperature(DeviceAddress deviceAddress)
{
  float tempC = sensors.getTempC(deviceAddress);
  Serial.print("Temp C: ");
  Serial.print(tempC);
  Serial.print(" Temp F: ");
  Serial.println(DallasTemperature::toFahrenheit(tempC)); // Converts tempC to Fahrenheit
}

void setup(void) {
  Serial.begin(9600);
  sensors.begin();
}

void loop(void) {
  if (millis() < 2000)
  {
    return;
  }
  
  printTemperature(insideThermometer);
  
  byte i;
  byte present = 0;
  byte data[12];
  byte addr[8];
  
  if ( !ds.search(addr)) {
    Serial.print("\nNo more addresses.\n");
    ds.reset_search();
    delay(250);
    return;
  }
  
  Serial.print("\nR=");
  for( i = 0; i < 8; i++) {
    Serial.print(addr[i], HEX);
    Serial.print(" ");
  }

  if ( OneWire::crc8( addr, 7) != addr[7]) {
      Serial.print("  CRC is not valid!\n");
      return;
  }
  
  if ( addr[0] != 0x10) {
      Serial.print("\nDevice is not a DS18S20 family device.\n");
      return;
  }

  // The DallasTemperature library can do all this work for you!

  ds.reset();
  ds.select(addr);
  ds.write(0x44,1);         // start conversion, with parasite power on at the end
  
  delay(1000);     // maybe 750ms is enough, maybe not
  // we might do a ds.depower() here, but the reset will take care of it.
  
  present = ds.reset();
  ds.select(addr);    
  ds.write(0xBE);         // Read Scratchpad

  Serial.print("\nP=");
  Serial.print(present,HEX);
  Serial.print(" ");
  for ( i = 0; i < 9; i++) {           // we need 9 bytes
    data[i] = ds.read();
    Serial.print(data[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
  Serial.print(" CRC=");
  Serial.print( OneWire::crc8( data, 8), HEX);
  Serial.println();
}
