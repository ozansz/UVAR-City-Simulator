from Ahc import GenericComponentModel, Event, PortNames, Topology, ComponentRegistry
from FailureDetectors import GenericFailureDetector
from Channels import P2PFIFOPerfectChannel
import networkx as nx
import matplotlib.pyplot as plt
import time

registry = ComponentRegistry()

class GenericSender(GenericComponentModel):

  def onInit(self, eventobj: Event):
    self.sendcnt = 0
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    self.sendself(Event(self, "generatemessage", "..."))

  def onGenerateMessage(self, eventobj: Event):
    self.senddown(Event(self, "message", eventobj))
    self.sendcnt = self.sendcnt + 1
    time.sleep(1)
    self.sendself(Event(self, "generatemessage", "..."))

  def onMessageFromChannel(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel
    self.eventhandlers["generatemessage"] = self.onGenerateMessage



class GenericReceiver(GenericComponentModel):
  def onInit(self, eventobj: Event):
    self.recvcnt = 0

  def onMessageFromChannel(self, eventobj: Event):
    self.recvcnt = self.recvcnt + 1
    print(f"{self.componentname}.{self.componentinstancenumber} received message {self.recvcnt}")

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel



def Main():
  topo = Topology(GenericSender, GenericReceiver, P2PFIFOPerfectChannel)
  nx.draw(topo.G, with_labels=True, font_weight='bold')
  plt.draw()

  plt.show()
  # while (True): pass   #plt.show() handles this

if __name__ == "__main__":
  Main()
