#include <Wire.h>
#include "GyverButton.h"

#define SLAVE_ADDRESS 0x09

#define motor_pin 5
#define sensor_pin A0

byte input_message[8];
byte output_message[8];
int32_t control_data[64];
int32_t return_data[64];
bool return_is_modified[64];
bool data_latch = false;
bool back_updating = false;
int back_updating_current_index = 0;

bool in_cycle = false;
bool was_one_on_sensor = false;
int32_t previous_value = 0;

void setup() {
  Wire.begin(SLAVE_ADDRESS);
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);
  Serial.begin(9600);
  pinMode(motor_pin, OUTPUT);
}


void loop() {
  if (not data_latch){
    if (previous_value != control_data[1]){
      previous_value = control_data[1];
      in_cycle = true;
      was_one_on_sensor = false;
    }
    bool sensor_value = digitalRead(sensor_pin);
    if (sensor_value and !was_one_on_sensor){
      was_one_on_sensor = true;
    }
    if (!sensor_value and was_one_on_sensor){
      in_cycle = false;
    }
    digitalWrite(motor_pin, in_cycle);
    delay(1);
  }
}

void ReadInputMessage(){
  int i = 0;
  Wire.read();
  while (Wire.available()) {
    byte c = Wire.read();
    input_message[i] = c;
    i++;
  }
}

void ParceInputMessage(){
  if (input_message[0] == 1){
    int index = static_cast<int>(input_message[1]);
    int32_t value = 0;
    value |= static_cast<int32_t>(input_message[2]);
    value |= (static_cast<int32_t>(input_message[3]) << 8);
    value |= (static_cast<int32_t>(input_message[4]) << 16);
    value |= (static_cast<int32_t>(input_message[5]) << 24);
    control_data[index] = value;
  }
  if (input_message[0] == 3){
    back_updating = true;
    back_updating_current_index = 0;
    BackupdatingStep();
  }
  if (input_message[0] == 5){
    data_latch = true;
  }
  if (input_message[0] == 6){
    data_latch = false;
  }
}

void BackupdatingStep(){
  while(true){
    if (back_updating_current_index == 64){
      back_updating = false;
      output_message[0] = 4;
      return;
    }
    if (return_is_modified[back_updating_current_index]){
      output_message[0] = 2;
      output_message[1] = static_cast<byte>(back_updating_current_index);
      output_message[2] = static_cast<byte>((return_data[back_updating_current_index]) & 255);
      output_message[3] = static_cast<byte>((return_data[back_updating_current_index] >> 8) & 255);
      output_message[4] = static_cast<byte>((return_data[back_updating_current_index] >> 16) & 255);
      output_message[5] = static_cast<byte>((return_data[back_updating_current_index] >> 24) & 255);

      return_is_modified[back_updating_current_index] = false;
      return;
    }
    else{
      back_updating_current_index++;
    }
  }
}

void SetReturnValue(int index, int32_t value){
  return_data[index] = value;
  return_is_modified[index] = true;
}

void receiveEvent(int howMany) {
  if (howMany == 1){
    Wire.read();
    return;
  }
  ReadInputMessage();
  ParceInputMessage();
}

void requestEvent() {
  Wire.write(output_message, 8);
  BackupdatingStep();
}
