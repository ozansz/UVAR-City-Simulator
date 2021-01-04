import os
import sys
import json
import math
import time
import random
import pickle
import networkx as nx
from enum import Enum
from threading import Timer
import matplotlib.pyplot as plt
from datetime import datetime as dt
from collections import defaultdict

from uvar_constructs import UVARMessageTypes, UVARMobileType, UVARSPacket

from simulation import City

from Channels import P2PFIFOPerfectChannel
from LinkLayers.GenericLinkLayer import LinkLayer
from Ahc import (TickerComponentModel, ComponentModel, Event,
                                 ConnectorTypes, Topology, ComponentRegistry,
                                 GenericMessagePayload, GenericMessageHeader,
                                 GenericMessage, EventTypes, MessageDestinationIdentifiers)

registry = ComponentRegistry()



TICKS_PER_SECOND = 1
SLEEP_PER_SIM_SEC = .1
SLEEP_PER_TICK = .2
_TICKS = 0

UVARS_RREQ_PROCESS_TIMEOUT = 2
UVARS_RREQ_TTL = 5
UVARS_UAV_RANGE = 1000


class MetricLogger(object):
    def __init__(self):
        self.__hop_logs = defaultdict(int)
        self.__packet_matcher = dict()
        self.__data_delivery = dict()

    def hop(self, packet_identifier):
        self.__hop_logs[packet_identifier] += 1

    def sending(self, packet_identifier):
        self.__packet_matcher[packet_identifier] = False

    def got_packet(self, packet_identifier):
        self.__packet_matcher[packet_identifier] = True

    def initiated(self, packet_identifier):
        self.__data_delivery[packet_identifier] = False

    def delivered(self, packet_identifier):
        self.__data_delivery[packet_identifier] = True

    def _debug(self):
        print(self.__data_delivery)
        print(self.__hop_logs)
        print(self.__packet_matcher)

    @property
    def dump(self):
        return {
            "hop_logs": self.__hop_logs,
            "matched_packets": self.__packet_matcher,
            "delivered_data_packets": self.__data_delivery,
            "metrics": {
                "PDR": self.pdr,
                "DDR": self.ddr,
                "HOP": self.avg_hops
            }
        }

    @property
    def pdr(self):
        if len(self.__packet_matcher.values()) == 0:
            return None

        return sum([1 for val in self.__packet_matcher.values() if val]) / len(self.__packet_matcher.values())

    @property
    def ddr(self):
        if len(self.__data_delivery.values()) == 0:
            return None

        return sum([1 for val in self.__data_delivery.values() if val]) / len(self.__data_delivery.values())

    #@property
    #def avg_hops(self):
    #    if len(self.__packet_matcher.values()) == 0:
    #        return None
    #
    #    return sum(self.__hop_logs.values()) / sum([1 for val in self.__packet_matcher.values() if val])

    @property
    def avg_hops(self):
        if len(self.__hop_logs.keys()) == 0:
            return None

        return sum(self.__hop_logs.values()) / len(self.__hop_logs.keys())

data_packet_identifier_string = lambda data_src, data_dst: f"{data_src}=>{data_dst}"

metric_logger = MetricLogger()

class NetworkLayerMessageTypes(Enum):
    NETMSG = "NETMSG"

# define your own message header structure
class NetworkLayerMessageHeader(GenericMessageHeader):
    pass

# define your own message payload structure
class NetworkLayerMessagePayload(GenericMessagePayload):
    pass

class OneHopBroadcastNetworkLayer(ComponentModel):
    def __init__(self, componentname, componentinstancenumber):
        self.rrep_waiting_dests = []
        self.rreqs_to_process = []
        self.state_waiting_other_rreqs = False
        self._once_sent = False
        self._dlvrd = False

        super().__init__(componentname, componentinstancenumber)
        
    def _select_path(self):
        square_dist = lambda p1, p2: ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**.5
        
        path_packet_index = None
        max_score = 0

        for index, packet in enumerate(self.rreqs_to_process):
            score = 1

            for i in range(len(packet.path)-1):
                score *= (UVARS_UAV_RANGE / square_dist(packet.path[i][1], packet.path[i+1][1]))

            if score > max_score:
                max_score = score
                path_packet_index = index

        return path_packet_index

    def process_rreqs(self):
        path_index = self._select_path()

        if path_index is None:
            #print(f"NL {self.componentinstancenumber} Calculated path is None, cancelled routing")
            return

        pkt = self.rreqs_to_process[path_index]
        rrep_packet = UVARSPacket(UVARMessageTypes.RREP, pkt.destination_id, pkt.source_id, ttl=UVARS_RREQ_TTL)
        rrep_packet.path = pkt.path[:]

        self.rreqs_to_process = []

        print(f"NL [{self.componentinstancenumber}] SELECTED PATH: {pkt.path}")
        hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST)
        payload = rrep_packet.serialize()
        msg = GenericMessage(hdr, payload)

        self._once_sent = True

        self.send_down(Event(self, EventTypes.MFRT, msg))
    def on_message_from_top(self, eventobj: Event):
        applmsg = eventobj.eventcontent
        hdr = applmsg.header
        destination = applmsg.header.messageto

        rreq_packet = UVARSPacket(UVARMessageTypes.RREQ, destination, self.componentinstancenumber, ttl=UVARS_RREQ_TTL)
        self.rrep_waiting_dests.append(destination)

        #print(f"SND {hdr.sequencenumber}")
        metric_logger.sending(hdr.sequencenumber)

        #print(f"NL {self.componentinstancenumber} will BROADCAST a message to {destination}")
        hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST)
        payload = rreq_packet.serialize()
        msg = GenericMessage(hdr, payload)

        metric_logger.initiated(data_packet_identifier_string(self.componentinstancenumber, destination))
        self.send_down(Event(self, EventTypes.MFRT, msg))

    def on_message_from_bottom(self, eventobj: Event):
        msg = eventobj.eventcontent
        hdr = msg.header
        payload = msg.payload

        #print(f"GOT {hdr.sequencenumber}")
        metric_logger.got_packet(hdr.sequencenumber)

        try:
            payload_deserialized = UVARSPacket.deserialize(payload)
        except Exception as e:
           # print(f"NL {self.componentinstancenumber} Deserialization err: {e}")
            return

        payload_deserialized.ttl -= 1

        if payload_deserialized.ttl == 0:
            #print("NL - TTL EXPIRED!")
            return

        #if self.componentinstancenumber in ("C9", "C16"):
        #    print(f"HEYOO {self.componentinstancenumber} :: '{payload_deserialized.source_id}' '{payload_deserialized.destination_id}'")

        if payload_deserialized.packet_type == UVARMessageTypes.RREQ:
            if self.appllayer.mobile_type == UVARMobileType.CAR:
                if payload_deserialized.destination_id == self.componentinstancenumber:
                    if not self._once_sent:
                        
                        if not self.state_waiting_other_rreqs:
                            
                            self.rreqs_to_process.append(payload_deserialized)
                            self.state_waiting_other_rreqs = True
                            self.timer_th = Timer(UVARS_RREQ_PROCESS_TIMEOUT, self.process_rreqs)
                            self.timer_th.start()
                        else:
                        
                            self.rreqs_to_process.append(payload_deserialized)
                else:
                    #print("NL RREQ - I am car but not dest, dropped.")
                    return
            elif self.appllayer.mobile_type == UVARMobileType.UAV:
                if payload_deserialized.source_id == self.componentinstancenumber or self.componentinstancenumber in [p[0] for p in payload_deserialized.path]:
                    #print("NL RREQ - I am already in this, dropped.")
                    return
                
                payload_deserialized.path.insert(0, (self.componentinstancenumber, self.appllayer.mobile_ptr.real_coord))
                #print(f"NL {self.componentinstancenumber} ADDED MYSELF TO PATH: {payload_deserialized.path}")
                hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST)
                payload = payload_deserialized.serialize()
                msg = GenericMessage(hdr, payload)

                metric_logger.sending(hdr.sequencenumber)
                metric_logger.hop(data_packet_identifier_string(payload_deserialized.source_id, payload_deserialized.destination_id))
                self.send_down(Event(self, EventTypes.MFRT, msg))
            else:
                #print(f"NL UNDEFINED MOBILE TYPE!!! {self.appllayer.mobile_type}")
                return
        elif payload_deserialized.packet_type == UVARMessageTypes.RREP:
            if payload_deserialized.source_id == self.componentinstancenumber:
                if not self._dlvrd:
                    self._dlvrd = True
                    print(f"NL [{self.componentinstancenumber}] GOT RREP!!")
                    metric_logger.delivered(data_packet_identifier_string(self.componentinstancenumber, payload_deserialized.destination_id))
            else:
                #print(f"NL recvd RREP but not mine, BROADCASTING.")
                hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST, MessageDestinationIdentifiers.NETWORKLAYERBROADCAST)
                payload = payload_deserialized.serialize()
                msg = GenericMessage(hdr, payload)

                metric_logger.sending(hdr.sequencenumber)
                #metric_logger.hop(data_packet_identifier_string(payload_deserialized.source_id, payload_deserialized.destination_id))
                self.send_down(Event(self, EventTypes.MFRT, msg))
class ApplicationLayerMessageHeader(GenericMessageHeader):
    pass

class ApplicationLayerMessagePayload(GenericMessagePayload):
    pass

class ApplicationLayerComponent(ComponentModel):
    def on_init(self, eventobj: Event):
        pass

    def on_message_from_bottom(self, eventobj: Event):
        applmessage = eventobj.eventcontent
        hdr = applmessage.header
        
        pass

    def transfer_data_file(self, destination_id, raw_data):
        header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, destination_id)
        payload = ApplicationLayerMessagePayload(raw_data)
        message = GenericMessage(header, payload)

        self.send_down(Event(self, EventTypes.MFRT, message))

class UVARSAdHocNode(TickerComponentModel):
    def __init__(self, componentname, componentid):
        self.appllayer = ApplicationLayerComponent("ApplicationLayer", componentid)
        self.netlayer = OneHopBroadcastNetworkLayer("NetworkLayer", componentid)
        self.linklayer = LinkLayer("LinkLayer", componentid)

        self.netlayer.appllayer = self.appllayer

        self.appllayer.uvar_data_packets_on_hold = list()

        self.appllayer.connect_me_to_component(ConnectorTypes.DOWN, self.netlayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.UP, self.appllayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
        self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.netlayer)

        self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
        self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

        super().__init__(componentname, componentid)
        
    def on_message_from_top(self, eventobj: Event):
        #print(f"{EventTypes.MFRT}    {self.componentname}.{self.componentinstancenumber}")

        # Broadcast message to all physically linked cellulars
        if eventobj.eventcontent.header.nexthop == MessageDestinationIdentifiers.LINKLAYERBROADCAST:
            for edge in Topology().G.edges:
                if edge[0] == self.componentinstancenumber:
                    Topology().nodes[edge[1]].linklayer.on_message_from_bottom(eventobj)
                elif edge[1] == self.componentinstancenumber:
                    Topology().nodes[edge[0]].linklayer.on_message_from_bottom(eventobj)
            #for uav_id in self.appllayer.mobile_ptr.uavs_in_contact:
            #    Topology().nodes[f"U{uav_id}"].linklayer.on_message_from_bottom(eventobj)
            #for car_id in self.appllayer.mobile_ptr.cars_in_contact:
            #    Topology().nodes[f"U{car_id}"].linklayer.on_message_from_bottom(eventobj)
        else:
            Topology().nodes[eventobj.eventcontent.header.nexthop].linklayer.on_message_from_bottom(eventobj)

    def assign_simclass_ptr_to_appllayer(self, car_or_uav):
        self.appllayer.mobile_ptr = car_or_uav

    def initiate_transfer(self, raw_data: bytes, destination_id: str):
        self.appllayer.transfer_data_file(destination_id, raw_data)

def gen_and_bench(transfer_pairs_count: int, cars_count: int, rank: int, simulation_steps: int):
    global _TICKS

    if not os.path.isdir("./data"):
        os.mkdir("./data")

    c = City(cars_count, rank)

    gif_file_name = f"./data/sim_{cars_count}_{rank}_{simulation_steps}.gif"
    data_file = f"./data/sim_{cars_count}_{rank}_{simulation_steps}_{str(dt.now().timestamp()).split('.')[0]}.pkl"

    c.save_simulation_with_graphics(simulation_steps, gif_file_name, data_file)

    os.system(f'ffmpeg -i {gif_file_name} -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" ./data/sim_{cars_count}_{rank}_{simulation_steps}.mp4')

    with open(data_file, "rb") as fp:
        objdict = pickle.load(fp)
    
    G = objdict[1]["network"]
    cars_1 = objdict[1]["cars"]
    uavs_1 = objdict[1]["uavs"]

    topo = Topology()
    topo.construct_from_graph(G, UVARSAdHocNode, P2PFIFOPerfectChannel)

    for node_id in topo.nodes:
        if node_id[0] == "U":
            topo.nodes[node_id].assign_simclass_ptr_to_appllayer(uavs_1[int(node_id[1:])])
        if node_id[0] == "C":
            topo.nodes[node_id].assign_simclass_ptr_to_appllayer(cars_1[int(node_id[1:])])

    topo.start()

    #topo.nodes["C50"].initiate_transfer(b"testdata", "C1") # 27

    transfer_pairs = []

    for _ in range(transfer_pairs_count):
        car1 = random.randint(0, cars_count-1)
        car2 = random.randint(0, cars_count-1)

        while car1 == car2 or (car1, car2) in transfer_pairs:
            car1 = random.randint(0, cars_count-1)
            car2 = random.randint(0, cars_count-1)

        transfer_pairs.append((car1, car2))

    print(transfer_pairs)

    for c1, c2 in transfer_pairs:
        topo.nodes[f"C{c1}"].initiate_transfer(b"testdata", f"C{c2}")

    try:
        for i in range(2, len(objdict) + 1):
            for tps in range(TICKS_PER_SECOND):
                _TICKS += 1

                print("=" * 15, i - 1, "::", tps + 1, "=" * 15)

                #print("*** ticks")
                for node_tag, adhoc_node in topo.nodes.items():
                    adhoc_node.simulation_tick()

                time.sleep(SLEEP_PER_TICK)

            #print("*** topo.update")
            topo.update_graph_edges(objdict[i]["network"])

            #print("*** node.update")
            for node_id in topo.nodes:
                if node_id[0] == "U":
                    new_uav = objdict[i]["uavs"][int(node_id[1:])]
                    assert topo.nodes[node_id].appllayer.mobile_ptr != new_uav
                    topo.nodes[node_id].appllayer.mobile_ptr = new_uav
                if node_id[0] == "C":
                    new_car = objdict[i]["cars"][int(node_id[1:])]
                    assert topo.nodes[node_id].appllayer.mobile_ptr != new_car
                    topo.nodes[node_id].appllayer.mobile_ptr = new_car

            time.sleep(SLEEP_PER_SIM_SEC)
    except KeyboardInterrupt:
        pass

    print(f"\nPDR: {metric_logger.pdr}")
    print(f"DDR: {metric_logger.ddr}")
    print(f"HOP: {metric_logger.avg_hops}")
    #metric_logger._debug()

    with open(f"./data/metrics_{cars_count}_{rank}_{simulation_steps}_{str(dt.now().timestamp()).split('.')[0]}.dat", "w") as fp:
        json.dump(metric_logger.dump, fp)

def read_and_bench(filepath: str, transfer_pairs_count: int):
    global _TICKS

    with open(filepath, "rb") as fp:
        objdict = pickle.load(fp)
    
    cars_count = len(objdict[1]["cars"])
    simulation_steps = len(objdict)

    G = objdict[1]["network"]
    cars_1 = objdict[1]["cars"]
    uavs_1 = objdict[1]["uavs"]

    topo = Topology()
    topo.construct_from_graph(G, UVARSAdHocNode, P2PFIFOPerfectChannel)

    for node_id in topo.nodes:
        if node_id[0] == "U":
            topo.nodes[node_id].assign_simclass_ptr_to_appllayer(uavs_1[int(node_id[1:])])
        if node_id[0] == "C":
            topo.nodes[node_id].assign_simclass_ptr_to_appllayer(cars_1[int(node_id[1:])])

    topo.start()

    #topo.nodes["C50"].initiate_transfer(b"testdata", "C1") # 27

    transfer_pairs = []

    for _ in range(transfer_pairs_count):
        car1 = random.randint(0, cars_count-1)
        car2 = random.randint(0, cars_count-1)

        while car1 == car2 or (car1, car2) in transfer_pairs:
            car1 = random.randint(0, cars_count-1)
            car2 = random.randint(0, cars_count-1)

        transfer_pairs.append((car1, car2))

    print(transfer_pairs)

    for c1, c2 in transfer_pairs:
        topo.nodes[f"C{c1}"].initiate_transfer(b"testdata", f"C{c2}")

    try:
        for i in range(2, len(objdict) + 1):
            for tps in range(TICKS_PER_SECOND):
                _TICKS += 1

                print("=" * 15, i - 1, "::", tps + 1, "=" * 15)
                
                #print("*** ticks")
                for node_tag, adhoc_node in topo.nodes.items():
                    adhoc_node.simulation_tick()

                time.sleep(SLEEP_PER_TICK)

            #print("*** topo.update")
            topo.update_graph_edges(objdict[i]["network"])

            #print("*** node.update")
            for node_id in topo.nodes:
                if node_id[0] == "U":
                    new_uav = objdict[i]["uavs"][int(node_id[1:])]
                    assert topo.nodes[node_id].appllayer.mobile_ptr != new_uav
                    topo.nodes[node_id].appllayer.mobile_ptr = new_uav
                if node_id[0] == "C":
                    new_car = objdict[i]["cars"][int(node_id[1:])]
                    assert topo.nodes[node_id].appllayer.mobile_ptr != new_car
                    topo.nodes[node_id].appllayer.mobile_ptr = new_car

            time.sleep(SLEEP_PER_SIM_SEC)
    except KeyboardInterrupt:
        pass

    print(f"\nPDR: {metric_logger.pdr}")
    print(f"DDR: {metric_logger.ddr}")
    print(f"HOP: {metric_logger.avg_hops}")
    #metric_logger._debug()

    metrics_save_path = f"./data/metrics_{cars_count}_FILE_{simulation_steps}_{str(dt.now().timestamp()).split('.')[0]}.dat"

    with open(metrics_save_path, "w") as fp:
        json.dump(metric_logger.dump, fp)

    print(f"[i] Dumped metrics to {metrics_save_path}")
    print(f"Bye :)")

if __name__ == "__main__":
    subcmd = sys.argv[1]

    if len(sys.argv) < 4 or subcmd not in ("gen", "file"):
        print(f"Usages:")
        print(f"  python3 {sys.argv[0]} gen <transfer_pairs_count:int> <cars_count:int> <rank:int> <simulation_steps:int>")
        print(f"  python3 {sys.argv[0]} file <filepath:str> <transfer_pairs_count:int>")
        sys.exit(0)

    if subcmd == "gen":
        transfer_pairs_count = int(sys.argv[2])
        cars_count = int(sys.argv[3])
        rank = int(sys.argv[4])
        simulation_steps = int(sys.argv[5])

        gen_and_bench(
            transfer_pairs_count=transfer_pairs_count,
            cars_count=cars_count, rank=rank,
            simulation_steps=simulation_steps
        )
    elif subcmd == "file":
        filepath = sys.argv[2]
        transfer_pairs_count = int(sys.argv[3])

        read_and_bench(
            filepath=filepath,
            transfer_pairs_count=transfer_pairs_count
        )