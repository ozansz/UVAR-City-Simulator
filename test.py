from Ahc import GenericComponentModel
from Ahc import Event
from Ahc import ComponentRegistry
import threading
from Ahc import PortNames
import time

registry = ComponentRegistry()

class ApplicationLayerComponent(GenericComponentModel):
  ports = {}

  def onMessage(self, eventobj: Event):
    myevent = Event(self, "message", "content")
    if self.upout:
      self.upout.trigger_event(myevent)
    if self.downout:
      self.downout.trigger_event(myevent)

  def onTimerExpired(self, eventobj: Event):
    pass

  handlerdict = {
    "message": onMessage,
    "timerexpired": onTimerExpired
  }

  def __init__(self, componentname, componentid):
    super().__init__(componentname, componentid, self.handlerdict, self.ports)

class NetworkLayerComponent(GenericComponentModel):
  ports = {}

  def onMessage(self, eventobj: Event):
    myevent = Event(self, "message", "content")
    if self.upout:
      self.upout.trigger_event(myevent)
    if self.downout:
      self.downout.trigger_event(myevent)

  def onTimerExpired(self, eventobj: Event):
    pass

  handlerdict = {
    "message": onMessage,
    "timerexpired": onTimerExpired
  }

#  def __init__(self, componentname, componentid):
#    super().__init__(componentname, componentid, self.handlerdict, self.ports)

class LinkLayerComponent(GenericComponentModel):
  ports = {}

  def onMessage(self, eventobj: Event):
    myevent = Event(self, "message", "content")
    if self.upout:
      self.upout.trigger_event(myevent)
    if self.downout:
      self.downout.trigger_event(myevent)

  def onTimerExpired(self, eventobj: Event):
    pass

  handlerdict = {
    "message": onMessage,
    "timerexpired": onTimerExpired
  }

  def __init__(self, componentname, componentid):
    super().__init__(componentname, componentid, self.handlerdict, self.ports)

class CompositeComponent(GenericComponentModel):

  def onMessage(self, eventobj: Event):
    myevent = Event(self, "internalmessage", "content")
    self.ports[PortNames.UP].trigger_event(myevent)

  def onInternalMessage(self, eventobj: Event):
    print(f"I am {self.componentname}: {eventobj.caller.componentname} called me at {eventobj.time}")
    myevent = Event(self, "message", "content")
    self.ports[PortNames.DOWN].trigger_event(myevent)

  handlerdict = {
    "message": onMessage,
    "internalmessage": onInternalMessage
  }

  def __init__(self, componentname, componentid):
    # SUBCOMPONENTS
    self.appllayer = ApplicationLayerComponent("ApplicationLayer", componentid)
    self.netlayer = NetworkLayerComponent("NetworkLayer", componentid)
    self.linklayer = LinkLayerComponent("LinkLayer", componentid)

    # CONNECTIONS AMONG SUBCOMPONENTS
    self.appllayer.connectTo(PortNames.DOWN, self.netlayer)
    self.netlayer.connectTo(PortNames.UP, self.appllayer)
    self.netlayer.connectTo(PortNames.DOWN, self.linklayer)
    self.linklayer.connectTo(PortNames.UP, self.netlayer)

    # Connect the bottom component to the composite component....
    self.linklayer.connectTo(PortNames.DOWN, self)
    self.connectTo(PortNames.UP, self.linklayer)

    super().__init__(componentname, componentid, self.handlerdict)

def Main():
  cc1 = CompositeComponent("CompositeNodeComponent", 1)
  cc2 = CompositeComponent("CompositeNodeComponent", 2)



  # print(registry.getComponentByInstance(cc.linklayer))
  # print(registry.getComponentByInstance(cc.netlayer))
  # print(registry.getComponentByInstance(cc))

  registry.printComponents()

  time.sleep(5)

  myevent = Event(cc1, "message", "content")
  cc1.trigger_event(myevent)

  while (True): pass

if __name__ == "__main__":
  Main()
