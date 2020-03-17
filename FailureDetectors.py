from Ahc import GenericComponentModel
from Ahc import Event
from Ahc import GenericMessage
from Ahc import MessageDestinationIdentifiers
import time
from enum import Enum


#################FAILURE ASSUMPTIONS
# TODO: Correctness properties: Safety and liveness
# TODO: Model fail stop, fail silent, omission, fail-recover and byzantine failure models to the components
# TODO: Add storage (temporary, persistent) to crash-recover model
# TODO: Channel failure models: lossy-link, fair-loss, stubborn links, perfect links (WHAT ELSE?), FIFO perfect
# TODO: Logged perfect links (tolerance to crashes), authenticated perfect links
# TODO: Broadcast channels? and their failure models? Collisions?
# TODO: Properties of all models separately: e.g., Fair loss, finite duplication, no fabrication in fair-loss link model
# TODO: Packets: loss, duplication, sequence change, windowing?,
# TODO: Eventually (unbounded time) or bounded time for message delivery?


class FailureDetectorMessageTypes(Enum):
  IAMALIVE = "IAMALIVE"

class FailureDetectorMessage(GenericMessage):
  pass

class GenericFailureDetector(GenericComponentModel):
  def onInit(self, eventobj: Event):
    self.alivemessageperiod = 1
    self.sendself(Event(self, "txalivemessage", "timer for alive message"))
    super().onInit(eventobj)   #Does not do much, just prints what it does, may be required...

  def onTxAliveMessage(self, eventobj: Event):
    time.sleep(self.alivemessageperiod)   #Period of alive messages
    # Send down the I'm Alive mesage
    # print("I am alive....")
    failuredetectormessage = FailureDetectorMessage(FailureDetectorMessageTypes.IAMALIVE, self.componentinstancenumber, MessageDestinationIdentifiers.LINKLAYERBROADCAST,
                                     f"I am Node.{self.componentinstancenumber} and I am live ")
    self.senddown(Event(self, "messagefromtop", failuredetectormessage))
    # Schedule the next I'm Alive message
    self.sendself(Event(self, "txalivemessage", "timer for alive message"))

  def onMessageFromBottom(self, eventobj: Event):
    failuredetectormessage = eventobj.messagecontent
    #print(f"Node-{self.componentinstancenumber} says Node-{failuredetectormessage.messagefrom} has sent to Node-{failuredetectormessage.messageto} {failuredetectormessage.messagetype} message")
    pass

  eventhandlers = {
    "init": onInit,
    "messagefrombottom": onMessageFromBottom,
    "txalivemessage": onTxAliveMessage
  }
