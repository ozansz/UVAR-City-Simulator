import queue
from threading import Thread
import datetime
from enum import Enum
import networkx as nx

#############TIMING ASSUMPTIONS
# TODO: Event handling time, message sending time, assumptions about clock (drift, skew, ...)
# TODO: 1. Asynch,  2. Synch 3. Partial-synch 4. Timed asynch
# TODO: Causal-order (happen before), total-order,
# TODO: Causal-order algebra!!!
# TODO: Implement logical clocks (Lamport clocks, vector clocks) in event handling loop

###### AUTOMATA and EXECUTIONS
# TODO: Let component model hande executions and chekcs on executions (which event, in which order, per process or per system, similarity of executions)


##### VISUALIZATION
# TODO: Space-time diagrams for events

###### TOPOLOGY MANAGEMENT
# TODO: Given a graph as input, generate the topology....


class MessageDestinationIdentifiers(Enum):
  LINKLAYERBROADCAST = "LINKLAYERBROADCAST",  # sinngle-hop broadcast, means all directly connected nodes
  NETWORKLAYERBROADCAST = "NETWORKLAYERBROADCAST"  # For flooding over multiple-hops means all connected nodes to me over one or more links

class PortList(dict):
  def __setitem__(self, key, value):
    try:
      self[key]
    except KeyError:
      super(PortList, self).__setitem__(key, [])
    self[key].append(value)

class PortNames(Enum):
  DOWN = "PORTDOWN"
  UP = "PORTUP"

class GenericMessagePayload():
  def __init__(self, messagepayload):
    self.messagepayload = messagepayload

class GenericMessageHeader():
  def __init__(self, messagetype, messagefrom, messageto):
    self.messagetype = messagetype
    self.messagefrom = messagefrom
    self.messageto = messageto

class GenericMessage:
  def __init__(self, header, payload):
    self.header = header
    self.payload = payload


class Event:
  def __init__(self, caller, event, messagecontent):
    self.caller = caller
    self.event = event
    self.time = datetime.datetime.now()
    self.messagecontent = messagecontent


def singleton(cls):
  instance = [None]

  def wrapper(*args, **kwargs):
    if instance[0] is None:
      instance[0] = cls(*args, **kwargs)
    return instance[0]

  return wrapper

@singleton
class ComponentRegistry():
  components = {}

  def getComponentByInstance(self, instance):
    listOfKeys = list()
    listOfItems = self.components.items()
    for item in listOfItems:
      if item[1] == instance:
        listOfKeys.append(item[0])
    return listOfKeys

  def addComponent(self, component):
    key = component.componentname + str(component.componentinstancenumber)
    self.components[key] = component

  def getComponentByKey(self, componentname, componentinstancenumber):
    key = componentname + str(componentinstancenumber)
    return self.components[key]

  def init(self):
    for itemkey in self.components:
      cmp = self.components[itemkey]
      cmp.inputqueue.put_nowait(Event(self, "init", None))

  def printComponents(self):
    for itemkey in self.components:
      cmp = self.components[itemkey]
      print(f"I am {cmp.componentname}.{cmp.componentinstancenumber}")
      for i in cmp.ports:
        connectedcmp = cmp.ports[i]
        for p in connectedcmp:
          print(f"\t{i} {p.componentname}.{p.componentinstancenumber}")

registry = ComponentRegistry()

class GenericComponentModel:

#  def onInit(self, eventobj: Event):
#    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def __init__(self, componentname, componentinstancenumber, num_worker_threads=2):
    self.eventhandlers = {}
    self.eventhandlers["init"] = self.onInit
    self.inputqueue = queue.Queue()
    self.componentname = componentname
    self.componentinstancenumber = componentinstancenumber
    try:
      if self.ports:
        pass
    except AttributeError:
      self.ports = PortList()

    self.registry = ComponentRegistry()
    self.registry.addComponent(self)




    for i in range(num_worker_threads):
      t = Thread(target=self.worker)
      t.daemon = True
      t.start()


  #eventhandlers = {
  #  "init": onInit
  #}


  def connectMeToComponent(self, name, component):
    try:
      self.ports[name] = component
    except AttributeError:
      self.ports = PortList()
      self.ports[name] = component

  def connectMeToChannel(self, name, channel):
    try:
      self.ports[name] = channel
    except AttributeError:
      self.ports = PortList()
      self.ports[name] = channel
    portnameforchannel = self.componentname + str(self.componentinstancenumber)
    channel.connectMeToComponent(portnameforchannel, self)

  def senddown(self, event: Event):
    try:
      for p in self.ports[PortNames.DOWN]:
        p.trigger_event(event)
    except KeyError:
      pass

  def sendup(self, event: Event):
    try:
      for p in self.ports[PortNames.UP]:
        p.trigger_event(event)
    except:
      pass

  def sendself(self, event: Event):
    self.trigger_event(event)

  def worker(self):
    while True:
      workitem = self.inputqueue.get()
      if workitem.event in self.eventhandlers:
        # print(
        #    f"I am {self.eventhandlers[workitem.event]}: {workitem.caller.componentname} called me at {workitem.time}" )
        self.eventhandlers[workitem.event](eventobj=workitem)  # call the handler
      else:
        print(f"Event Handler: {workitem.event} is not implemented")
      self.inputqueue.task_done()

  def trigger_event(self, eventobj: Event):
    self.inputqueue.put_nowait(eventobj)


class Topology():
  nodes = {}
  channels = {}

  def constructFromGraph(self, G: nx.Graph, nodetype, channeltype):
    self.G = G
    nodes = list(G.nodes)
    edges = list(G.edges)
    for i in nodes:
      cc = nodetype(nodetype.__name__, i)
      self.nodes[i] = cc
    for k in edges:
      ch = channeltype(channeltype.__name__, str(k[0])+"-"+str(k[1]))
      self.channels[k] = ch
      print(f"Edges: Node {k[0]} is connected to Node {k[1]}")
      self.nodes[k[0]].connectMeToChannel(PortNames.DOWN, ch)
      self.nodes[k[1]].connectMeToChannel(PortNames.DOWN, ch)

    registry.printComponents()
    ComponentRegistry().init()


  def constructSenderReceiver(self, sendertype, receivertype, channeltype):

    self.sender = sendertype(sendertype.__name__, 0)
    self.receiver = receivertype(receivertype.__name__, 1)
    ch = channeltype(channeltype.__name__, "0-1")

    self.G = nx.Graph()
    self.G.add_nodes_from([0, 1])
    self.G.add_edges_from([(0, 1)])

    self.nodes["0"] = self.sender
    self.nodes["1"] = self.receiver
    self.channels["0-1"] = ch

    self.sender.connectMeToChannel(PortNames.DOWN, ch)
    self.receiver.connectMeToChannel(PortNames.DOWN, ch)

  def start(self):
    #registry.printComponents()
    ComponentRegistry().init()
