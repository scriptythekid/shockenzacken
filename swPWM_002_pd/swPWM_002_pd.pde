/*
 scriptythekid 2k12 - 
 electro shocks for games (urban terror) / 4 players per arduino, or maybe even more
 

/*

 hyper hardcoded communication protocol towards pure data:
 featuring "MSCP"
 milgram shock control protocol
 
 arduino outputs:
 byte 82 - ready = ascii R
 byte 75 - ok    = ascii K
 byte 88 - error = ascii X
 
 arduino reads: (byte sequences)
 F int [int int int ].(character)   - sets Frequency for all players
 S int int [int] - (character) int [int int int].(character)  - Shock Payer int with Frequ int [int] for int [int int int] milliseconds
 
 example: S01-X250.
           S01-X2.    pn: 0 frq: 1 dur:402
           S01-A.    pn: 0 frq: 1 dur:17

           
 //
 */
#define MSCP_READY 82
#define MSCP_OK 75
#define MSCP_ERROR 88

#define DEBUG 1



#include <MsTimer2.h>

int ledPin =  13;    // LED connected to digital pin 13

//"lightning reaction" PCB pins:
int resetPin = 12;
int startgamePin = 11;
unsigned long millisSinceLastPCBReset = 0;
unsigned long currentMillis = 0;
unsigned long resetMillisInterval = 5000;


//FIXME comments on variables please
int pwmAdjustPin = 0;
int tmpint=0;
int pwmbase=0;
boolean updatePWM_poti = false;
boolean updatePWM_serial = true;


//FIXME comments on variables please
const int inputsize = 10;
const int maxplayers = 9;
const int timerresolution = 3;  // unit: ms; the resolution for MsTimer2: e.g. 1 = mstimer will interupt every 1ms
                                // set to 3 for ~166Hz , no further frequency adjustment is done...
//unused in this version
const int DEF_SHOCK_FREQUENCY = 9; // unit: ; the effective frequency to shock players with - iirc settable via serial shockCommand
/*
    looks like this was there to have the interrupt occur every 2ms, but then invert the shock signal every 9ms
    so effectivly: invert every 11ms - one phase= 22ms : 1000ms/22ms= ~45Hz
    current goal: get close to 170hz: 1000ms/170Hz=5.88235294118ms == one phase, so invert every 5.882/2 = invert every 2.9ms
    so lets invert every 3ms so we should get 166Hz
    
*/
const int DEF_SHOCK_DUR = 250;  // the default shock duration - iirc also settable via serial shockCommand

int ser_bytes[inputsize];
int ser_bindex=0;
int tmppwm = 0;

struct Player {
  int shockduration;
  int frequency;
  int nextinvert;
  int pin;
  boolean state;
  //pin 13 = my debug pin (LED)
  Player():
  shockduration(0),frequency(DEF_SHOCK_FREQUENCY),nextinvert(0),pin(13),state(LOW) {

  }

  void handletimertick() {
    //gets called every x ms (3ms for 170hz frequency: 6ms = full phase, 50% HIGH 50% LOW)
    if (shockduration > 0) {
      digitalWrite(pin, state);
      state = !state;
      shockduration -= timerresolution;
    } else {
      //dont schock idle players with state staying HIGH!!!
      state = LOW;
      digitalWrite(pin, state);
    }
  }


  void handletimertick_old() {
    if(shockduration > 0) {
      if(nextinvert < 1) {
        digitalWrite(pin, state);
        state = !state;
        nextinvert += frequency;
      } 
      else {
        nextinvert -= timerresolution;
      }
      shockduration -= timerresolution;
    } 
    else {
      //dont schock idle players with state staying HIGH!!!
      state = LOW;
      digitalWrite(pin, state);
    }
  }
};

Player players[maxplayers];

/*
used for switching gamemode on and
toggling reset pin on the "lightning reaction" PCB
*/

void pressButton(int pin) {
  digitalWrite(pin, HIGH);
  pinMode(pin, OUTPUT);
  delay(250);
  //"depress" button:
  pinMode(pin, INPUT);
  digitalWrite(pin, LOW);
}

// The setup() method runs once, when the sketch starts
void setup()   {                
  // initialize the digital pin as an output:
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);   // set the LED on

  //int resetPin = 12;
  //int startgamePin = 11;  
  pinMode(resetPin, INPUT);
  pinMode(startgamePin, INPUT);
  
  Serial.begin(9600);

  //set initial shocking frequency

  //init pins for players
  for(int i=0;i<maxplayers;i++) {
    players[i].pin = i+2;
    pinMode(players[i].pin, OUTPUT);
  }

#ifdef DEBUG
  Serial.println("elektroshock ready! 64KVolt ready. fire at will.");
#else
  Serial.print(MSCP_READY,BYTE);
#endif


  MsTimer2::set(timerresolution, shock);
  MsTimer2::start();
  
  //start the game on "lightningshock" PCB  
  millisSinceLastPCBReset = millis();
  pressButton(startgamePin);
}

void shock() {
  for(int i=0;i<maxplayers;i++) {
    players[i].handletimertick();
  }
}

int handleMessage() {
  tmppwm = 0;
  if(ser_bytes[0] == 'F' && ser_bindex > 1) {
    //old deprecated?
    for(int i=1;i < ser_bindex;i++) {
      tmppwm = tmppwm*10 + (ser_bytes[i] - '0'); // byte to int lolfoo
    }
    if(tmppwm > 0) {
#ifdef DEBUG
      Serial.print("pwm set to: ");
      Serial.println(tmppwm, DEC);
#else

#endif
      for(int i=0;i<maxplayers;i++) {
        players[i].frequency = tmppwm;
      }
      return 1;
    }
    return 0;
  } 
  else if(ser_bytes[0] == 'S' && ser_bindex > 1) {
    // S int int [int] - (character) int [int int int].
    // 0 1   2    3    4             5    6   7   8   9
    //   pn    frequ                 duration
    //playernum
    int pn = ser_bytes[1] -'0';
    //freq for player
    int frq=DEF_SHOCK_FREQUENCY;
    int idx=0;
    if(ser_bytes[3] == '-') {
      frq=ser_bytes[2] - '0';
      idx = 4;
    } 
    else if(ser_bytes[4] == '-') {
      frq=((ser_bytes[2] - '0')*10) + (ser_bytes[3] - '0');
      idx = 5;
#ifdef DEBUG
      Serial.print("frq: ");
      Serial.println(frq, DEC);
#endif
    } 
    else {
      //malformed msg
      return 0;
    }

    //read duration
    if(ser_bindex - idx > 4) {
      //error
      return 0;
    }

    int dur = 0;
    for(int i=idx;i < ser_bindex;i++) {
      dur = dur*10 + (ser_bytes[i] - '0'); // byte to int lolfoo
    }
#ifdef DEBUG
    Serial.print("pn: ");
    Serial.print(pn, DEC);
    Serial.print(" frq: ");
    Serial.print(frq, DEC);
    Serial.print(" dur:");
    Serial.print(dur, DEC);
    Serial.println("");

#else
#endif
    //now shock se pläyer!!!
    players[pn].frequency = frq;
    players[pn].shockduration = dur;
    //player has fun now.
    return 1;
  } 
  else {
    //Serial.println("unknown command");
    //erreur return 0
    return 0;
  }
}

void loop()                     
{
  
  
  if(updatePWM_serial == true) {

    int tmpByte = Serial.read();
    if(tmpByte != -1) {

      if(tmpByte != '.') {
        ser_bytes[ser_bindex] = tmpByte;
        ser_bindex++;
      } 
      else {

        if(handleMessage()) {
#ifdef DEBUG
          Serial.println("OK");
#else
          Serial.print(MSCP_OK,BYTE);
#endif
        } 
        else {
#ifdef DEBUG
          Serial.println("error - msg not handled");
#else
          Serial.print(MSCP_ERROR,BYTE);
#endif
        }

        ser_bindex=0;
      }

      if(ser_bindex > inputsize-1) {
        ser_bindex = 0;
#ifdef DEBUG
        Serial.println("index set to zero. bytelolfoo...");
#else
        Serial.print(MSCP_ERROR,BYTE);
#endif
      }
    }
  }


  // count seconds, reset the lighting shock PCB every x seconds
  currentMillis = millis();
  if (currentMillis - millisSinceLastPCBReset > resetMillisInterval) {
    Serial.println("resetting shocking PCB...");
    Serial.print(currentMillis, DEC);
    pressButton(resetPin);
    delay(80);
    pressButton(startgamePin);
    millisSinceLastPCBReset = currentMillis;
  }
  
}

