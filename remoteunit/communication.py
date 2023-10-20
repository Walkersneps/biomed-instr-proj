import settings as cfg
from paho.mqtt.client import Client as MQTTClient
from json import dumps as jsondumps

def _sendStartupData(client: MQTTClient):
    pl = {"MQTT_TOPIC_PREFIX": cfg.MQTT_TOPIC_PREFIX,
          "BIOSIGNALS": cfg.BIOSIGNALS
         }
    pl = jsondumps(pl)
    print(f"[____] . Configuration string for proximal unit is: {pl}")

    print(f"[MQTT] . Sending configuration string @ topic {cfg.MQTT_TOPIC_CFG}...")
    client.publish(topic= cfg.MQTT_TOPIC_CFG,
                   payload= pl,
                   qos= 1, # At least once
                   retain= True
                   )
    
def _do_subscriptions(client: MQTTClient):
    print(f"[MQTT] . Subscribing to biosignals' topics...")
    for t in cfg.MQTT_TOPICS:
        client.subscribe(topic= t,
                         qos= 2 # exactly once
                        )
        print(f"[MQTT] . . Subscribed to topic: {t}")
    print("[MQTT] . Subscribing to configuration topic...")
    client.subscribe(topic= cfg.MQTT_TOPIC_CFG, qos= 2)


def initMQTT() -> MQTTClient:
    def _onConnect(client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] . Connection to MQTT broker was successful!")
            print("[MQTT] Performing preliminary operations...")
            _do_subscriptions(client)
            _sendStartupData(client)
            print("[MQTT] Ready for normal operations!! :-)")

        else:
            print (f"[MQTT] . ERROR: connection to broker failed with response code: {rc}.")

    hostname = cfg.MQTT_BROKER_ADDR
    port = cfg.MQTT_BROKER_PORT

    print("[MQTT] Instatiating MQTT Client...")
    c = MQTTClient()
    c.on_connect = _onConnect

    print(f"[MQTT] Connecting to broker {hostname}@{port}...")
    c.connect(host= hostname,
              port= port)
    
    return c
    
