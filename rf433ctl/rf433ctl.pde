#include <avr/io.h>
#include <avr/interrupt.h>
#include <inttypes.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <IRremote.h>

//********************************************************************//

#define RF_DATA_OUT_PIN 13
#define IR_MOVEMENT_PIN 9
#define IR_MOVEMENT_PIN2 12
#define ONE_WIRE_PIN 8
#define PANIC_BUTTON_PIN 7
#define PANICLED_PWM_PIN 6
#define BLUELED_PWM_PIN 11
#define PHOTO_ANALOGPIN 0
//movement is reported if during IR_SAMPLE_DURATION at least IR_TRESHOLD ir signals are detectd
#define IR_SAMPLE_DURATION 6000
#define IR_TRESHOLD 5900
//duration PanicButton needs to be pressed before status change occurs (i.e. for two PanicButton Reports, the buttons needs to be pressed 1000 cycles, releases 1000 cycles and again pressed 1000 cycles)
#define PB_TRESHOLD 1000
#define PHOTO_SAMPLE_INTERVAL 4000
#define IRREMOTE_SEND_PIN 3   //hardcoded in library
//WARNING IRremote Lib uses TCCR2

OneWire  onewire(ONE_WIRE_PIN);
DallasTemperature dallas_sensors(&onewire);
DeviceAddress onShieldTemp = { 0x10, 0xE7, 0x77, 0xD3, 0x01, 0x08, 0x00, 0x3F };
IRsend irsend;
#define TEMPC_OFFSET_ARDUINO_GENEREATED_HEAT

//********************************************************************//
// IR Codes, 32 bit, NEC
const int YAMAHA_CODE_BITS = 32;
const unsigned long int YAMAHA_CODE_BASE = 0x0000000005EA10000;

const char YAMAHA_POWER_TOGGLE =0xF8; //Power On/Off
const char YAMAHA_POWER_OFF =0x78; //Power Off !!!
const char YAMAHA_SLEEP =0xEA; //Toggle Sleep 120/90/60/30min or Off

const char YAMAHA_CD =0xA8; //Input CD
const char YAMAHA_TUNER =0x68; //Input Tuner
const char YAMAHA_TAPE =0x18; //Input Toggle Tape/CD
const char YAMAHA_DVD_SPDIF =0xE8; //Input Toggle DVD Auto / DVD Analog
const char YAMAHA_SAT_SPDIFF =0x2A; //Input Toggle Sat-DTV Auto / Sat-DTV Analog
const char YAMAHA_AUX =0xAA;  //Input AUX (mode)
const char YAMAHA_VCR =0xF0; //Input VCR
const char YAMAHA_EXT51DEC =0xE1; //Input Ext. Decoder On/Off

const char YAMAHA_TUNER_PLUS =0x08; //Tuner Next Station 1-7  (of A1 - E7)
const char YAMAHA_TUNER_MINUS =0x88; //Tuner Prev Station 1-7  (of A1 - E7)
const char YAMAHA_TUNER_ABCDE =0x48; //Tuner Next Station Row A-E (of A1 - E7)

const char YAMAHA_MUTE =0x38;
const char YAMAHA_VOLUME_UP =0x58;
const char YAMAHA_VOLUME_DOWN =0xD8;

//const char YAMAHA_FRONT_LEVEL_P =0x01;  //no function
//const char YAMAHA_FRONT_LEVEL_M =0x81; //no function
//const char YAMAHA_CENTRE_LEVEL_P =0x41;  //no function
//const char YAMAHA_CENTRE_LEVEL_M =0xC1; //no function
//const char YAMAHA_REAR_LEVEL_P =0x7A; //no function
//const char YAMAHA_REAR_LEVEL_M =0xFA; //no function
const char YAMAHA_PLUS =0x4A;  //unteres Steuerkreuz: Taste Rechts (Plus)
const char YAMAHA_MINUS =0xCA; //unteres Steuerkreuz: Taste Links (Minus)
const char YAMAHA_MENU =0x39; // Menu: Settings
const char YAMAHA_TEST =0xA1; // Test Sounds
const char YAMAHA_TIME_LEVEL =0x19; //Settings for Delay, Subwfs, Right Surround, Left Surround, Center
const char YAMAHA_TIME_LEVEL2 =0x61; //(also) Settings for Delay, Subwfs, Right Surround, Left Surround, Center
const char YAMAHA_TIME_LEVEL3 =0x99; //(also) Settings for Delay, Subwfs, Right Surround, Left Surround, Center

const char YAMAHA_EFFECT_TOGGLE =0x6A; //Effect Toggle On/Off
const char YAMAHA_PRG_DOWN =0x9A; //Effect/DSP Programm Toggle in down direction
const char YAMAHA_PRG_UP =0x1A; //Effect/DSP Programm Toggle in up direction
const char YAMAHA_EFFECT1 =0x31; //Effect TV Sports
const char YAMAHA_EFFECT2 =0x71; //Effect Rock Concert
const char YAMAHA_EFFECT3 =0xB1;  //Effect Disco
const char YAMAHA_EFFECT4 =0xD1;  //Mono Movie
const char YAMAHA_EFFECT5 =0x91; //Effect Toggle 70mm Sci-Fi / 70mm Spectacle
const char YAMAHA_EFFECT6 =0x51; //Effect Toggle 70mm General / 70mm Adventure
const char YAMAHA_P5 =0xFB; //P5 PRT (1 Main Bypass)? (1587674115)

//********************************************************************//

#define TIMER_RUNNING (TIMSK1 & (1<<OCIE1A))

void start_timer()
{
  // timer 1: 2 ms
  TCCR1A = 0;                    // prescaler 1:8, WGM = 4 (CTC)
  TCCR1B = 1<<WGM12 | 1<<CS11;   //
//  OCR1A = 39;        // (1+39)*8 = 320 -> 0.02ms @ 16 MHz -> 1*alpha
//default: alpha=0.08
  OCR1A = 159;        // (1+159)*8 = 1280 -> 0.08ms @ 16 MHz -> 1*alpha
//  OCR1A = 154;        // (1+154)*8 = 1240 -> 0.0775ms @ 16 MHz -> 1*alpha
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

#define NUM_REPEAT_SIGNAL 8
#define RF_SIGNAL_BYTES 3
#define RF_SIGNAL_BITS RF_SIGNAL_BYTES * 8

typedef struct {
  byte duration_short_pulse;  //mulitple of 0.08ms, should be === 0 (mod 4)
  byte short_mult;
  byte long_mult;
  byte sync_mult;
  byte signal[RF_SIGNAL_BYTES];  //24bit signal info, excluding sync signal (short 1 followed by long pause (~128*0.08ms))
                            //for each bit: 0 means 1/4 Tau high followed by 3/4 Tau low;    1 means 3/4 Tau high followed by 1/4 Tau low
} rf_signal;

rf_signal current_signal = {6, 1, 3, 31, {0,0,0}};

typedef struct {
  byte atime; // time counter
  byte bit;  //index for current bit
  byte repeatc; //downward couner of repetition
  byte state; // current output to RF Pin (position within the bit)
} rf_state;

rf_state current_state = { 0, 0, 0, 0};
int rf_num_transmissions_to_acknowledge = 0;

#define CURRENT_BIT_CNT (RF_SIGNAL_BITS - current_state.bit - 1)
#define CURRENT_BIT (( current_signal.signal[ CURRENT_BIT_CNT/8] >> (CURRENT_BIT_CNT % 8)  )& 1)
#define RF_TIME_SHORT (current_signal.short_mult * current_signal.duration_short_pulse)
#define RF_TIME_LONG (current_signal.long_mult * current_signal.duration_short_pulse)
#define RF_TIME_SNYC (current_signal.sync_mult * current_signal.duration_short_pulse)
#define RF_OFF digitalWrite(RF_DATA_OUT_PIN, HIGH)
#define RF_ON digitalWrite(RF_DATA_OUT_PIN, LOW)
ISR(TIMER1_COMPA_vect)
{
  if ( current_state.state || current_state.bit || current_state.repeatc || current_state.atime)
  {
    if (current_state.atime)
    {
       current_state.atime--;
    }
    //atime ran out
    else if (current_state.state) //was in state 1 or 2
    {
      RF_OFF;  //stop sending
      if (current_state.state == 2) //aka sync
        current_state.atime=RF_TIME_SNYC;
      else
        current_state.atime=CURRENT_BIT?
           RF_TIME_SHORT
          :RF_TIME_LONG;
      current_state.state=0;
    } 
    else if  (current_state.bit)  //still more than 0 bits to do
    {
      current_state.bit--;
      current_state.state=1;
      current_state.atime=CURRENT_BIT?
           RF_TIME_LONG
          :RF_TIME_SHORT;
      RF_ON;  //start sending
    }
    else if (current_state.repeatc) 
    {
      current_state.bit=RF_SIGNAL_BITS;
      current_state.repeatc--;
      current_state.state=2;
      //start sync (short pulse followed by long pause)
      RF_ON;
      current_state.atime=RF_TIME_SHORT;
    }
  }
  else
  {
    stop_timer();
    RF_OFF;
    rf_num_transmissions_to_acknowledge++;
  }
}
//********************************************************************//

void serial_read_send_rf_cmd()
{
  while (TIMER_RUNNING)
  {}
  for (byte chr=0; chr < 3; chr++)
  {
    while (!Serial.available())
    {}
    current_signal.signal[chr]=Serial.read();
  }
  current_state.repeatc=NUM_REPEAT_SIGNAL;
  start_timer();
}

void send_rf_cmd(const char sr[])
{
  while (TIMER_RUNNING)
  {}
  for (byte chr=0; chr < 3; chr++)
  {
    current_signal.signal[chr]=sr[chr];
  }
  current_state.repeatc=NUM_REPEAT_SIGNAL;
  start_timer();
}

void check_frame_done()
{
  while (rf_num_transmissions_to_acknowledge > 0)
  {
    rf_num_transmissions_to_acknowledge--;
    Serial.println("Ok");
  }
}

//********************************************************************//

void printTemperature(DeviceAddress deviceAddress)
{
  dallas_sensors.requestTemperatures();
  float tempC = dallas_sensors.getTempC(deviceAddress);
  //Serial.print("Temp C: ");
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
  if (diff > 100)
    light_level_mean_ = value;
  else
      light_level_mean_=(unsigned int) ( ((float) light_level_mean_) * 0.90 + ((float)value)*0.10 );
}

void printLightLevel()
{
  //Serial.print("Photo: ");
  Serial.println(light_level_mean_);
}

//********************************************************************//

unsigned long wm_start_[3]={0,0,0};
bool wait_millis(unsigned long *start_time, unsigned long ms)
{
  if (ms == 0)
    return false;
  else if (*start_time > 0)
  {
    if (millis() < *start_time || millis() > (*start_time) + ms)
    {
      *start_time = 0;
      return false;
    }
    else
      return true;
  }
  else
  {
    *start_time=millis();
    return true;
  }
}
#define NUM_LEDS 2
char flash_led_pins_[NUM_LEDS]={BLUELED_PWM_PIN,PANICLED_PWM_PIN};
unsigned int flash_led_time_[3]={0,0,0};
unsigned int flash_led_brightness_[3]={255,255,255};
unsigned int flash_led_delay_[3]={8,8,8};
unsigned int flash_led_initial_delay_[3]={0,0,0};
void calculate_led_level()
{
  for (int ledid = 0; ledid < NUM_LEDS; ledid++)
  {
    if (flash_led_time_[ledid] == 0)
      continue;
    if (wait_millis(wm_start_ + ledid, flash_led_initial_delay_[ledid]))
      continue;
    flash_led_initial_delay_[ledid]=0;
    if (wait_millis(wm_start_ + ledid, flash_led_delay_[ledid]))
      continue;
    flash_led_time_[ledid]--;
    int c = abs(sin(float(flash_led_time_[ledid]) / 100.0)) * flash_led_brightness_[ledid];
    //int d = abs(sin(float(flash_led_time_) / 100.0)) * flash_led_brightness_;
    analogWrite(flash_led_pins_[ledid], 255-c);
  }
}

// id: id of LED to flash (0,1)
// times: # of times the LED should flash
// brightness_divisor: 1: full brightness, 2: half brightness, ...
// delay_divisor: 1: slow... 8: fastest
// phase_divisor: 0.. same phase; 2.. pi/2 phase, 4.. pi phase, 6.. 3pi/2 phase
void flash_led(unsigned int id, unsigned int times, unsigned int brightness_divisor, unsigned int delay_divisor, unsigned int phase_divisor)
{
  if (id >= NUM_LEDS)
    return;
  unsigned int new_flash_led_brightness = 255;
  unsigned int new_flash_led_delay = 8;
  if (times == 0)
  {
    analogWrite(flash_led_pins_[id],255); //off
    return;
  }
  if (brightness_divisor > 1) //guard against div by zero
    new_flash_led_brightness /= brightness_divisor;
  if (delay_divisor > 1)  //guard against div by zero
    new_flash_led_delay /= delay_divisor;
  if (flash_led_time_[id] == 0 || new_flash_led_brightness > flash_led_brightness_[id])
    flash_led_brightness_[id]=new_flash_led_brightness;
  if (flash_led_time_[id] == 0 || new_flash_led_delay < flash_led_delay_[id])
    flash_led_delay_[id]=new_flash_led_delay;
  flash_led_time_[id] += 314*times;
  flash_led_initial_delay_[id] = flash_led_delay_[id]*314*phase_divisor/8;
}

//********************************************************************//

int save_tcnt2=0;
int save_tccr2a=0;
int save_tccr2b=0;
void reset_timer2()
{
  TCNT2 = save_tcnt2;
  TCCR2A = save_tccr2a;  // normal mode
  TCCR2B = save_tccr2b;
  //TCNT2 = 256 - (50*(16000000/8/1000000)) + 5;
  //TCCR2A = 0;  // normal mode
  //TCCR2B = 0;
}

void send_yamaha_ir_signal(char codebyte)
{
  unsigned long int code = codebyte & 0xFF;
  code <<= 8;
  code |= (0xff ^ codebyte) & 0xFF;
  code |= YAMAHA_CODE_BASE;

  //irsend changes PWM Timer Frequency among other things
  //.. doesn't go well with PWM output using the same timer
  //.. thus we just set output to 255 so whatever frequency is used, led is off for the duration
  //analogWrite(BLUELED_PWM_PIN,255); // switch led off

  irsend.sendNEC(code,YAMAHA_CODE_BITS);

  reset_timer2();
  analogWrite(BLUELED_PWM_PIN,255); // switch off led again to be sure
                                      //is actually not necessary, since we are not multitasking/using interrupts, but just to be sure in case this might change

  Serial.println("Ok");
}

//********************************************************************//

void setup()
{
  pinMode(RF_DATA_OUT_PIN, OUTPUT);
  digitalWrite(RF_DATA_OUT_PIN, HIGH);
  pinMode(IR_MOVEMENT_PIN, INPUT);      // set pin to input
  digitalWrite(IR_MOVEMENT_PIN, LOW);  // turn off pullup resistors
  digitalWrite(IR_MOVEMENT_PIN2, LOW);  // turn off pullup resistors
  pinMode(PANIC_BUTTON_PIN, INPUT);      // set pin to input
  digitalWrite(PANIC_BUTTON_PIN, LOW);  // turn of pullup resistors
  analogWrite(PANICLED_PWM_PIN,255);
  analogWrite(BLUELED_PWM_PIN,255); //pwm sink(-) instead of pwm + (better for mosfets)
  pinMode(IRREMOTE_SEND_PIN, OUTPUT);
  digitalWrite(IRREMOTE_SEND_PIN, HIGH);

  Serial.begin(9600);

  onewire.reset();
  onewire.reset_search();
  dallas_sensors.begin();
  //in case we change temp sensor:
  if (!dallas_sensors.getAddress(onShieldTemp, 0))
    Serial.println("Error: Unable to find address for Device 0");
  dallas_sensors.setResolution(onShieldTemp, 9);

  //save prev timer states:
  save_tcnt2 = TCNT2;
  save_tccr2a = TCCR2A;  // normal mode
  save_tccr2b = TCCR2B;
}

unsigned int ir_time=IR_SAMPLE_DURATION;
unsigned int ir_count=0;
unsigned int ir_count2=0;
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
  ir_count2 += (digitalRead(IR_MOVEMENT_PIN2) == HIGH);

  if (pb_time < PB_TRESHOLD)
    pb_time++;
  pb_state=(digitalRead(PANIC_BUTTON_PIN) == HIGH);

  if (ir_time == 0)
  {
    if (ir_count >= IR_TRESHOLD || ir_count2 >= IR_TRESHOLD)
    {
      flash_led(0, 1, 8, 1, 0 );
      Serial.println("movement");
    }
    ir_time=IR_SAMPLE_DURATION;
    ir_count=0;
    ir_count2=0;
  }

  if (pb_state == pb_last_state && pb_time >= PB_TRESHOLD)
  {
    if (pb_state && ! pb_postth_state)
    {
      pb_postth_state=1;
      Serial.println("PanicButton");
      flash_led(0, 28, 1, 4, 0 );
      flash_led(1, 28, 1, 4, 4 );
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
  calculate_led_level();
  check_frame_done();
  if(Serial.available()) {
    char command = Serial.read();

    if (command == '>')
    {
      serial_read_send_rf_cmd();
    }
    else if(command == 'A')  
      send_rf_cmd("\x8a\xa0\x8a"); // pollin 00101 a 1
    else if(command == 'a')
      send_rf_cmd("\x8a\xa0\x2a");  // pollin 00101 a 0
    else if(command == 'B')
      send_rf_cmd("\xa0\xa2\xa8"); //white remote A 2 on
    else if(command == 'b')
      send_rf_cmd("\xa0\xa2\x28"); //white remote A 2 off    
    else if(command == 'C')
      send_rf_cmd("\xa2\xa0\xa8"); //white remote B 1 on
    else if(command == 'c')
      send_rf_cmd("\xa2\xa0\x28"); //white remote B 1 off
    else if(command == 'D')
      send_rf_cmd("\x8a\x88\x8a"); //pollin 00101 b 1
    else if(command == 'd')
      send_rf_cmd("\x8a\x88\x2a"); //pollin 00101 b 0
    else if(command == 'E')
      send_rf_cmd("\xa8\xa0\xa8"); //white remote C 1 on
    else if(command == 'e')    
      send_rf_cmd("\xa8\xa0\x28"); //white remote C 1 off
    else if(command == 'F')
      send_rf_cmd("\xa8\xa2\xa8");
    else if(command == 'f')
      send_rf_cmd("\xa8\xa2\x28");
    else if(command == 'G')
      send_rf_cmd("\xaa\xa0\xa8");
    else if(command == 'g')
      send_rf_cmd("\xaa\xa0\x28");
    else if(command == 'H')
      send_rf_cmd("\xaa\xa2\xa8");
    else if(command == 'h')
      send_rf_cmd("\xaa\xa2\x28");
    else if(command == 'I')
      send_rf_cmd("\x8a\x28\x8a"); //pollin 00101 c 1
    else if(command == 'i')
      send_rf_cmd("\x8a\x28\x2a"); //pollin 00101 c 0
    else if(command == 'J')
      send_rf_cmd("\x8a\xa8\x88"); //pollin 00101 d 1
    else if(command == 'j')
      send_rf_cmd("\x8a\xa8\x28"); //pollin 00101 d 0
    else if(command == 'L')
      send_rf_cmd("\xae\x2b\x30");
    else if(command == 'l')
      send_rf_cmd("\xae\x2b\xc0");
    else if(command == 'M')
      send_rf_cmd("\xae\x2e\x30");
    else if(command == 'm')
      send_rf_cmd("\xae\x2e\xc0");      
    else if(command == 'N')
      send_rf_cmd("\xae\x3a\x30");
    else if(command == 'n')
      send_rf_cmd("\xae\x3a\xc0");
    else if(command == 'Z')
      send_rf_cmd("\xa2\xa2\xaa");
    else if(command == 'z')
      send_rf_cmd("\xa2\xa2\x2a");
    else if(command == '*')
    {
      sensorEchoCommand(command);
      printTemperature(onShieldTemp);
    }
    else if(command == '?')
    {
      sensorEchoCommand(command);
      printLightLevel();
    }
    else if (command == '^')
    {
      //flash_led(1, 1, 2, 1, 0);
      flash_led(1, 1, 1, 1, 0);
      Serial.println("Ok");
    }
    else if (command == '&')
    {
      flash_led(0, 1, 2, 1, 0);
      Serial.println("Ok");
    }
    else if (command == '1')
      send_yamaha_ir_signal(YAMAHA_CD);
    else if (command == '2')
      send_yamaha_ir_signal(YAMAHA_TUNER);
    else if (command == '3')
      send_yamaha_ir_signal(YAMAHA_TAPE);
    else if (command == '4')
      send_yamaha_ir_signal(YAMAHA_DVD_SPDIF);
    else if (command == '5')
      send_yamaha_ir_signal(YAMAHA_SAT_SPDIFF);
    else if (command == '6')
      send_yamaha_ir_signal(YAMAHA_VCR);
//    else if (command == '7')
//      send_yamaha_ir_signal();
    else if (command == '8')
      send_yamaha_ir_signal(YAMAHA_AUX);
    else if (command == '9')
      send_yamaha_ir_signal(YAMAHA_EXT51DEC);
    else if (command == '0')
      send_yamaha_ir_signal(YAMAHA_TEST);
    else if (command == '/')
      send_yamaha_ir_signal(YAMAHA_TUNER_ABCDE);
    else if (command == '\\')
      send_yamaha_ir_signal(YAMAHA_EFFECT_TOGGLE);
    else if (command == '-')
      send_yamaha_ir_signal(YAMAHA_TUNER_MINUS);
    else if (command == '+')
      send_yamaha_ir_signal(YAMAHA_TUNER_PLUS);
    else if (command == ':')
      send_yamaha_ir_signal(YAMAHA_POWER_OFF);
    else if (command == '.')
      send_yamaha_ir_signal(YAMAHA_POWER_TOGGLE);
    else if (command == ';')
      send_yamaha_ir_signal(YAMAHA_VOLUME_UP);
    else if (command == ',')
      send_yamaha_ir_signal(YAMAHA_VOLUME_DOWN);
    else if (command == '_')
      send_yamaha_ir_signal(YAMAHA_MUTE);
    else if (command == '#')
      send_yamaha_ir_signal(YAMAHA_MENU);
    else if (command == '"')
      send_yamaha_ir_signal(YAMAHA_PLUS);
    else if (command == '!')
      send_yamaha_ir_signal(YAMAHA_MINUS);
    else if (command == '=')
      send_yamaha_ir_signal(YAMAHA_TIME_LEVEL);
    else if (command == '$')
      send_yamaha_ir_signal(YAMAHA_PRG_DOWN);
    else if (command == '%')
      send_yamaha_ir_signal(YAMAHA_PRG_UP);
    else if (command == '(')
      send_yamaha_ir_signal(YAMAHA_SLEEP);
    else if (command == ')')
      send_yamaha_ir_signal(YAMAHA_P5);
    else
      Serial.println("Error: unknown command");
  }
}
