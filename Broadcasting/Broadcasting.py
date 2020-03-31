import random
import time
from enum import Enum

from Ahc import ComponentModel, Event, GenericMessageHeader, GenericMessagePayload, GenericMessage, Topology, \
  MessageDestinationIdentifiers, EventTypes

# define your own message types
class BroadcastingMessageTypes(Enum):
  SIMPLEFLOOD = "SIMPLEFLOOD"

# define your own message header structure
class BroadcastingMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class BroadcastingMessagePayload(GenericMessagePayload):
  pass

class ControlledFlooding(ComponentModel):
  def onInit(self, eventobj: Event):
    self.broadcastdb = []
    if self.componentinstancenumber == 0:
      self.sendself(Event(self, EventTypes.MFRT, None))

  def senddownbroadcast(self, eventobj: Event, whosends, sequencenumber):
    applmsg = eventobj.eventcontent
    destination = MessageDestinationIdentifiers.NETWORKLAYERBROADCAST
    nexthop = MessageDestinationIdentifiers.LINKLAYERBROADCAST
    print(f"{self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
    hdr = BroadcastingMessageHeader(BroadcastingMessageTypes.SIMPLEFLOOD, whosends, destination,
                                    nexthop, sequencenumber)
    payload = applmsg
    broadcastmessage = GenericMessage(hdr, payload)
    self.senddown(Event(self, EventTypes.MFRT, broadcastmessage))
    self.broadcastdb.append(broadcastmessage.uniqueid)

  def updateTopology(self):
    Topology().nodecolors[self.componentinstancenumber] = 'r'
    Topology().plot()

  def onMessageFromTop(self, eventobj: Event):
    self.updateTopology()
    self.senddownbroadcast(eventobj, self.componentinstancenumber, 1)

  def onMessageFromBottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    payload = msg.payload
    if hdr.messagetype == BroadcastingMessageTypes.SIMPLEFLOOD:
      if hdr.messageto == self.componentinstancenumber or hdr.messageto == MessageDestinationIdentifiers.NETWORKLAYERBROADCAST:  # Add if broadcast....
        if (msg.uniqueid in self.broadcastdb):
          pass  # we have already handled this flooded message
        else:
          # Send to higher layers
          self.updateTopology()
          self.sendup(Event(self, EventTypes.MFRB, payload))
          # Also continue flooding once
          time.sleep(random.randint(1, 3))
          self.senddownbroadcast(eventobj, eventobj.eventcontent.header.messagefrom,
                                 eventobj.eventcontent.header.sequencenumber)

#  def __init__(self, componentname, componentinstancenumber):
#    super().__init__(componentname, componentinstancenumber)
#     #add events here
