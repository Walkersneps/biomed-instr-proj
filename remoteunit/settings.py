BIOSIGNALS: dict[str, dict[str, int]] = {"ECG": {"fsample": 300,
                                                 "fpacket": 4,
                                                 "overlay": 10
                                                },
                                         "PPG": {"fsample": 300,
                                                 "fpacket": 4,
                                                 "overlay": 10}
                                         #"GSR"
                                        }


MQTT_BROKER_ADDR: str = "localhost"
MQTT_BROKER_PORT: int = 1883
MQTT_TOPIC_CFG: str = "cfg"
MQTT_TOPIC_PREFIX: str = "signal/"




# DERIVED VALUES #
MQTT_TOPICS: list[str] = [f"{MQTT_TOPIC_PREFIX}{biosig}" for biosig in BIOSIGNALS]
