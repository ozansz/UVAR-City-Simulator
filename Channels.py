import queue
import random
from threading import Thread

from Ahc import Event
from Ahc import ComponentModel, EventTypes, ConnectorList
from enum import Enum

# TODO: Channel failure models: lossy-link, fair-loss, stubborn links, perfect links (WHAT ELSE?), FIFO perfect
# TODO: Logged perfect links (tolerance to crashes), authenticated perfect links
# TODO: Broadcast channels? and their failure models? Collisions?
# TODO: Properties of all models separately: e.g., Fair loss, finite duplication, no fabrication in fair-loss link model
# TODO: Packets: loss, duplication, sequence change, windowing?,
# TODO: Eventually (unbounded time) or bounded time for message delivery?


# Channels have three events: sendtochannel, processinchannel and delivertocomponent
# Components tell channels to handle a message by the EventTypes.MFRT event, the component calls senddown with the event EventTypes.MFRT
# First pipeline stage moves the message to the interim pipeline stage with the "processinchannel" event for further processing, such as  the channel may drop it, delay it, or whatever
# Channels deliver the message to output queue by the "delivertocomponent" event
# The output queue then will send the message up to the connected component(s) using the "messagefromchannel" event
# The components that will use the channel directly, will have to handle "messagefromchannel" event

class ChannelEventTypes(Enum):
  PROCESSINCHANNEL = "processinchannel"
  DELIVERTOCOMPONENT = "delivertocomponent"

class Channel(ComponentModel):

  # Overwrite onSendToChannel if you want to do something in the first pipeline stage
  def onMessageFromTop(self, eventobj: Event):
    # channel receives the input message and will process the message by the process event in the next pipeline stage
    myevent = Event(self, ChannelEventTypes.PROCESSINCHANNEL, eventobj.eventcontent)
    self.channelqueue.put_nowait(myevent)

  # Overwrite onProcessInChannel if you want to do something in interim pipeline stage
  def onProcessInChannel(self, eventobj: Event):
    # Add delay, drop, change order whatever....
    # Finally put the message in outputqueue with event deliver
    myevent = Event(self, ChannelEventTypes.DELIVERTOCOMPONENT, eventobj.eventcontent)
    self.outputqueue.put_nowait(myevent)

  # Overwrite onDeliverToComponent if you want to do something in the last pipeline stage
  # onDeliver will deliver the message from the channel to the receiver component using messagefromchannel event
  def onDeliverToComponent(self, eventobj: Event):
    callername = eventobj.eventsource.componentinstancenumber
    for item in self.connectors:
      callees = self.connectors[item]
      for callee in callees:
        calleename = callee.componentinstancenumber
        # print(f"I am connected to {calleename}. Will check if I have to distribute it to {item}")
        if calleename == callername:
          pass
        else:
          myevent = Event(self, EventTypes.MFRB, eventobj.eventcontent)
          callee.triggerevent(myevent)

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.outputqueue = queue.Queue()
    self.channelqueue = queue.Queue()
    self.eventhandlers[EventTypes.MFRT] = self.onMessageFromTop
    self.eventhandlers[ChannelEventTypes.PROCESSINCHANNEL] = self.onProcessInChannel
    self.eventhandlers[ChannelEventTypes.DELIVERTOCOMPONENT] = self.onDeliverToComponent

    for i in range(self.num_worker_threads):
      # note that the input queue is handled by the super class...
      tout = Thread(target=self.queuehandler, args=[self.outputqueue])
      tout.daemon = True
      tch = Thread(target=self.queuehandler, args=[self.channelqueue])
      tch.daemon = True
      tch.start()
      tout.start()

class AHCChannelError(Exception):
  pass

class P2PFIFOPerfectChannel(Channel):

  def onDeliverToComponent(self, eventobj: Event):
    msg = eventobj.eventcontent
    nexthop = msg.header.nexthop
    callername = eventobj.eventsource.componentinstancenumber
    for item in self.connectors:
      callees = self.connectors[item]
      for callee in callees:
        calleename = callee.componentinstancenumber
        # print(f"I am connected to {calleename}. Will check if I have to distribute it to {item}")
        if calleename == callername:
          pass
        else:
          myevent = Event(self, EventTypes.MFRB, eventobj.eventcontent)
          callee.triggerevent(myevent)


  # Overwriting to limit the number of connected components
  def connectMeToComponent(self, name, component):
    try:
      self.connectors[name] = component
      # print(f"Number of nodes connected: {len(self.ports)}")
      if len(self.connectors) > 2:
        raise AHCChannelError("More than two nodes cannot connect to a P2PFIFOChannel")
    except AttributeError:
      self.connectors = ConnectorList()
      self.connectors[name] = component
    # except AHCChannelError as e:
    #    print( f"{e}" )

class P2PFIFOFairLossChannel(P2PFIFOPerfectChannel):
  prob = 1
  duplicationprobability = 0

  def onProcessInChannel(self, eventobj: Event):
    if random.random() < self.prob:
      myevent = Event(self, ChannelEventTypes.DELIVERTOCOMPONENT, eventobj.eventcontent)
      self.outputqueue.put_nowait(myevent)
    if random.random() < self.duplicationprobability:
      self.channelqueue.put_nowait(eventobj)

  def setPacketLossProbability(self, prob):
    self.prob = prob

  def setAverageNumberOfDuplicates(self, d):
    if d > 0:
      self.duplicationprobability = (d - 1) / d
    else:
      self.duplicationprobability = 0

class FIFOBroadcastPerfectChannel(Channel):
  pass
