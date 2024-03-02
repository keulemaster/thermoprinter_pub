// Verkabelung:
//
//     ------------
//  5V |1   Ö   14| GND
//     |2       13| V BATT
//     |3       12| RASPI HIGH/LOW
//     |4       11|
//     |5       10|
// LED |6        9|
//     |7        8|
//     ------------

#include <Arduino.h>
#include "SoftwareSerial.h"

#define RED 3

#define V_LEER 3800 //zellenspannung Raspi aus
#define V_LAST 3500 //zellenspannung in betrieb

void setup() {

  // rote LED
  pinMode(RED, OUTPUT);

  // spannung der batt
  pinMode(A0, INPUT); 

  //LOW or HIGH vom Raspi, zeigt an ob Raspi läuft oder nicht
  pinMode(A1, INPUT); 
}

void loop() {
  double sensorValue = analogRead(A0);
  double voltage = map(sensorValue, 0, 1023, 0, 5000);

  // wenn raspi AUS dann muss die spannung unter V_LEER sein um zu leuchten
  if (!digitalRead(A1) && voltage < V_LEER) {
    digitalWrite(RED, HIGH);
  }
  else {
    digitalWrite(RED, LOW);
  }
  
  // wenn raspi EIN dann muss die spannung unter V_LAST sein um zu leuchten
  if (digitalRead(A1) && voltage < V_LAST) {
    digitalWrite(RED, HIGH);
  }
  else {
    digitalWrite(RED, LOW);
  }   
}
