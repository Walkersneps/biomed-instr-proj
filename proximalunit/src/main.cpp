#include <map>
#include <unordered_map>
#include <cstring>
#include <string>
#include <Arduino.h>
#include <WiFi.h>
#include <espMqttClientAsync.h>
#include <ArduinoJson.h>
#include <max86150.h>
#include <BiosignalsAcquisition.h>
#include <SensorsInitializations.h>

// ## o-o-o-o SETTINGS o-o-o-o ##
// ##############################
// ###  Wifi Settings ###
#include <secrets.h> // Tune this to your setup

// ### MQTT Settings ###
#define MQTT_BROKER_HOST IPAddress(192, 168, 1, 1)
#define MQTT_BROKER_PORT 1883
#define MQTT_TOPIC_CONFIG "cfg"

#define SERIAL_BAUDRATE 115200

#define MAX_SIGNALS 5 // Maximum numbers of signals to be acquired

// ###############################
// o-o-o-o END of SETTINGS o-o-o-o

// Standard indexes for arrays
// NB: none of those must exceed `MAX_SIGNALS - 1`!!!
#define IDX_ECG 0 // ElectroCardioGram
#define IDX_PPG 1 // PhotoPletismoGram
#define IDX_GSR 2 // Galvanic Skin Response
#define IDX_TMP 3 // TeMPerature
#define IDX_RVL 4 // Respiratory VoLume

// MQTT Management stuff
espMqttClientAsync mqttClient; // The actual MQTT Client instance
bool needsMQTTreconnection = false;
uint32_t timeOfLastReconnect = 0;
uint32_t currentMillis;
char topicPrefix[10];

// Handling of big/batched MQTT messages
const size_t maxPayloadSize = 8192; // Payloads with a total size exceeding this number will be discarded.
uint8_t* payloadBuffer = nullptr;
size_t payloadBufferSize = 0;
size_t payloadBufferIdx = 0;

// Topic-Callback pairing
struct MatchTopic { // Defines how to resolve an MQTT topic match.
  bool operator()(const char* a, const char* b) const {
    return strcmp(a, b) < 0;
  }
};
std::map<const char*, espMqttClientTypes::OnMessageCallback, MatchTopic> topicCallbacks; // This map will store the couples {topicName -> callbackFunc}, allowing messages coming from different topics to be handled indipendently.

// Operative Settings
JsonDocument settings;

// FreeRTOS Tasks handles
TaskHandle_t* taskHandles[MAX_SIGNALS] = {nullptr}; // Stores handles pointing to created RTOS tasks
const std::unordered_map<std::string, uint8_t> taskHandleIndexes = { // Matches signalName to correct index of the handle to the vTask() which samples that signal.
  {"ECG", IDX_ECG},
  {"PPG", IDX_PPG},
  {"GSR", IDX_GSR},
  {"TMP", IDX_TMP}
};


// FreeRTOS Tasks
void vTask_SampleMAX86150(void *pvParameters) {
  // Recover settings
  JsonObject config = *static_cast<JsonObject *>(pvParameters);
  const float fsample = config["fsample"].as<float>();
  const int overlay = config["overlay"].as<int>();
  const int npacket = config["npacket"].as<int>();

  // Build full topic names
  char topicECG[strlen(topicPrefix) + 3];
  char topicPPGRed[strlen(topicPrefix) + 6];
  char topicPPGIR[strlen(topicPrefix) + 5];
  strcpy(topicECG, topicPrefix);
  strcpy(topicPPGRed, topicPrefix);
  strcpy(topicPPGIR, topicPrefix);
  strcpy(&topicECG[strlen(topicPrefix)], "ECG");
  strcpy(&topicPPGRed[strlen(topicPrefix)], "PPGRed");
  strcpy(&topicPPGIR[strlen(topicPrefix)], "PPGIR");
  
  // Initialize sensor
  MAX86150* max86150 = new MAX86150();
  initializeMAX86150(max86150);

  // Check that we have everything we need
  const bool dataOk = (fsample && overlay && npacket);
  if (!dataOk) { Serial.print(F("[ERROR] Uncastable settings for ECG")); }

  // Prepare array to hold the samples
  static int16_t* samplesECG;
  static uint16_t* samplesIR;
  static uint16_t* samplesRED;
  samplesECG = static_cast<int16_t*>(pvPortMalloc(npacket * sizeof(int16_t)));
  samplesIR = static_cast<uint16_t*>(pvPortMalloc(npacket * sizeof(uint16_t)));
  samplesRED = static_cast<uint16_t*>(pvPortMalloc(npacket * sizeof(uint16_t)));
  int sampleIndex = 0;

  // Prepare timing data
  const TickType_t samplePeriod = pdMS_TO_TICKS(1000 / fsample); // Convert [Hz] fsample to number of ticks period
  Serial.printf("[%s] A sample will be acquired every %d ms, aka every %d ticks.\n", "ECG/PPG", pdTICKS_TO_MS(samplePeriod), samplePeriod);
  BaseType_t xWasDelayed;
  TickType_t xLastWakeTime = xTaskGetTickCount();

  while (dataOk) {
    xWasDelayed = xTaskDelayUntil(&xLastWakeTime, samplePeriod);

    if (max86150 -> check() > 0) {
     /* Note on MAX86150 data!
      * The data that then sensor outputs is  3-byte-long (24bit),
      * although the actual useful datum is always either 18 (for ECG) or 19 (for PPG) bits long.
      * 
      * The library we're using returns those in `uint32_t` datatype to fit the whole 24bits,
      * while masking the unused MSBs of each datum to 0.
      * 
      * Accepting to lose 2 LSBs of resolution, we can fit the data in 16bits, just by shifting
      * to the right 2 positions.
      */
      samplesECG[sampleIndex] = static_cast<int16_t>(max86150 -> getFIFOECG() >> 2);
      samplesIR[sampleIndex] = static_cast<uint16_t>(max86150 -> getFIFOIR() >> 2);
      samplesRED[sampleIndex] = static_cast<uint16_t>(max86150 -> getFIFORed() >> 2);
      sampleIndex++;
    }

    if (xWasDelayed == pdTRUE) {
      Serial.print("[");
      Serial.print(F("MAX86150"));
      Serial.println(F("] ! Sampling was delayed!"));
    }

    if (sampleIndex >= npacket) { // A packet is completeley filled and ready to be sent
      /* Per library docs, espMqttClient::publish(...) should buffer the payload
       * --> we don't need to worry about overwriting it before it is completely transmitted.
       * espMqttClient::publish(...) expects the payload to be an `uint8_t`, but we've been storing
       * samples as `uint16_t`s --> a cast is needed, keeping in mind that now, interpreting
       * the sample array in this way, we'll have more elements, as 16/8 = 2.
      */
      mqttClient.publish(topicECG, 2, false, reinterpret_cast<uint8_t*>(samplesECG), npacket * 2);
      mqttClient.publish(topicPPGRed, 2, false, reinterpret_cast<uint8_t*>(samplesRED), npacket * 2);
      mqttClient.publish(topicPPGIR, 2, false, reinterpret_cast<uint8_t*>(samplesIR), npacket * 2);
      
      // Bring back the overlayed samples
      sampleIndex = 0;
      for (uint8_t i = overlay; i > 0; i--) {
        samplesECG[sampleIndex] = samplesECG[npacket - i];
        samplesIR[sampleIndex] = samplesIR[npacket - i];
        samplesRED[sampleIndex] = samplesRED[npacket - i];
        sampleIndex++;
      }
    }

  }

  // TODO: !!! ensure this is run also on task deletion !!!
  vPortFree(samplesECG);
  vPortFree(samplesIR);
  vPortFree(samplesRED);
}




void connectToWiFi(const char* ssid, const char* pswd) {
  Serial.printf("[MAIN] Connecting to WiFi... ssid: '%s'. password: '%s'.\n", ssid, pswd);
  WiFi.begin(ssid, pswd);
}

void connectToMQTTBroker() {
  Serial.print(F("[MAIN] Connecting to MQTT Broker... "));
  if (!mqttClient.connect()) { // Attempts connection. This `if` block will be executed if connection fails.
    needsMQTTreconnection = true;
    timeOfLastReconnect = millis();
    Serial.println(F("\n[ERROR] . Connection attempt to MQTT broker failed."));
  } else {
    needsMQTTreconnection = false;
    Serial.println(F("Successful!"));
  }
}

void WiFiEvent(WiFiEvent_t e) {
  Serial.printf("[WiFi] Got event: %d\n", e);
  switch (e) {
    case SYSTEM_EVENT_STA_GOT_IP: // Connection successful and wifi is ready
      Serial.print(F("[WiFi] Connection successful!!\n[WiFi] IP Address is: "));
      Serial.println(WiFi.localIP());
      
      connectToMQTTBroker();
      break;

    case SYSTEM_EVENT_STA_DISCONNECTED:
      Serial.println(F("[WiFi] [ERROR] WiFi connection has been lost!"));
      break;
    
    default:
      Serial.println(F("[WiFi] Unhandled event."));
      break;
    }
}

/* Callback handler when a connection is established to the MQTT Broker.
 * Performs subscriptions to topics and publishes a message to acknowledge its presence.
*/
void _onMQTTConnect(bool sessionPresent) {
  Serial.print(F("[MQTT] Connected to broker!\n[MQTT] Session present: "));
  Serial.println(sessionPresent);

  Serial.printf("[MQTT] Subscribing to Configuration channel `%s`...\n", MQTT_TOPIC_CONFIG);
  mqttClient.subscribe(MQTT_TOPIC_CONFIG, 2);

  Serial.println(F("[MQTT] Publishing presence message..."));
  mqttClient.publish(MQTT_TOPIC_CONFIG, 2, false, "[proximalunit] Connected!");
}

void _onMQTTDisconnect(espMqttClientTypes::DisconnectReason reason) {
  Serial.printf("[MQTT] Disconnected :(  reason: %u\n", static_cast<uint8_t>(reason));

  if (WiFi.isConnected()) {
    needsMQTTreconnection = true;
    timeOfLastReconnect = millis();
  }
}

void _onMQTTSubscribe(uint16_t packetId, const espMqttClientTypes::SubscribeReturncode* retCodes, size_t len) {
  Serial.printf("[MQTT] Subscription(s) in packetID #%s was acknowledged, with QoS:\n       .");
  for (size_t i = 0; i < len; ++i) {
    Serial.print(F(" qos: "));
    Serial.print(static_cast<uint8_t>(retCodes[i]));
  }
  Serial.println();
}

void _onOversizedMessage(const espMqttClientTypes::MessageProperties& props, const char* topic, const uint8_t* payload, size_t chunkSize, size_t index, size_t total) {
  Serial.println(F("[MQTT] Got an oversized MQTT message. I can't handle that! :(("));
}

void createSamplingTask(const char* signalName, char* taskName, UBaseType_t uxPriority, void* pvParameters, BaseType_t xCoreID) {
  auto it = taskHandleIndexes.find(signalName);
  if (it != taskHandleIndexes.end()) { // `signalName` was found in the map (aka I haven't searched for it past the map's own size)
    TaskHandle_t* taskHandle = taskHandles[it -> second]; // obtain the corresponding taskHandle*

    switch (it -> second) {
      case IDX_ECG:
        xTaskCreatePinnedToCore(vTask_SampleMAX86150, taskName, 2048, pvParameters, uxPriority, taskHandle, xCoreID);
        break;
      
      default:
        Serial.println(F("       . TashHandle INDEX not in switch/case."));
        Serial.println(F("[ERROR]. Couldn't create sampling task."));
        break;
    }
  } else { // no index was specified for this specific signalName
    Serial.println(F("       . I don't know where to look for the index of the taskHandle* for this signal"));
    Serial.println(F("[ERROR]. Couldn't create sampling task."));
  }
}

void applySignalsSettings(const JsonObject signals) {
  // Delete old tasks
  // TODO: ensure they have freed their malloc()'ed memory!!
  for (int i = 0; i < MAX_SIGNALS; i++)
    if (taskHandles[i])
      vTaskDelete(taskHandles[i]);

  // Cycle through signals in the settings dict and start the corresponding sampling task for each
  for (JsonPair pair: signals) { // See the same iterator implemented in `_onCompleteConfigMessage(...)` for details
    const char* signalName = pair.key().c_str();
    static JsonObject sett = pair.value().as<JsonObject>();
    sett["signalName"] = signalName; // add field to sett, useful to pass on the signalName to invoked subroutines

    Serial.print(F("[MAIN] Creating freeRTOS task for "));
    Serial.println(signalName);
    char* taskName = static_cast<char*>(malloc(sizeof(char) * (strlen(signalName) + 6))); // task_ has 5 chars + 1 for the terminator (NB: strlen() doesn't count the terminator).
    strcpy(taskName, "task_");
    strcpy(&taskName[5], signalName); // strcpy() also copies the terminator. We will overwrite it with the first char of `signalName`.
    const int priority = sett["priority"].as<int>();

    createSamplingTask(signalName, taskName, priority, &sett, APP_CPU_NUM);

    free(taskName);
  }
    
}

/* Final arrival point of messages published to topic `MQTT_TOPIC_CONFIG`.*/
void _onCompleteConfigMessage(const espMqttClientTypes::MessageProperties& props, const char* topic, const uint8_t* payload, size_t chunkSize, size_t index, size_t total) {
  Serial.println(F("[MQTT] Got Config message from remoteunit: "));

  // Transform the char array to an actual null-terminated c-string
  char* strval = new char[chunkSize + 1];
  memcpy(strval, payload, chunkSize);
  strval[chunkSize] = '\0';
  Serial.println(strval);

  DeserializationError err = deserializeJson(settings, strval);
  delete[] strval;

  if (err) {
    Serial.print(F("[JSON] ERROR: Deserialization error: "));
    Serial.print(err.f_str());
    Serial.println(F("\nAborting interpretation of this message"));
    return;
  }

  // Save signals topic prefix
  strcpy(topicPrefix, settings["MQTT_TOPIC_PREFIX"].as<const char*>());

  JsonObject json = settings.as<JsonObject>(); // Get smart object reference
  for (JsonPair pair: json) { // Look for the `BIOSIGNALS` field, which contains settings for each signal
    /* Each JsonPair contains:
     * JsonPair::key() -> JsonString
     * JsonPair::value() -> JsonVariant
    */
    if (!strcmp(pair.key().c_str(), "BIOSIGNALS")) {
      applySignalsSettings(pair.value().as<JsonObject>());
    }
  }
}

/* Handler for messages received on `MQTT_TOPIC_CONFIG`.

 * Considering that we may expect msgs composed of potentially long configuration strings on this topic,
 * the function implements logic to allow recomposition of payloads which were split into smaller chunks.
 * 
 * Subsequent messages are assembled together until we have a `payloadBuffer` which holds the whole payload,
 * which is then passed to `_onCompleteConfigMessage(...)`.
 * 
 * If the total size of the payload is higher than `maxPayloadSize`, function `_onOversizedMessage(...)` is called.
*/
void _onConfigMessage(const espMqttClientTypes::MessageProperties& props, const char* topic, const uint8_t* payload, size_t chunkSize, size_t index, size_t total) {
  // payload is bigger then max --> call _onOversizedMessage() with the chunked message.
  if (total > maxPayloadSize) {
    _onOversizedMessage(props, topic, payload, chunkSize, index, total);
    return;
  }

  if (index == 0) { // That's the first chunk of the split payload --> Initialize buffer
    if (total > payloadBufferSize) { // If this first chunk is bigger than expected, make room for it
      delete[] payloadBuffer;
      payloadBufferSize = total;
      payloadBuffer = new (std::nothrow) uint8_t[payloadBufferSize];
      if (!payloadBuffer) {
        Serial.print(F("[ERROR] Payload buffer couldn't be created to handle chunked msg! (Out of memory?)"));
        return;
      }
    }
    payloadBufferIdx = 0;
  }

  // add data and dispatch when done
  if (payloadBuffer) {
    memcpy(&payloadBuffer[payloadBufferIdx], payload, chunkSize);
    payloadBufferIdx += chunkSize;
    if (payloadBufferIdx == total) {
      // message is complete here --> let's finally read it as completely assembled
      _onCompleteConfigMessage(props, topic, payloadBuffer, total, 0, total);
      
      // Reset for next time
      delete[] payloadBuffer;
      payloadBuffer = nullptr;
      payloadBufferSize = 0;
    }
  }
}

/* First Entry Point to handle received message on a topic we're subscribed to.
 * Searches on the map `topicCallbacks` if a specific handler exist for the message's topic.
 * If no specific handler is found for the topic, a generic message is printed to Serial.
*/
void _onMQTTMessage(const espMqttClientTypes::MessageProperties& props, const char* topic, const uint8_t* payload, size_t chunkSize, size_t index, size_t total) {
  Serial.printf("[MQTT] Received publication on topic %s:\n", topic);

  auto it = topicCallbacks.find(topic);
  if (it != topicCallbacks.end()) { // `topic` was found in the map (aka I haven't searched for it past the map's own size)
    (it -> second)(props, topic, payload, chunkSize, index, total); // run the corresponding callback
  } else { // no callback was specified for this specific topic
    Serial.println(F("       . I don't know what to do with this message hehehe ^_^"));
  }
}




void setup() {
  // Setup topic callbacks
  topicCallbacks.emplace(MQTT_TOPIC_CONFIG, _onConfigMessage); // The callback which will handle incoming messages on topic 'cfg' is _onConfigMessage

  Serial.begin(SERIAL_BAUDRATE);
  Serial.println(F("[SETUP] Hello! Setup in progress..."));

  Serial.println(F("[SETUP] Setupping WiFi settings..."));
  WiFi.setAutoConnect(false);
  WiFi.setAutoReconnect(true);
  WiFi.onEvent(WiFiEvent);
  WiFi.setMinSecurity(WIFI_AUTH_OPEN);

  Serial.println(F("[SETUP] Setupping MQTT Client..."));
  // Event callbacks
  mqttClient.onConnect(_onMQTTConnect);
  mqttClient.onDisconnect(_onMQTTDisconnect);
  mqttClient.onSubscribe(_onMQTTSubscribe);
  mqttClient.onMessage(_onMQTTMessage);
  // Settings
  mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);

  connectToWiFi(WIFI_SSID, WIFI_PSWD);

  Serial.println(F("[SETUP] Done :-)"));
} // end config()




void loop() {
  // Check MQTT connection
  if (needsMQTTreconnection) {
    currentMillis = millis();
    if ((currentMillis - timeOfLastReconnect) > 5000) {
      connectToMQTTBroker();
    }
  }





} // end loop()