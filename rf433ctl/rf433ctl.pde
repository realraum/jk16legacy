#include <avr/io.h>
#include <avr/interrupt.h>
#include <inttypes.h>
#include <OneWire.h>
#include <DallasTemperature.h>

//********************************************************************//

#define RF_DATA_OUT_PIN 13
#define IR_MOVEMENT_PIN 9
#define ONE_WIRE_PIN 8
#define PANIC_BUTTON_PIN 7
#define BLUELED_PWM_PIN 6
#define BLUELED2_PWM_PIN 10
#define PHOTO_ANALOGPIN 0
//movement is reported if during IR_SAMPLE_DURATION at least IR_TRESHOLD ir signals are detectd
#define IR_SAMPLE_DURATION 15000
#define IR_TRESHOLD 10000
//duration PanicButton needs to be pressed before status change occurs (i.e. for two PanicButton Reports, the buttons needs to be pressed 1000 cycles, releases 1000 cycles and again pressed 1000 cycles)
#define PB_TRESHOLD 1000
#define PHOTO_SAMPLE_INTERVAL 4000

OneWire  onewire(ONE_WIRE_PIN);
DallasTemperature dallas_sensors(&onewire);
DeviceAddress onShieldTemp = { 0x10, 0xE7, 0x77, 0xD3, 0x01, 0x08, 0x00, 0x3F };
#define TEMPC_OFFSET_ARDUINO_GENEREATED_HEAT -4.0

typedef struct {
  byte offset;
  byte state;
} rf_bit_t;

// offset is number of alphas (0.08ms)

const rf_bit_t zero_bit[] = { {  4, 1 },
                              { 16, 0 },
                              { 20, 1 },
                              { 32, 0 },
                              {  0, 0 } };

const rf_bit_t one_bit[] = { { 12, 1 },
                             { 16, 0 },
                             { 28, 1 },
                             { 32, 0 },
                             {  0, 0 } };

const rf_bit_t float_bit[] = { {  4, 1 },
                               { 16, 0 },
                               { 28, 1 },
                               { 32, 0 },
                               {  0, 0 } };

const rf_bit_t sync_bit[] = { {   4, 1 },
                              { 128, 0 },
                              {   0, 0 } };

typedef enum { ZERO = 0, ONE , FLOAT , SYNC } adbit_t;
typedef byte ad_bit_t;
#define WORD_LEN 13
typedef ad_bit_t word_t[WORD_LEN];

const rf_bit_t* bit_defs[] = { zero_bit, one_bit, float_bit, sync_bit };

byte alpha_cnt = 0;
byte bit_cnt = 0;
byte chunk_cnt = 0;
byte word_cnt = 0;
const ad_bit_t* current_word;
byte volatile frame_finished = 1;

#define FRAME_LEN 8

#define A1_ON  0
#define A1_OFF 1
#define A2_ON  2
#define A2_OFF 3

#define B1_ON  4
#define B1_OFF 5
#define B2_ON  6
#define B2_OFF 7

#define C1_ON  8
#define C1_OFF 9
#define C2_ON  10
#define C2_OFF 11

#define D1_ON  12
#define D1_OFF 13
#define D2_ON  14
#define D2_OFF 15

const word_t words[]  = { 
{ ZERO,  ZERO,  FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // A1_ON
{ ZERO,  ZERO,  FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // A1_OFF
{ ZERO,  ZERO,  FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // A2_ON
{ ZERO,  ZERO,  FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // A2_OFF

{ FLOAT, ZERO,  FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // B1_ON
{ FLOAT, ZERO,  FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // B1_OFF
{ FLOAT, ZERO,  FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // B2_ON
{ FLOAT, ZERO,  FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // B2_OFF

{ ZERO,  FLOAT, FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // C1_ON
{ ZERO,  FLOAT, FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // C1_OFF
{ ZERO,  FLOAT, FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // C2_ON
{ ZERO,  FLOAT, FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // C2_OFF

{ FLOAT, FLOAT, FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // D1_ON
{ FLOAT, FLOAT, FLOAT, FLOAT, ZERO,  ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }, // D1_OFF
{ FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, FLOAT, SYNC }, // D2_ON
{ FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO, FLOAT, FLOAT, ZERO,  SYNC }  // D2_OFF
};


//********************************************************************//

void start_timer()
{
  // timer 1: 2 ms
  TCCR1A = 0;                    // prescaler 1:8, WGM = 4 (CTC)
  TCCR1B = 1<<WGM12 | 1<<CS11;   // 
  OCR1A = 159;        // (1+159)*8 = 1280 -> 0.08ms @ 16 MHz -> 1*alpha
//  OCR1A = 207;        // (1+207)*8 = 1664 -> 0.104ms @ 16 MHz -> 1*alpha
  TCNT1 = 0;          // reseting timer
  TIMSK1 = 1<<OCIE1A; // enable Interrupt
}

void stop_timer() // stop the timer
{
  // timer1
  TCCR1B = 0; // no clock source
  TIMSK1 = 0; // disable timer interrupt
}

void init_word(const word_t w)
{
  current_word = w;
  alpha_cnt = 0;
  chunk_cnt = 0;
  bit_cnt = 0;

  if(bit_defs[current_word[bit_cnt]][chunk_cnt].state)
    digitalWrite(RF_DATA_OUT_PIN, HIGH);
  else
    digitalWrite(RF_DATA_OUT_PIN, LOW);

  start_timer();
}

ISR(TIMER1_COMPA_vect)
{
  alpha_cnt++;
  if(alpha_cnt < bit_defs[current_word[bit_cnt]][chunk_cnt].offset)
    return;

  chunk_cnt++;
  if(bit_defs[current_word[bit_cnt]][chunk_cnt].offset != 0) {
    if(bit_defs[current_word[bit_cnt]][chunk_cnt].state)
      digitalWrite(RF_DATA_OUT_PIN, HIGH);
    else
      digitalWrite(RF_DATA_OUT_PIN, LOW);
    return;
  }
  
  bit_cnt++;
  if(bit_cnt < WORD_LEN) {
    alpha_cnt = 0;
    chunk_cnt = 0;
    if(bit_defs[current_word[bit_cnt]][chunk_cnt].state)
      digitalWrite(RF_DATA_OUT_PIN, HIGH);
    else
      digitalWrite(RF_DATA_OUT_PIN, LOW);
    return;
  }
  stop_timer();
  digitalWrite(RF_DATA_OUT_PIN, LOW);

  word_cnt++;
  if(word_cnt < FRAME_LEN)
    init_word(current_word);

  frame_finished = 1;
}

//***********//


void send_frame(const word_t w)
{
  word_cnt = 0;
  frame_finished = 0;
  init_word(w);

  for(;;)
    if(frame_finished)
      break;

  Serial.println("Ok");
}

//********************************************************************//

void printTemperature(DeviceAddress deviceAddress)
{
  dallas_sensors.requestTemperatures();
  float tempC = dallas_sensors.getTempC(deviceAddress);
  Serial.print("Temp C: ");
  Serial.println(tempC TEMPC_OFFSET_ARDUINO_GENEREATED_HEAT);
  //Serial.print(" Temp F: ");
  //Serial.println(DallasTemperature::toFahrenheit(tempC)); // Converts tempC to Fahrenheit
}

//********************************************************************//

unsigned int light_level_mean_ = 0;
unsigned int light_sample_time_ = 0;

void updateLightLevel(unsigned int pin)
{
  light_sample_time_++;
  if (light_sample_time_ < PHOTO_SAMPLE_INTERVAL)
    return;
  light_sample_time_ = 0;
  
  unsigned int value = analogRead(pin);
  if (value == light_level_mean_)
    return;
  
  unsigned int diff = abs(value - light_level_mean_);
  if (light_level_mean_ < 6 || diff > 250)
    light_level_mean_ = value;
  else
      light_level_mean_=(unsigned int) ( ((float) light_level_mean_) * 0.98 + ((float)value)*0.02 );
}

void printLightLevel()
{
  Serial.print("Photo: ");
  Serial.println(light_level_mean_);
}

//********************************************************************//

unsigned long wm_start_=0;
bool wait_millis(unsigned long ms)
{
  if (wm_start_ > 0)
  {
    if (millis() < wm_start_ || millis() > wm_start_+ ms)
    {
      wm_start_=0;
      return false;
    }
    else
      return true;
  }
  else
  {
    wm_start_=millis();
    return true;
  }
}

unsigned int flash_led_time_=0;
unsigned int flash_led_brightness_=256;
unsigned int flash_led_delay_=8;
void calculate_led_level(unsigned int pwm_pin)
{
  if (flash_led_time_ == 0)
    return;
  if (wait_millis(flash_led_delay_))
    return;
  flash_led_time_--;
  int c = abs(sin(float(flash_led_time_) / 100.0)) * flash_led_brightness_;
  analogWrite(BLUELED_PWM_PIN,c);
  analogWrite(BLUELED2_PWM_PIN,c);
}

void flash_led(unsigned int times, unsigned int brightness_divisor, unsigned int delay_divisor)
{
  unsigned int new_flash_led_brightness = 256 / brightness_divisor;
  unsigned int new_flash_led_delay = 8 / delay_divisor;
  if (flash_led_time_ == 0 || new_flash_led_brightness > flash_led_brightness_)
    flash_led_brightness_=new_flash_led_brightness;
  if (flash_led_time_ == 0 || new_flash_led_delay < flash_led_delay_)
    flash_led_delay_=new_flash_led_delay;
  flash_led_time_ += 314*times;
}

//********************************************************************//

void setup()
{
  pinMode(RF_DATA_OUT_PIN, OUTPUT);
  digitalWrite(RF_DATA_OUT_PIN, LOW);
  pinMode(IR_MOVEMENT_PIN, INPUT);      // set pin to input
  digitalWrite(IR_MOVEMENT_PIN, LOW);  // turn off pullup resistors  
  pinMode(PANIC_BUTTON_PIN, INPUT);      // set pin to input
  digitalWrite(PANIC_BUTTON_PIN, HIGH);  // turn on pullup resistors 
  analogWrite(BLUELED_PWM_PIN,0);

  Serial.begin(9600);
  
  onewire.reset();
  onewire.reset_search();
  dallas_sensors.begin();
  //in case we change temp sensor:
  if (!dallas_sensors.getAddress(onShieldTemp, 0)) 
    Serial.println("Error: Unable to find address for Device 0"); 
  dallas_sensors.setResolution(onShieldTemp, 9);  
}

unsigned int ir_time=IR_SAMPLE_DURATION;
unsigned int ir_count=0;
boolean pb_last_state=0;
boolean pb_state=0;
boolean pb_postth_state=0;
unsigned int pb_time=0;

void sensorEchoCommand(char command)
{
  Serial.print("Sensor ");
  Serial.print(command);
  Serial.print(": ");
}

void loop()
{
  ir_time--;
  ir_count += (digitalRead(IR_MOVEMENT_PIN) == HIGH);

  if (pb_time < PB_TRESHOLD)
    pb_time++;
  pb_state=(digitalRead(PANIC_BUTTON_PIN) == LOW);
  
  if (ir_time == 0)
  {
    if (ir_count >= IR_TRESHOLD)
    {
      flash_led(1,8,1);
      Serial.println("movement");
    }
    ir_time=IR_SAMPLE_DURATION;
    ir_count=0;
  }
  
  if (pb_state == pb_last_state && pb_time >= PB_TRESHOLD)
  {
    if (pb_state && ! pb_postth_state)
    {   
      pb_postth_state=1;
      Serial.println("PanicButton");
      flash_led(7,1,2);
    }
    else if (!pb_state)
      pb_postth_state=0;
  }
  else if (pb_state != pb_last_state)
  {
    pb_time=0;
    pb_last_state=pb_state;
  }
  
  updateLightLevel(PHOTO_ANALOGPIN);
  calculate_led_level(BLUELED_PWM_PIN);
  
  if(Serial.available()) {
    char command = Serial.read();
    
    if(command == 'A')
      send_frame(words[A1_ON]);
    else if(command == 'a')
      send_frame(words[A1_OFF]);
    else if(command == 'B')
      send_frame(words[A2_ON]);
    else if(command == 'b')
      send_frame(words[A2_OFF]);

    else if(command == 'C')
      send_frame(words[B1_ON]);
    else if(command == 'c')
      send_frame(words[B1_OFF]);
    else if(command == 'D')
      send_frame(words[B2_ON]);
    else if(command == 'd')
      send_frame(words[B2_OFF]);

    else if(command == 'E')
      send_frame(words[C1_ON]);
    else if(command == 'e')
      send_frame(words[C1_OFF]);
    else if(command == 'F')
      send_frame(words[C2_ON]);
    else if(command == 'f')
      send_frame(words[C2_OFF]);

    else if(command == 'G')
      send_frame(words[D1_ON]);
    else if(command == 'g')
      send_frame(words[D1_OFF]);
    else if(command == 'H')
      send_frame(words[D2_ON]);
    else if(command == 'h')
      send_frame(words[D2_OFF]);
    else if(command == 'T')
    {
      sensorEchoCommand(command);
      printTemperature(onShieldTemp);
    }
    else if(command == 'P')
    {
      sensorEchoCommand(command);
      printLightLevel();
    }
    else
      Serial.println("Error: unknown command");
  }
}
