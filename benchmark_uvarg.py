import os
import sys
import json
import time
import random
import pickle
import networkx as nx
from enum import Enum
import matplotlib.pyplot as plt
from datetime import datetime as dt
from collections import defaultdict

from uvar_constructs import UVARGPacket, UVARMessageTypes, UVARMobileType

from simulation import City

from Channels import P2PFIFOPerfectChannel
from LinkLayers.GenericLinkLayer import LinkLayer
from Ahc import (TickerComponentModel, ComponentModel, Event,
                                 ConnectorTypes, Topology, ComponentRegistry,
                                 GenericMessagePayload, GenericMessageHeader,
                                 GenericMessage, EventTypes)

registry = ComponentRegistry()



TICKS_PER_SECOND = 1
SLEEP_PER_SIM_SEC = .1
SLEEP_PER_TICK = .2
_TICKS = 0



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

class OneHopNetworkLayer(ComponentModel):
    def __init__(self, componentname, componentinstancenumber):
        super().__init__(componentname, componentinstancenumber)
        
    def on_message_from_top(self, eventobj: Event):
        applmsg = eventobj.eventcontent
        destination = applmsg.header.messageto
        nexthop = destination

        #print(f"NL {self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
        hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination, nexthop)
        payload = eventobj.eventcontent
        msg = GenericMessage(hdr, payload)

        print(f"SND {hdr.sequencenumber}")
        metric_logger.sending(hdr.sequencenumber)
        self.send_down(Event(self, EventTypes.MFRT, msg))

    def on_message_from_bottom(self, eventobj: Event):
        msg = eventobj.eventcontent
        hdr = msg.header
        payload = msg.payload

        print(f"GOT {hdr.sequencenumber}")
        metric_logger.got_packet(hdr.sequencenumber)

        if hdr.messageto == self.componentinstancenumber or hdr.messageto == MessageDestinationIdentifiers.NETWORKLAYERBROADCAST:  
            self.send_up(Event(self, EventTypes.MFRB, payload))
            #print(f"NL I received a message to {hdr.messageto} and I am {self.componentinstancenumber}")
        else:
            destination = hdr.messageto
            nexthop = destination

            newhdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination, nexthop)
            newpayload = eventobj.eventcontent.payload
            msg = GenericMessage(newhdr, newpayload)
            self.send_down(Event(self, EventTypes.MFRT, msg))
            #print(f"NL {self.componentinstancenumber} will FORWARD a message to {destination} over {nexthop}")

class PacketHoldType(Enum):
    INITIAL = "INITIAL"
    FORWARD = "FORWARD"

class ApplicationLayerMessageHeader(GenericMessageHeader):
    pass

class ApplicationLayerMessagePayload(GenericMessagePayload):
    pass

class ApplicationLayerComponent(ComponentModel):
    def on_init(self, eventobj: Event):
        pass

    def process_initial(self, dest, data):
        dest_car_id = int(dest[1:])

        if dest == self.componentinstancenumber:
            print(f"[{self.componentinstancenumber}] RECVD")
            return
        elif dest_car_id in self.mobile_ptr.cars_in_contact:
            print(f"[{self.componentinstancenumber}] Dest is neighbor")

            data_packet_serialized = UVARGPacket(dest, self.componentinstancenumber,
                None, data, None).serialize()

            header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, dest)
            payload = ApplicationLayerMessagePayload(data_packet_serialized)
            message = GenericMessage(header, payload)

            metric_logger.initiated(data_packet_identifier_string(self.componentinstancenumber, dest))
            self.send_down(Event(self, EventTypes.MFRT, message))
        elif len(self.mobile_ptr.cars_in_contact) > 0:
            I_next = self.mobile_ptr.next_intersection_to_target_car(dest_car_id)

            if I_next is None:
                print(f"[{self.componentinstancenumber}] I_next is None, will hold for a while")
                self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                return

            print(f"[{self.componentinstancenumber}] I_next is {I_next}")

            next_hop = self.mobile_ptr.farthest_neighbor_car_near_intersection_point(I_next)[0]

            if next_hop is None:
                print(f"[{self.componentinstancenumber}] next_hop is None, will hold for a while")
                self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                return

            next_hop = f"C{next_hop}"
            print(f"[{self.componentinstancenumber}] Will send to neighbor {next_hop} for I_next {I_next}")

            data_packet_serialized = UVARGPacket(dest, self.componentinstancenumber,
                I_next, data, None).serialize()

            header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, next_hop)
            payload = ApplicationLayerMessagePayload(data_packet_serialized)
            message = GenericMessage(header, payload)

            metric_logger.initiated(data_packet_identifier_string(self.componentinstancenumber, dest))
            self.send_down(Event(self, EventTypes.MFRT, message))
        else:
            print(f"[{self.componentinstancenumber}] No neighbors, will hold for a while")
            self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))

    def process_forward_car(self, serialized_data):
        dest = serialized_data.destination_id
        src = serialized_data.source_id
        data = serialized_data.raw_data
        pkt_i_next = serialized_data.next_intersection
        dest_car_id = int(dest[1:])

        print(f"[{self.componentinstancenumber}] FWD-CAR Dest: {dest}, src: {src}, i_next: {pkt_i_next}")

        if dest == self.componentinstancenumber:
            print(f"[{self.componentinstancenumber}] RECVD")
            return
        elif dest_car_id in self.mobile_ptr.cars_in_contact:
            data_packet_serialized = UVARGPacket(dest, src,
                None, data, None).serialize()

            header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, dest)
            payload = ApplicationLayerMessagePayload(data_packet_serialized)
            message = GenericMessage(header, payload)

            metric_logger.hop(data_packet_identifier_string(src, dest))
            self.send_down(Event(self, EventTypes.MFRT, message))
        elif len(self.mobile_ptr.cars_in_contact) > 0:
            I_next = self.mobile_ptr.next_intersection_to_target_car(dest_car_id)
            
            if I_next is None:
                print(f"[{self.componentinstancenumber}] I_next is None, will hold for a while")
                self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                return

            print(f"[{self.componentinstancenumber}] I_next is {I_next}")
            next_hop = self.mobile_ptr.farthest_neighbor_car_near_intersection_point(I_next)[0]

            if next_hop is None:
                print(f"[{self.componentinstancenumber}] next_hop is None, will hold for a while")
                self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                return

            next_hop = f"C{next_hop}"

            data_packet_serialized = UVARGPacket(dest, src,
                I_next, data, None).serialize()

            header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, next_hop)
            payload = ApplicationLayerMessagePayload(data_packet_serialized)
            message = GenericMessage(header, payload)

            metric_logger.hop(data_packet_identifier_string(src, dest))
            self.send_down(Event(self, EventTypes.MFRT, message))
        else:
            if pkt_i_next is not None:
                print(f"[{self.componentinstancenumber}] UAV Found I_next: {pkt_i_next}")
                I_next = pkt_i_next
            else:
                I_next = next_intersection_to_target_car(dest_car_id)

                if I_next is None:
                    print("[{self.componentinstancenumber}] UAV I_next is None, will hold for a while")
                    self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                    return

            uav_id = self.mobile_ptr.nearest_uav_near_intersection(I_next)[0]

            if uav_id is None:
                print("[{self.componentinstancenumber}] No neighbor car or UAVs, will hold for a while")
                self.uvar_data_packets_on_hold.append((PacketHoldType.INITIAL, dest, data))
                return
            
            uav_send_me_to_car_in_section = (self.mobile_ptr.my_section_joint_near_joint(I_next), I_next)

            data_packet_serialized = UVARGPacket(dest, src,
                I_next, data, uav_send_me_to_car_in_section).serialize()

            uav_id = f"U{uav_id}"

            header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, uav_id)
            payload = ApplicationLayerMessagePayload(data_packet_serialized)
            message = GenericMessage(header, payload)

            metric_logger.hop(data_packet_identifier_string(src, dest))
            self.send_down(Event(self, EventTypes.MFRT, message))

    def process_forward_uav(self, serialized_data):
        dest = serialized_data.destination_id
        src = serialized_data.source_id
        data = serialized_data.raw_data
        pkt_i_next = serialized_data.next_intersection
        uav_send_me_to_car_in_section = serialized_data.uav_send_me_to_car_in_section
        dest_car_id = int(dest[1:])

        print(f"[{self.componentinstancenumber}] FWD-UAV Dest: {dest}, src: {src}, i_next: {pkt_i_next}, uav_send_me_to_car_in_section: {uav_send_me_to_car_in_section}")

        if pkt_i_next is None:
            print(f"[{self.componentinstancenumber}] NODATA at pkt_i_next, dropping")
            return

        if uav_send_me_to_car_in_section is None:
            print(f"[{self.componentinstancenumber}] NODATA at uav_send_me_to_car_in_section, dropping")
            return

        next_hop = self.mobile_ptr.nearest_car_in_section_near_intersection(uav_send_me_to_car_in_section, pkt_i_next)[0]

        if next_hop is None:
            print(f"[{self.componentinstancenumber}] No near cars in {uav_send_me_to_car_in_section} near I_next: {I_next}, will hold the packet")
            self.uvar_data_packets_on_hold.append((PacketHoldType.FORWARD, serialized_data))
            return

        next_hop = f"C{next_hop}"

        data_packet_serialized = UVARGPacket(dest, src,
                pkt_i_next, data, uav_send_me_to_car_in_section).serialize()

        header = ApplicationLayerMessageHeader(UVARMessageTypes.DATA, self.componentinstancenumber, next_hop)
        payload = ApplicationLayerMessagePayload(data_packet_serialized)
        message = GenericMessage(header, payload)

        metric_logger.hop(data_packet_identifier_string(src, dest))
        self.send_down(Event(self, EventTypes.MFRT, message))

    def simulation_tick(self):
        to_reprocess = self.uvar_data_packets_on_hold[:]
        self.uvar_data_packets_on_hold = []

        while len(to_reprocess) > 0:
            queue_item = to_reprocess.pop(0)

            if queue_item[0] == PacketHoldType.INITIAL:
                self.process_initial(queue_item[1], queue_item[2])
            elif queue_item[0] == PacketHoldType.FORWARD:
                if self.mobile_type == UVARMobileType.UAV:
                    self.process_forward_uav(queue_item[1])
                elif self.mobile_type == UVARMobileType.CAR:
                    self.process_forward_car(queue_item[1])

    def transfer_data_file(self, destination_node: str, raw_data: bytes):
        self.process_initial(destination_node, raw_data)

    def on_message_from_bottom(self, eventobj: Event):
        applmessage = eventobj.eventcontent
        hdr = applmessage.header
        
        print(f"[{self.componentinstancenumber}] Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
        
        if hdr.messagetype == UVARMessageTypes.DATA:
            packet_deserialized = UVARGPacket.deserialize(applmessage.payload.messagepayload)

            dest = packet_deserialized.destination_id
            src = packet_deserialized.source_id

            if self.componentinstancenumber == packet_deserialized.destination_id:
                print(f"[{self.componentinstancenumber}] RECVD DATA")
                metric_logger.delivered(data_packet_identifier_string(src, dest))
                return

            if self.mobile_type == UVARMobileType.UAV:
                self.process_forward_uav(packet_deserialized)
            elif self.mobile_type == UVARMobileType.CAR:
                self.process_forward_car(packet_deserialized)
            else:
                print(f"[{self.componentinstancenumber}] !!! UNDEFINED MOBILE TYPE: {self.mobile_type}")

class UVARGAdHocNode(TickerComponentModel):
    def __init__(self, componentname, componentid):
        self.appllayer = ApplicationLayerComponent("ApplicationLayer", componentid)
        self.netlayer = OneHopNetworkLayer("NetworkLayer", componentid)
        self.linklayer = LinkLayer("LinkLayer", componentid)

        self.appllayer.uvar_data_packets_on_hold = list()

        self.appllayer.connect_me_to_component(ConnectorTypes.DOWN, self.netlayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.UP, self.appllayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
        self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.netlayer)

        self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
        self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

        super().__init__(componentname, componentid)
        
    def on_message_from_top(self, eventobj: Event):
        self.logger.info(f"{EventTypes.MFRT}    {self.componentname}.{self.componentinstancenumber}")
        Topology().nodes[eventobj.eventcontent.header.nexthop].linklayer.on_message_from_bottom(eventobj)

    def assign_simclass_ptr_to_appllayer(self, car_or_uav):
        self.appllayer.mobile_ptr = car_or_uav

    def initiate_transfer(self, raw_data: bytes, destination_id: str):
        self.appllayer.transfer_data_file(destination_id, raw_data)

    def reprocess_simulation_tick(self):
        self.appllayer.simulation_tick()

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
    topo.construct_from_graph(G, UVARGAdHocNode, P2PFIFOPerfectChannel)

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

                #print("*** rp ticks")
                for node_tag, adhoc_node in topo.nodes.items():
                    adhoc_node.reprocess_simulation_tick()
                
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
    topo.construct_from_graph(G, UVARGAdHocNode, P2PFIFOPerfectChannel)

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

                #print("*** rp ticks")
                for node_tag, adhoc_node in topo.nodes.items():
                    adhoc_node.reprocess_simulation_tick()
                
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