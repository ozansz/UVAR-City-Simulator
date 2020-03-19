from Ahc import GenericComponentModel, Event, PortNames, Topology, ComponentRegistry
from FailureDetectors import GenericFailureDetector
from Channels import P2PFIFOPerfectChannel
import networkx as nx
import matplotlib.pyplot as plt

registry = ComponentRegistry()

class LinkLayerComponent(GenericComponentModel):

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, "messagefromtop", eventobj.messagecontent))

  def onMessageFromBottom(self, eventobj: Event):
    self.sendup(Event(self, "messagefrombottom", eventobj.messagecontent))

  def onTimerExpired(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefromtop"] = self.onMessageFromTop
    self.eventhandlers["messagefrombottom"] = self.onMessageFromBottom
    self.eventhandlers["timerexpired"] = self.onTimerExpired


class AdHocNode(GenericComponentModel):

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, "sendtochannel", eventobj.messagecontent))

  def onMessageFromChannel(self, eventobj: Event):
    self.sendup(Event(self, "messagefrombottom", eventobj.messagecontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.linklayer = LinkLayerComponent("LinkLayer", componentid)
    self.failuredetect = GenericFailureDetector("FailureDetector", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.failuredetect.connectMeToComponent(PortNames.DOWN, self.linklayer)
    self.linklayer.connectMeToComponent(PortNames.UP, self.failuredetect)

    # Connect the bottom component to the composite component....
    self.linklayer.connectMeToComponent(PortNames.DOWN, self)
    self.connectMeToComponent(PortNames.UP, self.linklayer)


    #First initialize the super, then add your own event handlers...
    super().__init__(componentname, componentid)
    self.eventhandlers["messagefromtop"] = self.onMessageFromTop
    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel


class MessageContent:
  def __init__(self, value, mynodeid):
    self.value = value
    self.mynodeid = mynodeid

def Main():
  # G = nx.Graph()
  # G.add_nodes_from([1, 2, 3, 4])
  # G.add_edges_from([(1, 2), (2, 3), (3,4)])

  # https://networkx.github.io/documentation/stable/index.html
  G = nx.random_geometric_graph(5, 0.5)
  nx.draw(G, with_labels=True, font_weight='bold')
  plt.draw()

  topo = Topology()
  topo.constructFromGraph(G, AdHocNode, P2PFIFOPerfectChannel)
  topo.start()
  #  nodes = []
  #  ch1 = FIFOBroadcastChannel("FIFOBroadcastChannel", 1)
  #  for i in range(3):
  #    cc = AdHocNode("Node", i)
  #    nodes.append(cc)
  #    cc.connectMeToChannel(PortNames.DOWN, ch1)

  #  registry.printComponents()

  plt.show()
  # while (True): pass   #plt.show() handles this

if __name__ == "__main__":
  Main()
