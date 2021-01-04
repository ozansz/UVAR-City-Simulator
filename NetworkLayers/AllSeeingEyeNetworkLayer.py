import os
from enum import Enum

DO_DEBUG = "AHC_DEBUG" in os.environ

from Ahc import ComponentModel, TickerComponentModel, Event, GenericMessageHeader, GenericMessagePayload, GenericMessage, Topology, \
  MessageDestinationIdentifiers, EventTypes

# define your own message types
class NetworkLayerMessageTypes(Enum):
  NETMSG = "NETMSG"

# define your own message header structure
class NetworkLayerMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class NetworkLayerMessagePayload(GenericMessagePayload):
  pass

class AllSeingEyeNetworkLayer(ComponentModel):

  def on_message_from_top(self, eventobj: Event):
    # Encapsulate the SDU in network layer PDU
    applmsg = eventobj.eventcontent
    destination = applmsg.header.messageto
    nexthop = Topology().get_next_hop(self.componentinstancenumber, destination)

    print(f"[###] destination: {destination}, nexthop: {nexthop}")

    if nexthop is None:
      nexthop = destination

    if nexthop != float('inf'):
      print(f"NL {self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
      hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination,
                                      nexthop)
      payload = eventobj.eventcontent
      msg = GenericMessage(hdr, payload)
      self.send_down(Event(self, EventTypes.MFRT, msg))
    else:
      print(f"NL NO PATH: {self.componentinstancenumber} will NOTSEND a message to {destination} over {nexthop}")

  def on_message_from_bottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    payload = msg.payload

    if hdr.messageto == self.componentinstancenumber or hdr.messageto == MessageDestinationIdentifiers.NETWORKLAYERBROADCAST:  # Add if broadcast....
      self.send_up(Event(self, EventTypes.MFRB, payload))
      print(f"NL I received a message to {hdr.messageto} and I am {self.componentinstancenumber}")
    else:
      destination = hdr.messageto
      nexthop = Topology().get_next_hop(self.componentinstancenumber, destination)

      if nexthop is None:
        nexthop = destination

      if nexthop != float('inf'):
        newhdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination,
                                           nexthop)
        newpayload = eventobj.eventcontent.payload
        msg = GenericMessage(newhdr, newpayload)
        self.send_down(Event(self, EventTypes.MFRT, msg))
        print(f"NL {self.componentinstancenumber} will FORWARD a message to {destination} over {nexthop}")
      else:
        print(f"NL NO PATH {self.componentinstancenumber} will NOT FORWARD a message to {destination} over {nexthop}")

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)

class OneHopNetworkLayer(ComponentModel):

  def on_message_from_top(self, eventobj: Event):
    # Encapsulate the SDU in network layer PDU
    applmsg = eventobj.eventcontent
    destination = applmsg.header.messageto
    nexthop = Topology().get_next_hop(self.componentinstancenumber, destination)

    #print(f"[###] destination: {destination}, nexthop: {nexthop}")

    if nexthop != float('inf'):
      print(f"NL {self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
      hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination,
                                      nexthop)
      payload = eventobj.eventcontent
      msg = GenericMessage(hdr, payload)
      self.send_down(Event(self, EventTypes.MFRT, msg))
    else:
      print(f"NL NO PATH: {self.componentinstancenumber} will NOTSEND a message to {destination} over {nexthop}")

  def on_message_from_bottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    payload = msg.payload

    if hdr.messageto == self.componentinstancenumber or hdr.messageto == MessageDestinationIdentifiers.NETWORKLAYERBROADCAST:  # Add if broadcast....
      self.send_up(Event(self, EventTypes.MFRB, payload))
      print(f"NL I received a message to {hdr.messageto} and I am {self.componentinstancenumber}")
    else:
      destination = hdr.messageto
      nexthop = Topology().get_next_hop(self.componentinstancenumber, destination)
      if nexthop != float('inf'):
        newhdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination,
                                           nexthop)
        newpayload = eventobj.eventcontent.payload
        msg = GenericMessage(newhdr, newpayload)
        self.send_down(Event(self, EventTypes.MFRT, msg))
        print(f"NL {self.componentinstancenumber} will FORWARD a message to {destination} over {nexthop}")
      else:
        print(f"NL NO PATH {self.componentinstancenumber} will NOT FORWARD a message to {destination} over {nexthop}")

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)