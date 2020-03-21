import random
import time
from enum import Enum

import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentRegistry
from Ahc import GenericComponentModel, Event, PortNames, Topology, MessageDestinationIdentifiers
from Ahc import GenericMessagePayload, GenericMessageHeader, GenericMessage
from Channels import P2PFIFOPerfectChannel, FIFOBroadcastPerfectChannel
from Broadcasting.Broadcasting import SimpleFlooding
from GenericLinkLayer import GenericLinkLayer
from FailureDetectors import GenericFailureDetector

registry = ComponentRegistry()

class AdHocNode(GenericComponentModel):
  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, "sendtochannel", eventobj.messagecontent))

  def onMessageFromChannel(self, eventobj: Event):
    self.sendup(Event(self, "messagefrombottom", eventobj.messagecontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.broadcastservice = SimpleFlooding("SimpleFlooding", componentid)
    self.linklayer = GenericLinkLayer("LinkLayer", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.broadcastservice.connectMeToComponent(PortNames.DOWN, self.linklayer)
    self.linklayer.connectMeToComponent(PortNames.UP, self.broadcastservice)

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
  topo = Topology()
  topo.constructFromGraph(G, AdHocNode, P2PFIFOPerfectChannel)
  topo.start()
  topo.plot()
  plt.show()  # while (True): pass

  print(topo.nodecolors)

if __name__ == "__main__":
  Main()
