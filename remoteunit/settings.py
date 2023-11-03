# o-o-o-o ACQUISITION SYSTEM SETTINGS o-o-o-o #
# NB!!! Make sure that 'fsample' is an integer multiple of 'fpacket' !!!
BIOSIGNALS: dict[str, dict[str, float]] = {"ECG": {
                                                   "fsample": 10,
                                                   "fpacket": 0.5,
                                                   "overlay": 20,
                                                   "npacket": 200,
                                                   "priority": 10
                                                },
                                           "PPG": {
                                                   "fsample": 300,
                                                   "fpacket": 2,
                                                   "overlay": 30,
                                                   "npacket": 100,
                                                   "priority": 10
                                                },
                                           "TMP": {
                                                   "fsample": 0.5,
                                                   "npacket": 5,
                                                   "overlay": 1,
                                                   "priority": 5,
                                                   "fpacket": 2
                                                }
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

FRAMERATE_PLOT: dict[str, int] = {signal: int((PACKET_SIZES[signal] - (3*OVERLAY_SIZES[signal]/4)) * props['fpacket']) for signal, props in BIOSIGNALS.items()}  #(packet_size - overlay) * fpacket = [samplesToPlot/packet] * [packets/sec] = [samplesToPlot/sec]
#FRAMERATE_PLOT: dict[str, int] = {signal: int(PACKET_SIZES[signal] * props['fpacket']) for signal, props in BIOSIGNALS.items()}
PERIOD_PLOT: dict[str, int] = {signal: int((1/framerate) * 1000) for signal, framerate in FRAMERATE_PLOT.items()} # [ms]
print(PERIOD_PLOT['ECG'])