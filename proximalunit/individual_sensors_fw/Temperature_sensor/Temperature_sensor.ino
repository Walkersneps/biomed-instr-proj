#define TEMPSENS_PIN 32
#define FILTER_NSAMPLES 100

int i;
long total;

/* Conversion
float c1 = 1.009249522e-03, c2 = 2.378405444e-04, c3 = 2.019202697e-07;
float delta_v;
float out;
float V_ref=3.3;
int R1=2490;
float Rt;
int R0=100;
float Temp;
float Temp2;
float a=3.9083e-3;
float b=-5.775e-7;
float G=14.53;
*/

void setup() {
  Serial.begin(9600);
}

void loop() {
  /*
  out=(Vo/4095.0-1)*V_ref;
  Rt=float(out/G)/(V_ref/R1);

  Temp=(-a+sqrt((sq(a)-4*(b*(1-Rt/R0)))))/(2*b);
  */

  // Flat Average
  total = 0;
  for (i= 0; i<FILTER_NSAMPLES; i++)
    total += analogRead(TEMPSENS_PIN);
  
  Serial.println(total / FILTER_NSAMPLES);

  /*
  Serial.print("Temperature: "); 
  Serial.print(Temp);
  Serial.println(" °C");
  */

  delay(500);
}
