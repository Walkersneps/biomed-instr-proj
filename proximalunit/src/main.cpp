#include <map>
#include <unordered_map>
#include <cstring>
#include <string>
#include <Arduino.h>
#include <WiFi.h>
#include <espMqttClientAsync.h>
#include <ArduinoJson.h>

// ## o-o-o-o SETTINGS o-o-o-o ##
// ##############################
// ###  Wifi Settings ###
#define WIFI_SSID "ap_ssid"
#define WIFI_PSWD "password"

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
#define IDX_ECG 0
#define IDX_PPG 1
#define IDX_GSR 2
#define IDX_TEMP 3
#define IDX_RVOL 4

// MQTT Management stuff
espMqttClientAsync mqttClient; // The actual MQTT Client instance
bool needsMQTTreconnection = false;
uint32_t timeOfLastReconnect = 0;
uint32_t currentMillis;

// Handling of big/batched MQTT messages
const size_t maxPayloadSize = 8192; // Payloads with a total size exceeding this number will be discarded.
uint8_t* payloadBuffer = nullptr;
size_t payloadBufferSize = 0;
size_t payloadBufferIdx = 0;

// Topic/Callback pairing
struct MatchTopic { // Defines how to look for a topic in the map `topicCallbacks`
  bool operator()(const char* a, const char* b) const {
    return strcmp(a, b) < 0;
  }
};
std::map<const char*, espMqttClientTypes::OnMessageCallback, MatchTopic> topicCallbacks; // This map will store the couples {topicName -> callbackFunc}, allowing messages coming from different topics to be handled indipendently.

// Operative Settings
JsonDocument settings;
//typedef std::unordered_map<std::string, uint8_t> Settings; // Defines a dictionary of type {`settingName`: `value`}
//std::unordered_map<std::string, Settings> signalSettings; // 2-level dict of type {`signalName`: {`settingName`: `value`}}

// FreeRTOS Tasks handles
TaskHandle_t* taskHandles[MAX_SIGNALS] = {nullptr}; // Stores handles pointing to created RTOS tasks


// FreeRTOS Tasks
void vTask_SampleECG(void *pvParameters) {
  JsonObject config = *(JsonObject *)pvParameters;
  const int fsample = config["fsample"].as<int>();
  const int overlay = config["overlay"].as<int>();
  const int npacket = config["npacket"].as<int>();
  const bool dataOk = (fsample && overlay && npacket);
  if (!dataOk) Serial.println(F("[ERROR] Uncastable settings for ECG!!"));

  static int* samples;
  samples = (int*)pvPortMalloc(npacket * sizeof(int));
  int sampleIndex = 0;

  const TickType_t samplePeriod = pdMS_TO_TICKS(int(1000 / fsample));
  Serial.printf("[ECG] A sample will be acquired every %d ms, aka every %d ticks.\n", pdTICKS_TO_MS(samplePeriod), samplePeriod);
  BaseType_t xWasDelayed;
  TickType_t xLastWakeTime = xTaskGetTickCount();

  while (dataOk) {
    xWasDelayed = xTaskDelayUntil(&xLastWakeTime, samplePeriod);

    // TODO: implement overlay!
    // TODO: acquire sample
    samples[sampleIndex] = 0;
    sampleIndex++;

    if (xWasDelayed == pdTRUE) Serial.println(F("[ECG] ! Sampling was delayed!"));

    if (sampleIndex >= npacket) {
      // TODO: send via mqtt
      sampleIndex = 0;
    }

  }

  // TODO: !!! ensure this is run also on task deletion !!!
  vPortFree(samples);
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

    if (!strcmp(signalName, "ECG")) {
      Serial.println(F("[MAIN] Creating freeRTOS task for ECG..."));
      xTaskCreatePinnedToCore(vTask_SampleECG, "task_ECG", 2048, &sett, 10, taskHandles[IDX_ECG], APP_CPU_NUM);
    } else if (!strcmp(signalName, "PPG")) {
      Serial.println(F("[MAIN] Creating freeRTOS task for PPG..."));
      //xTaskCreatePinnedToCore(vTask_SamplePPG, "task_PPG", 2048, &sett, 10, taskHandles[IDX_ECG], APP_CPU_NUM);
    } else {
      Serial.printf("[MAIN] Signal `%s` unknown. Can't proceed.\n", signalName);
    }
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

  const char* config_topic = settings["MQTT_TOPIC_PREFIX"];
  JsonObject json = settings.as<JsonObject>(); // Get smart object reference
  for (JsonPair pair: json) {
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