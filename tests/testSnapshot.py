import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentRegistry
from Ahc import ConnectorTypes
from Channels import P2PFIFOPerfectChannel
from LinkLayers.GenericLinkLayer import LinkLayer
from Snapshots.Snapshots import *

registry = ComponentRegistry()

class AdHocNode(ComponentModel):
  def on_message_from_top(self, eventobj: Event):
    self.send_down(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def on_message_from_bottom(self, eventobj: Event):
    self.send_up(Event(self, EventTypes.MFRB, eventobj.eventcontent, eventobj.fromchannel))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.chandylamportsnapshot = ChandyLamportSnapshot("ChandyLamportSnapshot", componentid)
    self.linklayer = LinkLayer("LinkLayer", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.chandylamportsnapshot.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
    self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.chandylamportsnapshot)

    # Connect the bottom component to the composite component....
    self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
    self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

    super().__init__(componentname, componentid)

#    self.eventhandlers[EventTypes.MFRT] = self.onMessageFromTop
#    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel

def main():
  # G = nx.Graph()
  # G.add_nodes_from([1, 2])
  # G.add_edges_from([(1, 2)])
  # nx.draw(G, with_labels=True, font_weight='bold')
  # plt.draw()
  # G = nx.random_geometric_graph(5, 0.95)

  G = nx.gnp_random_graph(10, 0.5, directed=True)
  topo = Topology()
  topo.construct_from_graph(G, AdHocNode, P2PFIFOPerfectChannel)
  #  for ch in topo.channels:
  #    topo.channels[ch].setPacketLossProbability(random.random())
  #    topo.channels[ch].setAverageNumberOfDuplicates(0)

  # ComponentRegistry().printComponents()

  topo.start()
  topo.plot()

  print(topo.nodecolors)

  #  topo.nodes[0].chandylamportsnapshot.sendself(Event(topo.nodes[0].chandylamportsnapshot, SnapshotsEventTypes.TAKESNAPSHOT, None))
  plt.show()  # while (True): pass

if __name__ == "__main__":
  main()
