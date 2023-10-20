import settings as cfg
from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.client import MQTTMessage
from json import dumps as jsondumps

class MQTTManager:
    def _sendStartupData(self):
        pl = {"MQTT_TOPIC_PREFIX": cfg.MQTT_TOPIC_PREFIX,
            "BIOSIGNALS": cfg.BIOSIGNALS
            }
        pl = jsondumps(pl)
        print(f"[____] . Configuration string for proximal unit is: {pl}")

        print(f"[MQTT] . Sending configuration string @ topic {cfg.MQTT_TOPIC_CFG}...")
        self.c.publish(topic= cfg.MQTT_TOPIC_CFG,
                    payload= pl,
                    qos= 1, # At least once
                    retain= True
                    )
        
    def _do_subscriptions(self):
        print(f"[MQTT] . Subscribing to biosignals' topics...")
        for t in cfg.MQTT_TOPICS:
            self.c.subscribe(topic= t,
                             qos= 2 # exactly once
                            )
            print(f"[MQTT] . . Subscribed to topic: {t}")
        print("[MQTT] . Subscribing to configuration topic...")
        self.c.subscribe(topic= cfg.MQTT_TOPIC_CFG, qos= 2)

    def _onConnect(self, client, userdata, flags, rc):
            if rc == 0:
                print("[MQTT] . Connection to MQTT broker was successful!")
                print("[MQTT] Performing preliminary operations...")
                self._do_subscriptions()
                self._sendStartupData()
                print("[MQTT] Ready for normal operations!! :-)")

            else:
                print (f"[MQTT] . ERROR: connection to broker failed with response code: {rc}.")

    def _onDataMessage(self, client, userdata, msg: MQTTMessage):
        signalName: str = msg.topic.removeprefix(f"{cfg.MQTT_TOPIC_PREFIX}")
        print(f"Received data payload: {msg.payload}")
        #self.samples[signalName]['old'] = samples[signalName]['new']
        #self.samples[signalName]['new'] = msg.payload

    def _onConfigMessage(self, client, userdata, msg:MQTTMessage):
        print(f"[MQTT] Got Config msg: {msg.payload}")


    def __init__(self, samplesDict):
        self.samples = samplesDict

        hostname = cfg.MQTT_BROKER_ADDR
        port = cfg.MQTT_BROKER_PORT

        print("[MQTT] Instatiating MQTT Client...")
        self.c = MQTTClient()
        self.c.on_connect = self._onConnect
        self.c.message_callback_add(sub= f"{cfg.MQTT_TOPIC_PREFIX}/+",
                            callback= self._onDataMessage)
        self.c.message_callback_add(sub= cfg.MQTT_TOPIC_CFG,
                            callback= self._onConfigMessage)

        print(f"[MQTT] Connecting to broker {hostname}@{port}...")
        self.c.connect(host= hostname,
                port= port)

        
