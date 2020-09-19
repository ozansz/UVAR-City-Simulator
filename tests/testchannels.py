import matplotlib.pyplot as plt
import networkx as nx

from Ahc import ComponentModel, Event, Topology, ComponentRegistry, GenericMessage, GenericMessageHeader, EventTypes
from Channels import P2PFIFOFairLossChannel

registry = ComponentRegistry()

class Sender(ComponentModel):
  def on_init(self, eventobj: Event):
    self.sendcnt = 0
    # print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    self.send_self(Event(self, "generatemessage", "..."))

  def on_generate_message(self, eventobj: Event):
    self.sendcnt = self.sendcnt + 1
    msg = GenericMessage(GenericMessageHeader("AL", 0, 1), self.sendcnt)
    self.send_down(Event(self, EventTypes.MFRT, msg))
    # time.sleep(1)
    self.send_self(Event(self, "generatemessage", "..."))

  def on_message_from_bottom(self, eventobj: Event):
    pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["generatemessage"] = self.on_generate_message

class Receiver(ComponentModel):
  def on_init(self, eventobj: Event):
    self.recvcnt = 0
    print("Received Percentage:\n")

  def on_message_from_bottom(self, eventobj: Event):
    self.recvcnt = self.recvcnt + 1
    self.sentcnt = eventobj.eventcontent.payload
    print(f"{self.recvcnt / self.sentcnt}")
    # print(nx.adjacency_matrix(Topology().G).todense())
    # print("Progress {:2.2}".format(self.recvcnt/self.sentcnt), end="\r")
    Topology().shortest_path_to_all(self.componentinstancenumber)

def main():
  topo = Topology()

  topo.construct_sender_receiver(Sender, Receiver, P2PFIFOFairLossChannel)
  nx.draw(topo.G, with_labels=True, font_weight='bold')
  plt.draw()
  topo.channels["0-1"].setPacketLossProbability(0.1)
  topo.channels["0-1"].setAverageNumberOfDuplicates(0)

  # topo.computeForwardingTable()

  topo.start()
  plt.show()
  # while (True): pass   #plt.show() handles this

if __name__ == "__main__":
  main()
