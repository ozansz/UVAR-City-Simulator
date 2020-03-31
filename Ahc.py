import datetime
import queue
from enum import Enum
from threading import Thread, Lock

import matplotlib.pyplot as plt
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

inf = float('inf')

class EventTypes(Enum):
  INIT = "init"
  MFRB = "msgfrombottom"
  MFRT = "msgfromtop"
  MFRP = "msgfrompeer"



class MessageDestinationIdentifiers(Enum):
  LINKLAYERBROADCAST = -1,  # sinngle-hop broadcast, means all directly connected nodes
  NETWORKLAYERBROADCAST = -2  # For flooding over multiple-hops means all connected nodes to me over one or more links

# A Dictionary that holds a list for the same key
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
  PEER = "PORTTOPEER"

class GenericMessagePayload():
  def __init__(self, messagepayload):
    self.messagepayload = messagepayload

class GenericMessageHeader():
  def __init__(self, messagetype, messagefrom, messageto, nexthop=float('inf'), sequencenumber=-1):
    self.messagetype = messagetype
    self.messagefrom = messagefrom
    self.messageto = messageto
    self.nexthop = nexthop
    self.sequencenumber = sequencenumber

class GenericMessage:
  def __init__(self, header, payload):
    self.header = header
    self.payload = payload
    self.uniqueid = str(header.messagefrom) + "-" + str(header.sequencenumber)

class Event:
  def __init__(self, eventsource, event, eventcontent):
    self.eventsource = eventsource
    self.event = event
    self.time = datetime.datetime.now()
    self.eventcontent = eventcontent

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
      cmp.inputqueue.put_nowait(Event(self, EventTypes.INIT, None))

  def printComponents(self):
    for itemkey in self.components:
      cmp = self.components[itemkey]
      print(f"I am {cmp.componentname}.{cmp.componentinstancenumber}")
      for i in cmp.ports:
        connectedcmp = cmp.ports[i]
        for p in connectedcmp:
          print(f"\t{i} {p.componentname}.{p.componentinstancenumber}")

registry = ComponentRegistry()

class ComponentModel:

  def onInit(self, eventobj: Event):
    print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromBottom(self, eventobj: Event):
    print(f"{EventTypes.MFRB} {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromTop(self, eventobj: Event):
    print(f"{EventTypes.MFRT}  {self.componentname}.{self.componentinstancenumber}")

  def onMessageFromPeer(self, eventobj: Event):
    print(f"{EventTypes.MFRP}  {self.componentname}.{self.componentinstancenumber}")

  def __init__(self, componentname, componentinstancenumber, num_worker_threads=1):
    self.eventhandlers = {}
    # Add default handlers to all instantiated components.
    # If a component overwrites the __init__ method it has to call the super().__init__ method
    self.eventhandlers[EventTypes.INIT] = self.onInit
    self.eventhandlers[EventTypes.MFRB] = self.onMessageFromBottom
    self.eventhandlers[EventTypes.MFRT] = self.onMessageFromTop
    self.eventhandlers[EventTypes.MFRP] = self.onMessageFromPeer
    self.inputqueue = queue.Queue()
    self.componentname = componentname
    self.componentinstancenumber = componentinstancenumber
    self.num_worker_threads = num_worker_threads
    try:
      if self.ports:
        pass
    except AttributeError:
      self.ports = PortList()

    self.registry = ComponentRegistry()
    self.registry.addComponent(self)

    for i in range(self.num_worker_threads):
      t = Thread(target=self.queuehandler, args=[self.inputqueue])
      t.daemon = True
      t.start()

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
        p.triggerevent(event)
    except:
      pass

  def sendup(self, event: Event):
    try:
      for p in self.ports[PortNames.UP]:
        p.triggerevent(event)
    except:
      pass

  def sendpeers(self, event: Event):
    try:
      for p in self.ports[PortNames.PEER]:
        p.triggerevent(event)
    except:
      pass


  def sendself(self, event: Event):
    self.triggerevent(event)

  def queuehandler(self, myqueue):
    while True:
      workitem = myqueue.get()
      if workitem.event in self.eventhandlers:
        # print(f"OUTPUT I am {self.eventhandlers[workitem.event]}: {workitem.caller.componentname} called me at {workitem.time}" )
        self.eventhandlers[workitem.event](eventobj=workitem)  # call the handler
      else:
        print(f"Event Handler: {workitem.event} is not implemented")
      myqueue.task_done()

  def triggerevent(self, eventobj: Event):
    self.inputqueue.put_nowait(eventobj)

@singleton
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
      ch = channeltype(channeltype.__name__, str(k[0]) + "-" + str(k[1]))
      self.channels[k] = ch
      # print(f"Edges: Node {k[0]} is connected to Node {k[1]}")
      self.nodes[k[0]].connectMeToChannel(PortNames.DOWN, ch)
      self.nodes[k[1]].connectMeToChannel(PortNames.DOWN, ch)

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

  def allpairsshortestpath(self):
    return dict(nx.all_pairs_shortest_path(self.G))

  def shortestpathtoall(self, myid):
    path = dict(nx.all_pairs_shortest_path(self.G))
    nodecnt = len(self.G.nodes)
    for i in range(nodecnt):
      print(path[myid][i])

  def start(self):
    # registry.printComponents()
    N = len(self.G.nodes)
    self.computeForwardingTable()
    self.nodecolors = ['b'] * N
    self.nodepos = nx.drawing.spring_layout(self.G)
    self.lock = Lock()
    ComponentRegistry().init()

  def computeForwardingTable(self):

    N = len(self.G.nodes)
    self.ForwardingTable = [[0 for i in range(N)] for j in range(N)]
    path = dict(nx.all_pairs_shortest_path(self.G))
    print(f"There are {N} nodes")
    for i in range(N):
      for j in range(N):
        try:
          mypath = path[i][j]
          # print(f"{i}to{j} path = {path[i][j]} nexthop = {path[i][j][1]}")
          self.ForwardingTable[i][j] = path[i][j][1]
        except KeyError:
          # print(f"{i}to{j}path = NONE")
          self.ForwardingTable[i][j] = inf  # No paths
        except IndexError:
          # print(f"{i}to{j} nexthop = NONE")
          self.ForwardingTable[i][j] = i  # There is a path but length = 1 (self)

  # all-seeing eye routing table contruction
  def printForwardingTable(self):
    registry.printComponents()
    print('\n'.join([''.join(['{:4}'.format(item) for item in row])
                     for row in self.ForwardingTable]))

  # returns the all-seeing eye routing based next hop id
  def getNextHop(self, fromId, toId):
    return self.ForwardingTable[fromId][toId]

  # Returns the list of neighbors of a node
  def getNeighbors(self, nodeId):
    return sorted([neighbor for neighbor in self.G.neighbors(nodeId)])

  def plot(self):
    self.lock.acquire()
    nx.draw(self.G, self.nodepos, node_color=self.nodecolors, with_labels=True, font_weight='bold')
    plt.draw()
    self.lock.release()
