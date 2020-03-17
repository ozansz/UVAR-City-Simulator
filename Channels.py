from Ahc import GenericComponentModel
from Ahc import Event
import time

class GenericChannel(GenericComponentModel):
  pass

class AHCChannelError(Exception):
  pass

class P2PFIFOChannel(GenericChannel):
  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def connectMeToComponent(self, name, component):
    try:
      self.ports[name] = component
      print(f"Number of nodes connected: {len(self.ports)}")
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

  eventhandlers = {
    "init": onInit,
    "message": onMessage
  }

class FIFOBroadcastChannel(GenericChannel):
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

  eventhandlers = {
    "init": onInit,
    "message": onMessage
  }
