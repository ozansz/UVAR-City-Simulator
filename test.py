from Ahc import GenericComponentModel
from Ahc import Event
from Ahc import ComponentRegistry
import threading

class Component(GenericComponentModel):
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
    super().__init__(componentname, componentid, self.handlerdict)

registry = ComponentRegistry()

class CompositeComponent(GenericComponentModel):

  def onMessage(self, eventobj: Event):
    myevent = Event(self, "internalmessage", "content")
    if self.upout:
      self.upout.trigger_event(myevent)
    if self.downout:
      self.downout.trigger_event(myevent)

  def onInternalMessage(self, eventobj: Event):
    print(f"I am {self.componentname}: {eventobj.caller.componentname} called me at {eventobj.time}")
    myevent = Event(self, "message", "content")
    if self.upout:
      self.upout.trigger_event(myevent)
    if self.downout:
      self.downout.trigger_event(myevent)

  handlerdict = {
    "message": onMessage,
    "internalmessage": onInternalMessage
  }

  def __init__(self, componentname, componentid):
    self.appllayer = Component("ApplicationLayer", componentid)
    self.netlayer = Component("NetworkLayer", componentid)
    self.linklayer = Component("LinkLayer", componentid)

    registry.linkComponents(self.appllayer,self.netlayer)
    registry.linkComponents(self.netlayer,self.linklayer)
    # registry.linkComponentsbyKey("NetworkLayer",componentid, "LinkLayer",componentid)

    super().__init__(componentname, componentid, self.handlerdict)

def Main():
  cc = CompositeComponent("CompositeNodeComponent", 1)

  myevent = Event(cc, "message", "content")
  cc.trigger_event(myevent)

  registry.linkComponents(cc, cc.linklayer)

  print(registry.getComponentByInstance(cc.linklayer))
  print(registry.getComponentByInstance(cc.netlayer))
  print(registry.getComponentByInstance(cc))

  while (True): pass

if __name__ == "__main__":
  Main()
