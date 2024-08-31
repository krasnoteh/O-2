#include <Wire.h>
#include "GyverButton.h"

#define SLAVE_ADDRESS 0x08

#define left_wheel_speed_pin 6
#define right_wheel_speed_pin 5
#define left_wheel_reverse_pin A2
#define right_wheel_reverse_pin A3
#define first_button_pin 7
#define second_button_pin 8
#define first_led_pin 9
#define second_led_pin 10
#define third_led_pin 11
#define headlights_pin A0

class LedController{
  public:
  LedController(int in_pin): pin(in_pin){}
  void tick(){
    analogWrite(pin, get_brightness());
  }
  void set_mode(int new_mode){
    if (mode != new_mode){
      mode = new_mode;
      timestamp = millis();
    }
  }
  private:
  int get_brightness(){
    if (mode == 0){
      return 0;
    }
    if (mode == 1){ 
      return 255;
    }
    if (mode == 2){
      return 255 * (((millis() - timestamp)%2000)>1000);
    }
    if (mode == 3){
      return static_cast<int>(pow(sin(static_cast<float>(millis() - timestamp)/500.0), 8) * 255.0);
    }
    if (mode == 4){
      return static_cast<int>(sin(static_cast<float>(millis() - timestamp)/200.0) * 50.0) + 100;
    }
  }
  int mode = 0;
  int pin;
  uint32_t timestamp = 0;
};

byte input_message[8];
byte output_message[8];
int32_t control_data[64];
int32_t return_data[64];
bool return_is_modified[64];
bool data_latch = false;
bool back_updating = false;
int back_updating_current_index = 0;

const bool right_is_reversed = false;
const bool left_is_reversed = true;

bool hotspot_mode = false;

GButton first_button(first_button_pin);
LedController first_led(first_led_pin);


void setup() {
  Wire.begin(SLAVE_ADDRESS);
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);
  Serial.begin(9600);
  pinMode(left_wheel_speed_pin, OUTPUT);
  pinMode(right_wheel_speed_pin, OUTPUT);
  pinMode(left_wheel_reverse_pin, OUTPUT);
  pinMode(right_wheel_reverse_pin, OUTPUT);
  pinMode(first_button_pin, INPUT_PULLUP);
  pinMode(second_button_pin, INPUT_PULLUP);
  pinMode(first_led_pin, OUTPUT);
  pinMode(second_led_pin, OUTPUT);
  pinMode(third_led_pin, OUTPUT);
  pinMode(headlights_pin, OUTPUT);
}

int prev_wifi_mode = false;

void loop() {
  first_led.tick();
  if (prev_wifi_mode != control_data[3]){
    first_led.set_mode(control_data[3]);
    prev_wifi_mode = control_data[3];
  }
  
  first_button.tick();
  if (first_button.isSingle()){
    hotspot_mode ^= 1;
    SetReturnValue(1, hotspot_mode);
    Serial.println(hotspot_mode);
    first_led.set_mode(4);
  }
  if (not data_latch){
    digitalWrite(headlights_pin, control_data[4]);
    SetMoveDirection(control_data[1], control_data[2]);
  }
}

void SetLeftWheelSpeed(int wheel_speed){
  digitalWrite(left_wheel_reverse_pin, left_is_reversed ^ (wheel_speed < 0));
  analogWrite(left_wheel_speed_pin, map(abs(wheel_speed), 0, 100, 0, 255));
}

void SetRightWheelSpeed(int wheel_speed){
  digitalWrite(right_wheel_reverse_pin, right_is_reversed ^ (wheel_speed < 0));
  analogWrite(right_wheel_speed_pin, map(abs(wheel_speed), 0, 100, 0, 255));
}

void SetMoveDirection(int move_speed, int angle){
  int left_speed;
  int right_speed;
  if (angle == 0){
    left_speed = move_speed;
    right_speed = move_speed;
  }
  if (angle < 0){
    right_speed = move_speed;
    left_speed = static_cast<int>(static_cast<float>(move_speed) * (1.0 - (static_cast<float>(abs(angle)) / 100.0)));
  }
  if (angle > 0){
    left_speed = move_speed;
    right_speed = static_cast<int>(static_cast<float>(move_speed) * (1.0 - (static_cast<float>(abs(angle)) / 100.0)));
  }
  SetLeftWheelSpeed(left_speed);
  SetRightWheelSpeed(right_speed);
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
