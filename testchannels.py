from Ahc import GenericComponentModel, Event, Topology, ComponentRegistry, GenericMessage, GenericMessageHeader, GenericMessagePayload
from Channels import P2PFIFOPerfectChannel,P2PFIFOFairLossChannel
import networkx as nx
import matplotlib.pyplot as plt
import time

registry = ComponentRegistry()

class GenericSender(GenericComponentModel):
  def onInit(self, eventobj: Event):
    self.sendcnt = 0
    #print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    self.sendself(Event(self, "generatemessage", "..."))

  def onGenerateMessage(self, eventobj: Event):
    self.sendcnt = self.sendcnt + 1
    msg = GenericMessage(GenericMessageHeader("AL", 0, 1), self.sendcnt)
    self.senddown(Event(self, "sendtochannel", msg))
    #time.sleep(1)
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
    print("Received Percentage:\n")

  def onMessageFromChannel(self, eventobj: Event):
    self.recvcnt = self.recvcnt + 1
    self.sentcnt = eventobj.messagecontent.payload
    print(f"{self.recvcnt/self.sentcnt}")
    #print("Progress {:2.2}".format(self.recvcnt/self.sentcnt), end="\r")

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["messagefromchannel"] = self.onMessageFromChannel

def Main():
  topo = Topology()
  topo.constructSenderReceiver(GenericSender, GenericReceiver, P2PFIFOFairLossChannel)
  nx.draw(topo.G, with_labels=True, font_weight='bold')
  plt.draw()
  topo.channels["0-1"].setPacketLossProbability(0.1)
  topo.channels["0-1"].setAverageNumberOfDuplicates(0)
  topo.start()
  plt.show()
  # while (True): pass   #plt.show() handles this

if __name__ == "__main__":
  Main()
