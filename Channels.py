from Ahc import GenericComponentModel
from Ahc import Event
import time
import random

# TODO: Channel failure models: lossy-link, fair-loss, stubborn links, perfect links (WHAT ELSE?), FIFO perfect
# TODO: Logged perfect links (tolerance to crashes), authenticated perfect links
# TODO: Broadcast channels? and their failure models? Collisions?
# TODO: Properties of all models separately: e.g., Fair loss, finite duplication, no fabrication in fair-loss link model
# TODO: Packets: loss, duplication, sequence change, windowing?,
# TODO: Eventually (unbounded time) or bounded time for message delivery?


class GenericChannel(GenericComponentModel):
  pass

class AHCChannelError(Exception):
  pass

class P2PFIFOPerfectChannel(GenericChannel):
  def onInit(self, eventobj: Event):
    #print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    pass

  # Overwriting to limit the number of connected components
  def connectMeToComponent(self, name, component):
    try:
      self.ports[name] = component
      #print(f"Number of nodes connected: {len(self.ports)}")
      if len(self.ports) > 2:
        raise AHCChannelError("More than two nodes cannot connect to a P2PFIFOChannel")
    except AttributeError:
      self.ports = PortList()
      self.ports[name] = component
    # except AHCChannelError as e:
    #    print( f"{e}" )

  def onMessage(self, eventobj: Event):
    callername = eventobj.caller.componentname + str(eventobj.caller.componentinstancenumber)
    for item in self.ports:
      callees = self.ports[item]

      for callee in callees:
        calleename = callee.componentname + str(callee.componentinstancenumber)
        # print(f"I am connected to {calleename}. Will check if I have to distribute it to {item}")
        if calleename == callername:
          pass
        else:
          myevent = Event(self, "messagefromchannel", eventobj.messagecontent)
          callee.trigger_event(myevent)

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["message"] = self.onMessage



class P2PFIFOFairLossChannel(P2PFIFOPerfectChannel):
  prob = 1

  def onMessage(self, eventobj: Event):
    callername = eventobj.caller.componentname + str(eventobj.caller.componentinstancenumber)
    for item in self.ports:
      callees = self.ports[item]

      for callee in callees:
        calleename = callee.componentname + str(callee.componentinstancenumber)
        if calleename == callername:
          pass
        else:
          myevent = Event(self, "messagefromchannel", eventobj.messagecontent)
          if random.random() < self.prob:
            callee.trigger_event(myevent)
            if random.random() < self.duplicationprobability:
              callee.trigger_event(myevent)

  def setPacketLossProbability(self, prob):
    self.prob = prob

  def setAverageNumberOfDuplicates(self, d):
    self.duplicationprobability = (d-1)/d


class FIFOBroadcastPerfectChannel(GenericChannel):

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessage(self, eventobj: Event):
    callername = eventobj.caller.componentname + str(eventobj.caller.componentinstancenumber)
    for item in self.ports:
      callees = self.ports[item]
      for callee in callees:
        calleename = callee.componentname + str(callee.componentinstancenumber)
        # print(f"I am connected to {calleename}. Will check if I have to distribute it to {item}")
        if calleename == callername:
          pass
        else:
          myevent = Event(self, "messagefromchannel", eventobj.messagecontent)
          callee.trigger_event(myevent)


  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers["message"] = self.onMessage


