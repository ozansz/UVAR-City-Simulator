

from Ahc import ComponentModel, MessageDestinationIdentifiers, Event, GenericMessageHeader, GenericMessagePayload, GenericMessage, EventTypes
from enum import Enum

# define your own message types
class LinkLayerMessageTypes(Enum):
  LINKMSG = "LINKMSG"

# define your own message header structure
class LinkLayerMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class LinkLayerMessagePayload(GenericMessagePayload):
  pass


class LinkLayer(ComponentModel):
  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    abovehdr = eventobj.eventcontent.header
    if abovehdr == MessageDestinationIdentifiers.NETWORKLAYERBROADCAST:
      hdr = LinkLayerMessageHeader(LinkLayerMessageTypes.LINKMSG, self.componentinstancenumber,
                                   MessageDestinationIdentifiers.LINKLAYERBROADCAST)
    else:
      hdr = LinkLayerMessageHeader(LinkLayerMessageTypes.LINKMSG, self.componentinstancenumber,
                                   abovehdr.nexthop)

    payload = eventobj.eventcontent
    msg = GenericMessage(hdr, payload)
    self.senddown(Event(self, EventTypes.MFRT, msg))

  def onMessageFromBottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    payload = msg.payload
    if hdr.messageto == self.componentinstancenumber or hdr.messageto == MessageDestinationIdentifiers.LINKLAYERBROADCAST :
      self.sendup(Event(self, EventTypes.MFRB, payload)) #doing decapsulation by just sending the payload
    else:
      print(f"I am {self.componentinstancenumber} and dropping the {hdr.messagetype} message to {hdr.messageto}")

#  def __init__(self, componentname, componentinstancenumber):
#   super().__init__(componentname, componentinstancenumber)
#   If you have to extend the model add events here