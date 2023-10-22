# o-o-o-o ACQUISITION SYSTEM SETTINGS o-o-o-o #
# NB!!! Make sure that 'fsample' is an integer multiple of 'fpacket' !!!
BIOSIGNALS: dict[str, dict[str, int]] = {"ECG": {"fsample": 300,
                                                 "fpacket": 4,
                                                 "overlay": 10
                                                },
                                         "PPG": {"fsample": 300,
                                                 "fpacket": 4,
                                                 "overlay": 10}
                                         #"GSR"
                                        }

# o-o-o-o MQTT SETTINGS #
MQTT_BROKER_ADDR: str = "broker.hivemq.com" # address of the MQTT broker
MQTT_BROKER_PORT: int = 1883 # TCP port of the MQTT broker
MQTT_TOPIC_CFG: str = "cfg" # topic on which remoteunit and proximalunit will exchange configuration information. NB: this must be hardcoded in the proximalunit firmware.
MQTT_TOPIC_PREFIX: str = "signal/" # common prefix of the topics on which proximalunit should send the acquired samples

# o-o-o-o GUI SETTINGS o-o-o-o #
#FRAMERATE_PLOT: int = 




# o-o-o-o DERIVED VALUES o-o-o-o #
# (do not edit below this point)
MQTT_TOPICS: list[str] = [f"{MQTT_TOPIC_PREFIX}{biosig}" for biosig in BIOSIGNALS]
PACKET_SIZES: dict[str, int] = {signal: int(props['fsample']/props['fpacket']) for signal, props in BIOSIGNALS.items()}
OVERLAY_SIZES: dict[str, int] = {signal: int(props['overlay']) for signal, props in BIOSIGNALS.items()}