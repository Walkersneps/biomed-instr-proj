#define NSAMPLES 80
#define FLOWSENS_PIN 35

long avg;
long total = 0;
int samples[NSAMPLES] = {0};
int idx = 0;

void setup() {
  Serial.begin(115200);
  //pinMode(FLOWSENS_PIN, INPUT);
}

void loop() {
  total = total - samples[idx];
  samples[idx] = analogRead(FLOWSENS_PIN);
  total = total + samples[idx];

  idx += 1;
  if (idx >= NSAMPLES) idx = 0;

  avg = total / NSAMPLES;
  
  Serial.println(avg);
  delay(10);
}
