import matplotlib.pyplot as plt
import networkx as nx
import random
from Ahc import ComponentRegistry
from Ahc import ComponentModel, Event, PortNames, Topology, MessageDestinationIdentifiers, EventTypes
from Ahc import GenericMessagePayload, GenericMessageHeader, GenericMessage
from Channels import P2PFIFOPerfectChannel, FIFOBroadcastPerfectChannel,P2PFIFOFairLossChannel
from Broadcasting.Broadcasting import ControlledFlooding
from GenericLinkLayer import LinkLayer
from FailureDetectors import FailureDetector

registry = ComponentRegistry()

class AdHocNode(ComponentModel):
  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def onMessageFromBottom(self, eventobj: Event):
    self.sendup(Event(self, EventTypes.MFRB, eventobj.eventcontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.broadcastservice = ControlledFlooding("SimpleFlooding", componentid)
    self.linklayer = LinkLayer("LinkLayer", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.broadcastservice.connectMeToComponent(PortNames.DOWN, self.linklayer)
    self.linklayer.connectMeToComponent(PortNames.UP, self.broadcastservice)

    # Connect the bottom component to the composite component....
    self.linklayer.connectMeToComponent(PortNames.DOWN, self)
    self.connectMeToComponent(PortNames.UP, self.linklayer)

    super().__init__(componentname, componentid)
#    self.eventhandlers[EventTypes.MFRT] = self.onMessageFromTop
#    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel

def Main():
  #G = nx.Graph()
  #G.add_nodes_from([1, 2])
  #G.add_edges_from([(1, 2)])
  #nx.draw(G, with_labels=True, font_weight='bold')
  #plt.draw()
  G = nx.random_geometric_graph(19, 0.5)
  topo = Topology()
  topo.constructFromGraph(G, AdHocNode, P2PFIFOFairLossChannel)
  for ch in topo.channels:
    topo.channels[ch].setPacketLossProbability(random.random())
    topo.channels[ch].setAverageNumberOfDuplicates(0)

  topo.start()
  topo.plot()
  plt.show()  # while (True): pass




  print(topo.nodecolors)

if __name__ == "__main__":
  Main()
