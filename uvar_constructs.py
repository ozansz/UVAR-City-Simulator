import pickle
from enum import Enum

class UVARGPacket(object):
    def __init__(self, destination_id: int, source_id: int, next_intersection: int, raw_data: bytes, uav_send_me_to_car_in_section: tuple):
        self.raw_data = raw_data
        self.source_id = source_id
        self.destination_id = destination_id
        self.next_intersection = next_intersection
        self.uav_send_me_to_car_in_section = uav_send_me_to_car_in_section
    
    def serialize(self) -> bytes:
        return pickle.dumps(self)#, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def deserialize(data: bytes):
        return pickle.loads(data)#, protocol=pickle.HIGHEST_PROTOCOL)

class UVARMessageTypes(Enum):
    DATA = "DATA"
    RREQ = "RREQ"
    RREP = "RREP"

class UVARMobileType:
    CAR = "CAR"
    UAV = "UAV"