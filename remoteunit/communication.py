from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.client import MQTTMessage
from json import dumps as jsondumps

import settings as cfg


def payloadToList(pl: bytes | bytearray, signed: bool) -> list:
    """Converts an MQTT payload to `list[int]`

    Parameters
    ----------
    pl : bytes | bytearray
        The payload as received by the MQTT handler.
    signed : bool
        Whether the bytes are to be interpreted in 2's complement (--> signed ints) or not (--> unsigned ints)

    Returns
    -------
    list(int)
        A List object holding the converted data.
    """
    #return [int(smpl) for smpl in pl.decode().replace('[', '').replace(']', '').split(', ')]
    print(pl.hex(sep= ':', bytes_per_sep= 2))
    return [int.from_bytes(bytes= pl[i:i+2], byteorder= 'big', signed= signed) for i in range(0, len(pl), 2)]


class MQTTManager:
    """Acts as a proxy to handle the MQTT communication.
    """

    def _sendStartupData(self):
        """Sends the configuration data to the `proximalunit`.
        """
        pl = {
              "MQTT_TOPIC_PREFIX": cfg.MQTT_TOPIC_PREFIX,
              "BIOSIGNALS": cfg.BIOSIGNALS
             }
        pl = jsondumps(pl)
        print(f"[____] . Configuration string for proximal unit is: {pl}")

        print(f"[MQTT] . Sending configuration string @ topic {cfg.MQTT_TOPIC_CFG}...")
        self._c.publish(topic= cfg.MQTT_TOPIC_CFG,
                    payload= pl,
                    qos= 1, # At least once
                    retain= True
                    )
        

    def _do_subscriptions(self):
        """Subscribes to notable topics.
        """
        print(f"[MQTT] . Subscribing to biosignals' topics...")
        for t in cfg.MQTT_TOPICS:
            self._c.subscribe(topic= t,
                             qos= 2 # exactly once
                            )
            print(f"[MQTT] . . Subscribed to topic: {t}")
        print("[MQTT] . Subscribing to configuration topic...")
        self._c.subscribe(topic= cfg.MQTT_TOPIC_CFG, qos= 2)


    def _onConnect(self, client, userdata, flags, rc):
            """ Callback function for connection attempts. Checks the return code of the attempt.
            """
            if rc == 0:
                print("[MQTT] . Connection to MQTT broker was successful!")
                print("[MQTT] Performing preliminary operations...")
                self._do_subscriptions()
                self._sendStartupData()
                print("[MQTT] Ready for normal operations!! :-)")

            else:
                print (f"[MQTT] . ERROR: connection to broker failed with response code: {rc}.")


    def _onDataMessage(self, client, userdata, msg: MQTTMessage):
        """Callback function for handling of incoming data messages.
        This callback is invoked everytime a message is received in a subtopic of `MQTT_TOPIC_PREFIX`.
        """

        signalName: str = msg.topic.removeprefix(f"{cfg.MQTT_TOPIC_PREFIX}")
        #print(f"On signal {signalName}, Received data payload: {msg.payload}")
        self.samples[signalName]['old'] = self.samples[signalName]['new'] # Store old data: may be needed if pkt was received before finishing plotting all samples of previous batch
        self.samples[signalName]['new'] = payloadToList(msg.payload, signalName in cfg.SIGNED_BIOSIGNALS)
        self.newData[signalName] = True # Notify that new data was received, for this specific signal


    def _onConfigMessage(self, client, userdata, msg:MQTTMessage):
        """Callback function for handling of incoming configuration messages.
        This callback is invoked everytime a message is received in topic `MQTT_TOPIC_CFG`.
        """
        print(f"[MQTT] Got Config msg: {msg.payload}")


    def __init__(self,
                 samplesDict: dict[str, dict[str, list[int]]],
                 newData: dict[str, bool]):
        """Creates an MQTTClient, configures it, and connects it to a broker.
        The client itself will be accessible under class property `c`. 

        Args:
            samplesDict (dict[str, dict[str, list[int]]]): Reference to the dictionary holding all current and 1-step old sample packets, for each signal. Can be an empty dict.
            newData (dict[str, bool]): Dictionary specifying, for each signal, if a new packet containing samples has arrived. Can be an empty dict.
        """
        self.samples: dict[str, dict[str, list[int]]] = samplesDict
        self.newData: dict[str, bool] = newData

        hostname = cfg.MQTT_BROKER_ADDR
        port = cfg.MQTT_BROKER_PORT

        print("[MQTT] Instatiating MQTT Client...")
        self._c = MQTTClient()
        self._c.on_connect = self._onConnect
        self._c.message_callback_add(sub= f"{cfg.MQTT_TOPIC_PREFIX}+",
                            callback= self._onDataMessage)
        self._c.message_callback_add(sub= cfg.MQTT_TOPIC_CFG,
                            callback= self._onConfigMessage)

        print(f"[MQTT] Connecting to broker {hostname}@{port}...")
        self._c.connect(host= hostname,
                       port= port)

    @property
    def c(self):
        """The underlying MQTT Client managed by this instance of MQTTManager.

        Returns:
            paho.mqtt.client.Client: The MQTT Client.
        """
        return self._c
        
