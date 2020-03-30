import time
from enum import Enum

from Ahc import Event
from Ahc import ComponentModel
from Ahc import GenericMessagePayload, GenericMessageHeader, GenericMessage
from Ahc import MessageDestinationIdentifiers

#################FAILURE ASSUMPTIONS
# TODO: Correctness properties: Safety and liveness
# TODO: Model fail stop, fail silent, omission, fail-recover and byzantine failure models to the components
# TODO: Add storage (temporary, persistent) to crash-recover model

# define your own message types
class FailureDetectorMessageTypes(Enum):
  IAMALIVE = "IAMALIVE"

# define your own message header structure
class FailureDetectorMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class FailureDetectorMessagePayload(GenericMessagePayload):
  pass

# define your own component model extending the generic component model
# do not forget to define onInit event handler...MUST!

class FailureDetector(ComponentModel):
  def onTxAliveMessage(self, eventobj: Event):
    time.sleep(self.alivemessageperiod)  # Period of alive messages
    # Send down the I'm Alive mesage
    # print("I am alive....")
    hdr = FailureDetectorMessageHeader(FailureDetectorMessageTypes.IAMALIVE, self.componentinstancenumber,
                                       MessageDestinationIdentifiers.LINKLAYERBROADCAST)
    payload = FailureDetectorMessagePayload(f"I am Node.{self.componentinstancenumber} and I am live ")
    failuredetectormessage = GenericMessage(hdr, payload)
    self.senddown(Event(self, "messagefromtop", failuredetectormessage))
    # Schedule the next I'm Alive message
    self.sendself(Event(self, "txalivemessage", "timer for alive message"))

  def onMessageFromBottom(self, eventobj: Event):
    try:
      failuredetectormessage = eventobj.eventcontent
      hdr = failuredetectormessage.header
      payload = failuredetectormessage.payload
      if hdr.messagetype == FailureDetectorMessageTypes.IAMALIVE:
        print(f"Node-{self.componentinstancenumber} says Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
      else:
        print(f"Node-{self.componentinstancenumber} says received {hdr.messagetype}")

    except AttributeError:
      print("Attribute Error")

  def onInit(self, eventobj: Event):
    self.alivemessageperiod = 1
    self.sendself(Event(self, "txalivemessage", "timer for alive message"))

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefrombottom"] = self.onMessageFromBottom
    self.eventhandlers["txalivemessage"] = self.onTxAliveMessage
