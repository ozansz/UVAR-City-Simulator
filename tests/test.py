import random
import time
from enum import Enum

import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentRegistry
from Ahc import ComponentModel, Event, ConnectorTypes, Topology
from Ahc import GenericMessagePayload, GenericMessageHeader, GenericMessage, EventTypes
from Channels import P2PFIFOPerfectChannel
from NetworkLayers.AllSeeingEyeNetworkLayer import AllSeingEyeNetworkLayer
from LinkLayers.GenericLinkLayer import LinkLayer

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

class ApplicationLayerComponent(ComponentModel):
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
      applmessage = eventobj.eventcontent
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
    self.senddown(Event(self, EventTypes.MFRT, proposalmessage))

  def onAgree(self, eventobj: Event):
    print(f"Agreed on {eventobj.eventcontent}")

  def onTimerExpired(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["propose"] = self.onPropose
    self.eventhandlers["agree"] = self.onAgree
    self.eventhandlers["timerexpired"] = self.onTimerExpired

class AdHocNode(ComponentModel):

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def onMessageFromBottom(self, eventobj: Event):
    self.sendup(Event(self, EventTypes.MFRB, eventobj.eventcontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.appllayer = ApplicationLayerComponent("ApplicationLayer", componentid)
    self.netlayer = AllSeingEyeNetworkLayer("NetworkLayer", componentid)
    self.linklayer = LinkLayer("LinkLayer", componentid)
    #self.failuredetect = GenericFailureDetector("FailureDetector", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.appllayer.connectMeToComponent(ConnectorTypes.DOWN, self.netlayer)
    #self.failuredetect.connectMeToComponent(PortNames.DOWN, self.netlayer)
    self.netlayer.connectMeToComponent(ConnectorTypes.UP, self.appllayer)
    #self.netlayer.connectMeToComponent(PortNames.UP, self.failuredetect)
    self.netlayer.connectMeToComponent(ConnectorTypes.DOWN, self.linklayer)
    self.linklayer.connectMeToComponent(ConnectorTypes.UP, self.netlayer)

    # Connect the bottom component to the composite component....
    self.linklayer.connectMeToComponent(ConnectorTypes.DOWN, self)
    self.connectMeToComponent(ConnectorTypes.UP, self.linklayer)

    super().__init__(componentname, componentid)

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
  topo.constructFromGraph(G, AdHocNode, P2PFIFOPerfectChannel)
  topo.start()

  plt.show()  # while (True): pass

if __name__ == "__main__":
  Main()
