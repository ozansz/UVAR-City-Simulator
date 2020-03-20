
from Ahc import GenericComponentModel, Event, GenericMessageHeader, GenericMessagePayload, GenericMessage, Topology
from enum import Enum

# define your own message types
class NetworkLayerMessageTypes(Enum):
  NETMSG = "NETMSG"

# define your own message header structure
class NetworkLayerMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class NetworkLayerMessagePayload(GenericMessagePayload):
  pass


class NetworkLayerComponent(GenericComponentModel):
  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    # Encapsulate the SDU in network layer PDU
    applmsg = eventobj.messagecontent
    destination = applmsg.header.messageto
    nexthop = Topology().getNextHop(self.componentinstancenumber, destination)
    if nexthop != float('inf'):
      print(f"{self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
      hdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination, nexthop )
      payload = eventobj.messagecontent
      msg = GenericMessage(hdr, payload)
      self.senddown(Event(self, "messagefromtop", msg))
    else:
      print(f"NO PATH: {self.componentinstancenumber} will NOTSEND a message to {destination} over {nexthop}")


  def onMessageFromBottom(self, eventobj: Event):
    msg = eventobj.messagecontent
    hdr = msg.header
    payload = msg.payload
    if hdr.messageto == self.componentinstancenumber:  # Add if broadcast....
      self.sendup(Event(self, "messagefrombottom", payload))
    else:
      destination = hdr.messageto
      nexthop = Topology().getNextHop(self.componentinstancenumber, destination)
      if nexthop != float('inf') :
        newhdr = NetworkLayerMessageHeader(NetworkLayerMessageTypes.NETMSG, self.componentinstancenumber, destination, nexthop)
        newpayload = eventobj.messagecontent
        msg = GenericMessage(newhdr, newpayload)
        self.senddown(Event(self, "messagefromtop", msg))
        print(f"{self.componentinstancenumber} will FORWARD a message to {destination} over {nexthop}")
      else:
        print(f"NO PATH {self.componentinstancenumber} will NOT FORWARD a message to {destination} over {nexthop}")

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefromtop"] = self.onMessageFromTop
    self.eventhandlers["messagefrombottom"] = self.onMessageFromBottom
