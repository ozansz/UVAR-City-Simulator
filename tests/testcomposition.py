import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentModel, Event, ConnectorTypes, Topology, EventTypes
from Ahc import ComponentRegistry
from Channels import P2PFIFOPerfectChannel

registry = ComponentRegistry()

class A(ComponentModel):
  def onInit(self, eventobj: Event):
    evt = Event(self, EventTypes.MFRT, "A to lower layer")
    self.senddown(evt)

  def onMessageFromBottom(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")

class B(ComponentModel):
  def onInit(self, eventobj: Event):
    evt = Event(self, EventTypes.MFRP, "B to peers")
    self.sendpeer(evt)

  def onMessageFromTop(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")

  def onMessageFromBottom(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")
    evt = Event(self, EventTypes.MFRB, "B to higher layer")
    self.sendup(evt)

  def onMessageFromPeer(self, eventobj: Event):
    print(f"I am {self.componentname}, got message from peer, eventcontent={eventobj.eventcontent}\n")

class N(ComponentModel):
  def onMessageFromTop(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")
    evt = Event(self, EventTypes.MFRT, "N to lower layer")
    self.senddown(evt)

  def onMessageFromBottom(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")

  def onMessageFromPeer(self, eventobj: Event):
    print(f"I am {self.componentname}, got message from peer, eventcontent={eventobj.eventcontent}\n")

class L(ComponentModel):
  def onMessageFromTop(self, eventobj: Event):
    print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}")
    evt = Event(self, EventTypes.MFRB, "L to higher layer")
    self.sendup(evt)

class Node(ComponentModel):
  def onInit(self, eventobj: Event):
    pass

  def onMessageFromTop(self, eventobj: Event):
    self.senddown(Event(self, EventTypes.MFRT, eventobj.eventcontent))

  def onMessageFromBottom(self, eventobj: Event):
    self.sendup(Event(self, EventTypes.MFRB, eventobj.eventcontent))

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.A = A("A", componentid)
    self.N = N("N", componentid)
    self.B = B("B", componentid)
    self.L = L("L", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.A.connectMeToComponent(ConnectorTypes.DOWN, self.B)
    self.A.connectMeToComponent(ConnectorTypes.DOWN, self.N)

    self.N.connectMeToComponent(ConnectorTypes.UP, self.A)
    self.B.connectMeToComponent(ConnectorTypes.UP, self.A)

    self.N.connectMeToComponent(ConnectorTypes.PEER, self.B)
    self.B.connectMeToComponent(ConnectorTypes.PEER, self.N)

    self.B.connectMeToComponent(ConnectorTypes.DOWN, self.L)
    self.N.connectMeToComponent(ConnectorTypes.DOWN, self.L)

    self.L.connectMeToComponent(ConnectorTypes.UP, self.B)
    self.L.connectMeToComponent(ConnectorTypes.UP, self.N)

    # Connect the bottom component to the composite component....
    self.L.connectMeToComponent(ConnectorTypes.DOWN, self)
    self.connectMeToComponent(ConnectorTypes.UP, self.L)

    super().__init__(componentname, componentid)

def Main():
  topo = Topology();
  topo.constructSingleNode(Node, 0)
  topo.start()

  while (True): pass

if __name__ == "__main__":
  Main()
