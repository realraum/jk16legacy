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
//movement is reported if during IR_SAMPLE_DURATION at least IR_TRESHOLD ir signals are detectd
#define IR_SAMPLE_DURATION 20000
#define IR_TRESHOLD 13000
//duration PanicButton needs to be pressed before status change occurs (i.e. for two PanicButton Reports, the buttons needs to be pressed 1000 cycles, releases 1000 cycles and again pressed 1000 cycles)
#define PB_TRESHOLD 1000

OneWire  onewire(ONE_WIRE_PIN);
DallasTemperature dallas_sensors(&onewire);
DeviceAddress onShieldTemp = { 0x10, 0xE7, 0x77, 0xD3, 0x01, 0x08, 0x00, 0x3F };

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
  Serial.println(tempC);
  //Serial.print(" Temp F: ");
  //Serial.println(DallasTemperature::toFahrenheit(tempC)); // Converts tempC to Fahrenheit
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
  
  onewire.reset();
  onewire.reset_search();
  dallas_sensors.begin();
  //in case we change temp sensor:
  if (!dallas_sensors.getAddress(onShieldTemp, 0)) 
    Serial.println("Unable to find address for Device 0"); 
  dallas_sensors.setResolution(onShieldTemp, 9);
  
  Serial.begin(9600);
}

unsigned int ir_time=IR_SAMPLE_DURATION;
unsigned int ir_count=0;
boolean pb_last_state=0;
boolean pb_state=0;
boolean pb_postth_state=0;
unsigned int pb_time=0;

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
      Serial.println("movement");
    ir_time=IR_SAMPLE_DURATION;
    ir_count=0;
  }
  
  if (pb_state == pb_last_state && pb_time >= PB_TRESHOLD)
  {
    if (pb_state && ! pb_postth_state)
    {   
      pb_postth_state=1;
      Serial.println("PanicButton");
    }
    else if (!pb_state)
      pb_postth_state=0;
  }
  else if (pb_state != pb_last_state)
  {
    pb_time=0;
    pb_last_state=pb_state;
  }
    
  if(Serial.available()) {
    char command = Serial.read();
    
    if(command == 'q')
      send_frame(words[A1_ON]);
    else if(command == 'a')
      send_frame(words[A1_OFF]);
    else if(command == 'w')
      send_frame(words[A2_ON]);
    else if(command == 's')
      send_frame(words[A2_OFF]);

    else if(command == 'e')
      send_frame(words[B1_ON]);
    else if(command == 'd')
      send_frame(words[B1_OFF]);
    else if(command == 'r')
      send_frame(words[B2_ON]);
    else if(command == 'f')
      send_frame(words[B2_OFF]);

    else if(command == 't')
      send_frame(words[C1_ON]);
    else if(command == 'g')
      send_frame(words[C1_OFF]);
    else if(command == 'z')
      send_frame(words[C2_ON]);
    else if(command == 'h')
      send_frame(words[C2_OFF]);

    else if(command == 'u')
      send_frame(words[D1_ON]);
    else if(command == 'j')
      send_frame(words[D1_OFF]);
    else if(command == 'i')
      send_frame(words[D2_ON]);
    else if(command == 'k')
      send_frame(words[D2_OFF]);
    else if(command == 'T')
      printTemperature(onShieldTemp);

    else
      Serial.println("Error: unknown command");
  }
}
