import random
import time
from enum import Enum

import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentRegistry
from Ahc import GenericComponentModel, Event, PortNames, Topology, MessageDestinationIdentifiers
from Ahc import GenericMessagePayload, GenericMessageHeader, GenericMessage
from Channels import  FIFOBroadcastPerfectChannel
from AllSeeingEyeNetworkLayer import AllSeingEyeNetworkLayer
from GenericLinkLayer import GenericLinkLayer

registry = ComponentRegistry()

# define your own message types
class ApplicationLayerMessageTypes(Enum):
  PROPOSE = "PROPOSE"
  ACCEPT = "ACCEPT"

# define your own message header structure
class ApplicationLayerMessageHeader(GenericMessageHeader):
  pass


# define your own message payload structure
class ApplicationLayerMessagePayload(GenericMessagePayload):
  pass

class ApplicationLayerComponent(GenericComponentModel):
  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    proposedval = random.randint(0, 100)

    if self.componentinstancenumber == 0:
      #destination = random.randint(len(Topology.G.nodes))
      destination = 1
      hdr = ApplicationLayerMessageHeader(ApplicationLayerMessageTypes.PROPOSE, self.componentinstancenumber, destination)
      payload = ApplicationLayerMessagePayload("23")
      proposalmessage = GenericMessage(hdr, payload)
      randdelay = random.randint(0, 5)
      time.sleep(randdelay)
      self.sendself(Event(self, "propose", proposalmessage))
    else:
      pass

  def onMessageFromBottom(self, eventobj: Event):
    try:
      applmessage = eventobj.messagecontent
      hdr = applmessage.header
      payload = applmessage.payload
      if hdr.messagetype == ApplicationLayerMessageTypes.ACCEPT:
        print(f"Node-{self.componentinstancenumber} says Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
      elif hdr.messagetype == ApplicationLayerMessageTypes.PROPOSE:
        print(f"Node-{self.componentinstancenumber} says Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
    except AttributeError:
      print("Attribute Error")

  # print(f"{self.componentname}.{self.componentinstancenumber}: Gotton message {eventobj.content} ")
  # value = eventobj.content.value
  # value += 1
  # newmsg = MessageContent( value )
  # myevent = Event( self, "agree", newmsg )
  # self.trigger_event(myevent)

  def onPropose(self, eventobj: Event):
    destination = 1
    hdr = ApplicationLayerMessageHeader(ApplicationLayerMessageTypes.ACCEPT, self.componentinstancenumber, destination)
    payload = ApplicationLayerMessagePayload("23")
    proposalmessage = GenericMessage(hdr, payload)
    self.senddown(Event(self, "messagefromtop", proposalmessage))

  def onAgree(self, eventobj: Event):
    print(f"Agreed on {eventobj.messagecontent}")

  def onTimerExpired(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["propose"] = self.onPropose
    self.eventhandlers["messagefrombottom"] = self.onMessageFromBottom
    self.eventhandlers["agree"] = self.onAgree
    self.eventhandlers["timerexpired"] = self.onAgree

class AdHocNode(GenericComponentModel):

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, "sendtochannel", eventobj.messagecontent))

  def onMessageFromChannel(self, eventobj: Event):
    self.sendup(Event(self, "messagefrombottom", eventobj.messagecontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.appllayer = ApplicationLayerComponent("ApplicationLayer", componentid)
    self.netlayer = AllSeingEyeNetworkLayer("NetworkLayer", componentid)
    self.linklayer = GenericLinkLayer("LinkLayer", componentid)
    #self.failuredetect = GenericFailureDetector("FailureDetector", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.appllayer.connectMeToComponent(PortNames.DOWN, self.netlayer)
    #self.failuredetect.connectMeToComponent(PortNames.DOWN, self.netlayer)
    self.netlayer.connectMeToComponent(PortNames.UP, self.appllayer)
    #self.netlayer.connectMeToComponent(PortNames.UP, self.failuredetect)
    self.netlayer.connectMeToComponent(PortNames.DOWN, self.linklayer)
    self.linklayer.connectMeToComponent(PortNames.UP, self.netlayer)

    # Connect the bottom component to the composite component....
    self.linklayer.connectMeToComponent(PortNames.DOWN, self)
    self.connectMeToComponent(PortNames.UP, self.linklayer)

    super().__init__(componentname, componentid)
    self.eventhandlers["messagefromtop"] = self.onMessageFromTop
    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel

def Main():
  #G = nx.Graph()
  #G.add_nodes_from([1, 2])
  #G.add_edges_from([(1, 2)])
  #nx.draw(G, with_labels=True, font_weight='bold')
  #plt.draw()
  G = nx.random_geometric_graph(19, 0.5)
  nx.draw(G, with_labels=True, font_weight='bold')
  plt.draw()

  topo = Topology()
  topo.constructFromGraph(G, AdHocNode, FIFOBroadcastPerfectChannel)
  topo.start()

  plt.show()  # while (True): pass

if __name__ == "__main__":
  Main()
