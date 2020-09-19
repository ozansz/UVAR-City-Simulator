import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentModel, Event, ConnectorTypes, Topology, ComponentRegistry, EventTypes
from Channels import P2PFIFOPerfectChannel
from FailureDetectors.FailureDetectors import FailureDetector

registry = ComponentRegistry()

class LinkLayerComponent(ComponentModel):

  def on_init(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def on_message_from_top(self, eventobj: Event):
    self.send_down(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def on_message_from_bottom(self, eventobj: Event):
    self.send_up(Event(self, EventTypes.MFRB, eventobj.eventcontent))

  def on_timer_expired(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["timerexpired"] = self.on_timer_expired

class AdHocNode(ComponentModel):

  def on_init(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def on_message_from_top(self, eventobj: Event):
    self.send_down(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def on_message_from_bottom(self, eventobj: Event):
    self.send_up(Event(self, EventTypes.MFRB, eventobj.eventcontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.linklayer = LinkLayerComponent("LinkLayer", componentid)
    self.failuredetect = FailureDetector("FailureDetector", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.failuredetect.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
    self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.failuredetect)

    # Connect the bottom component to the composite component....
    self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
    self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

    # First initialize the super, then add your own event handlers...
    super().__init__(componentname, componentid)

class MessageContent:
  def __init__(self, value, mynodeid):
    self.value = value
    self.mynodeid = mynodeid

def main():
  # G = nx.Graph()
  # G.add_nodes_from([1, 2, 3, 4])
  # G.add_edges_from([(1, 2), (2, 3), (3,4)])

  # https://networkx.github.io/documentation/stable/index.html
  G = nx.random_geometric_graph(9, 0.5)
  nx.draw(G, with_labels=True, font_weight='bold')
  plt.draw()

  topo = Topology()
  topo.construct_from_graph(G, AdHocNode, P2PFIFOPerfectChannel)
  topo.compute_forwarding_table()
  topo.print_forwarding_table()

  print(topo.get_next_hop(0, 1))

  print(topo.get_neighbors(0))

  # topo.start()

  #  nodes = []
  #  ch1 = FIFOBroadcastChannel("FIFOBroadcastChannel", 1)
  #  for i in range(3):
  #    cc = AdHocNode("Node", i)
  #    nodes.append(cc)
  #    cc.connectMeToChannel(ConnectorTypes.DOWN, ch1)

  #  registry.printComponents()

  plt.show()
  # while (True): pass   #plt.show() handles this

if __name__ == "__main__":
  main()
