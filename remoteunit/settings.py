# o-o-o-o ACQUISITION SYSTEM SETTINGS o-o-o-o #
# NB!!! Make sure that 'fsample' is an integer multiple of 'fpacket' !!!
BIOSIGNALS: dict[str, dict[str, float]] = {"ECG": {
                                                   "fsample": 200,
                                                   "fpacket": 1,
                                                   "overlay": 20,
                                                   "npacket": 200,
                                                   "priority": 10
                                                },
                                           "PPGRed": {
                                                   "fsample": 200,
                                                   "fpacket": 1,
                                                   "overlay": 30,
                                                   "npacket": 200,
                                                   "priority": 10
                                                },
                                           "PPGIR": {
                                                "fsample": 200,
                                                "fpacket": 1,
                                                "overlay": 30,
                                                "npacket": 200,
                                                "priority": 10
                                        },
                                        }
SIGNED_BIOSIGNALS = ["ECG"]

# o-o-o-o BLUETOOTH SETTINGS o-o-o-o #
BT_MAC_REMOTEUNIT = "C0:49:EF:6B:D8:C2"
BT_PORT = 1




# o-o-o-o DERIVED VALUES o-o-o-o #
# (do not edit below this point)
PACKET_SIZES: dict[str, int] = {signal: int(props['fsample']/props['fpacket']) for signal, props in BIOSIGNALS.items()}
OVERLAY_SIZES: dict[str, int] = {signal: int(props['overlay']) for signal, props in BIOSIGNALS.items()}

FRAMERATE_PLOT: dict[str, int] = {signal: int((PACKET_SIZES[signal] - (3*OVERLAY_SIZES[signal]/4)) * props['fpacket']) for signal, props in BIOSIGNALS.items()}  #(packet_size - overlay) * fpacket = [samplesToPlot/packet] * [packets/sec] = [samplesToPlot/sec]
#FRAMERATE_PLOT: dict[str, int] = {signal: int(PACKET_SIZES[signal] * props['fpacket']) for signal, props in BIOSIGNALS.items()}
PERIOD_PLOT: dict[str, int] = {signal: int((1/framerate) * 1000) for signal, framerate in FRAMERATE_PLOT.items()} # [ms]
print(PERIOD_PLOT['ECG'])