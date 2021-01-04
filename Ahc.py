import os
import uuid
import queue
import datetime
from enum import Enum
import networkx as nx
from utils import Logger
import matplotlib.pyplot as plt
from threading import Thread, Lock

PIPT = 200
DO_DEBUG = "AHC_DEBUG" in os.environ

from uvar_constructs import UVARMobileType

# TIMING ASSUMPTIONS
# TODO: Event handling time, message sending time, assumptions about clock (drift, skew, ...)
# TODO: 1. Asynch,  2. Synch 3. Partial-synch 4. Timed asynch
# TODO: Causal-order (happen before), total-order,
# TODO: Causal-order algebra!!!
# TODO: Implement logical clocks (Lamport clocks, vector clocks) in event handling loop

#  AUTOMATA and EXECUTIONS
# TODO: Let component model hande executions and chekcs on executions (which event, in which order, per process or per system, similarity of executions)


#  VISUALIZATION
# TODO: Space-time diagrams for events

#  TOPOLOGY MANAGEMENT
# TODO: Given a graph as input, generate the topology....

inf = float('inf')

# The following are the common default events for all components.
class EventTypes(Enum):
  INIT = "init"
  MFRB = "msgfrombottom"
  MFRT = "msgfromtop"
  MFRP = "msgfrompeer"

class MessageDestinationIdentifiers(Enum):
  LINKLAYERBROADCAST = -1,  # sinngle-hop broadcast, means all directly connected nodes
  NETWORKLAYERBROADCAST = -2  # For flooding over multiple-hops means all connected nodes to me over one or more links

# A Dictionary that holds a list for the same key
class ConnectorList(dict):
  def __setitem__(self, key, value):
    try:
      self[key]
    except KeyError:
      super(ConnectorList, self).__setitem__(key, [])
    self[key].append(value)

class ConnectorTypes(Enum):
  DOWN = "DOWN"
  UP = "UP"
  PEER = "PEER"

class GenericMessagePayload:
  def __init__(self, messagepayload):
    self.messagepayload = messagepayload

class GenericMessageHeader:
  def __init__(self, messagetype, messagefrom, messageto, nexthop=float('inf'), interfaceid=float('inf'), sequencenumber=None):
    self.messagetype = messagetype
    self.messagefrom = messagefrom
    self.messageto = messageto
    self.nexthop = nexthop
    self.interfaceid = interfaceid
    self.sequencenumber = sequencenumber

    if sequencenumber is None:
      self.sequencenumber = uuid.uuid4().hex

class GenericMessage:
  def __init__(self, header, payload):
    self.header = header
    self.payload = payload
    self.uniqueid = str(header.messagefrom) + "-" + str(header.sequencenumber)

class Event:
  def __init__(self, eventsource, event, eventcontent, fromchannel=None):
    self.eventsource = eventsource
    self.event = event
    self.time = datetime.datetime.now()
    self.eventcontent = eventcontent
    self.fromchannel = fromchannel

def singleton(cls):
  instance = [None]

  def wrapper(*args, **kwargs):
    if instance[0] is None:
      instance[0] = cls(*args, **kwargs)
    return instance[0]

  return wrapper

@singleton
class ComponentRegistry:
  components = {}

  def get_component_by_instance(self, instance):
    list_of_keys = list()
    list_of_items = self.components.items()
    for item in list_of_items:
      if item[1] == instance:
        list_of_keys.append(item[0])
    return list_of_keys

  def add_component(self, component):
    key = component.componentname + str(component.componentinstancenumber)
    self.components[key] = component

  def get_component_by_key(self, componentname, componentinstancenumber):
    key = componentname + str(componentinstancenumber)
    return self.components[key]

  def init(self):
    for itemkey in self.components:
      cmp = self.components[itemkey]

      # NOTE: Changed
      #cmp.inputqueue.put_nowait(Event(self, EventTypes.INIT, None))
      cmp.trigger_event(Event(self, EventTypes.INIT, None))

  def print_components(self):
    for itemkey in self.components:
      cmp = self.components[itemkey]
      print(f"I am {cmp.componentname}.{cmp.componentinstancenumber}")
      for i in cmp.connectors:
        connectedcmp = cmp.connectors[i]
        for p in connectedcmp:
          print(f"\t{i} {p.componentname}.{p.componentinstancenumber}")

registry = ComponentRegistry()

class ComponentModel:
  def on_init(self, eventobj: Event):
    # print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
    pass

  def on_message_from_bottom(self, eventobj: Event):
    print(f"{EventTypes.MFRB} {self.componentname}.{self.componentinstancenumber}")

  def on_message_from_top(self, eventobj: Event):
    print(f"{EventTypes.MFRT}  {self.componentname}.{self.componentinstancenumber}")

  def on_message_from_peer(self, eventobj: Event):
    print(f"{EventTypes.MFRP}  {self.componentname}.{self.componentinstancenumber}")

  def __init__(self, componentname, componentinstancenumber, num_worker_threads=1):
    self.terminated = False
    
    self.eventhandlers = {EventTypes.INIT: self.on_init, EventTypes.MFRB: self.on_message_from_bottom,
                          EventTypes.MFRT: self.on_message_from_top, EventTypes.MFRP: self.on_message_from_peer}
    # Add default handlers to all instantiated components.
    # If a component overwrites the __init__ method it has to call the super().__init__ method
    self.inputqueue = queue.Queue()
    self.componentname = componentname
    self.componentinstancenumber = componentinstancenumber
    self.num_worker_threads = num_worker_threads
    try:
      if self.connectors:
        pass
    except AttributeError:
      self.connectors = ConnectorList()

    self.registry = ComponentRegistry()
    self.registry.add_component(self)

    for i in range(self.num_worker_threads):
      t = Thread(target=self.queue_handler, args=[self.inputqueue])
      t.daemon = True
      t.start()

  def connect_me_to_component(self, name, component):
    try:
      self.connectors[name] = component
    except AttributeError:
      self.connectors = ConnectorList()
      self.connectors[name] = component

  def connect_me_to_channel(self, name, channel):
    try:
      self.connectors[name] = channel
    except AttributeError:
      self.connectors = ConnectorList()
      self.connectors[name] = channel
    connectornameforchannel = self.componentname + str(self.componentinstancenumber)
    channel.connect_me_to_component(connectornameforchannel, self)

  def terminate(self):
    self.terminated = True

  def send_down(self, event: Event):
    #print(f"PL {self.componentinstancenumber} will SEND a message to {event.eventcontent.header.messageto}")

    try:
      for p in self.connectors[ConnectorTypes.DOWN]:
        p.trigger_event(event)
    except:
      pass

  def send_up(self, event: Event):
    #print(f"PL {self.componentinstancenumber} RECVD a message to {event.eventcontent.header.messageto}")

    try:
      for p in self.connectors[ConnectorTypes.UP]:
        p.trigger_event(event)
    except:
      pass

  def send_peer(self, event: Event):
    try:
      for p in self.connectors[ConnectorTypes.PEER]:
        p.trigger_event(event)
    except:
      pass

  def send_self(self, event: Event):
    self.trigger_event(event)

  # noinspection PyArgumentList
  def queue_handler(self, myqueue):
    while not self.terminated:
      workitem = myqueue.get()
      if workitem.event in self.eventhandlers:
        self.eventhandlers[workitem.event](eventobj=workitem)  # call the handler
      else:
        print(f"Event Handler: {workitem.event} is not implemented")
      myqueue.task_done()

  def trigger_event(self, eventobj: Event):
    self.inputqueue.put_nowait(eventobj)

class TickerComponentModel(object):
  terminated = False

  def __init__(self, componentname, componentinstancenumber, process_items_per_tick=PIPT):
    self.logger = Logger(log=DO_DEBUG)

    self.process_items_per_tick = process_items_per_tick

    self.eventhandlers = {EventTypes.INIT: self.on_init, EventTypes.MFRB: self.on_message_from_bottom,
                          EventTypes.MFRT: self.on_message_from_top, EventTypes.MFRP: self.on_message_from_peer}
    # Add default handlers to all instantiated components.
    # If a component overwrites the __init__ method it has to call the super().__init__ method
    self.inputqueue = list()
    self.componentname = componentname
    self.componentinstancenumber = componentinstancenumber
    
    try:
      if self.connectors:
        pass
    except AttributeError:
      self.connectors = ConnectorList()

    self.registry = ComponentRegistry()
    self.registry.add_component(self)

  def on_init(self, eventobj: Event):
    self.logger.debug(f"Initializing {self.componentname}.{self.componentinstancenumber}")

  def on_message_from_bottom(self, eventobj: Event):
    self.logger.debug(f"{EventTypes.MFRB} {self.componentname}.{self.componentinstancenumber}")
    self.send_up(eventobj)

  def on_message_from_top(self, eventobj: Event):
    self.logger.debug(f"{EventTypes.MFRT}  {self.componentname}.{self.componentinstancenumber}")
    self.send_down(eventobj)

  def on_message_from_peer(self, eventobj: Event):
    self.logger.debug(f"{EventTypes.MFRP}  {self.componentname}.{self.componentinstancenumber}")

  def connect_me_to_component(self, name, component):
    try:
      self.connectors[name] = component
    except AttributeError:
      self.connectors = ConnectorList()
      self.connectors[name] = component

  def connect_me_to_channel(self, name, channel):
    try:
      self.connectors[name] = channel
    except AttributeError:
      self.connectors = ConnectorList()
      self.connectors[name] = channel
    connectornameforchannel = self.componentname + str(self.componentinstancenumber)
    channel.connect_me_to_component(connectornameforchannel, self)

  def terminate(self):
    self.terminated = True

  def send_down(self, event: Event):
    self.logger.debug(f"PL {self.componentinstancenumber} will SEND a message to {event.eventcontent.header.messageto}")

    try:
      for p in self.connectors[ConnectorTypes.DOWN]:
        p.trigger_event(event)
    except:
      pass

  def send_up(self, event: Event):
    self.logger.debug(f"PL {self.componentinstancenumber} RECVD a message to {event.eventcontent.header.messageto}")

    try:
      for p in self.connectors[ConnectorTypes.UP]:
        p.trigger_event(event)
    except:
      pass

  def send_peer(self, event: Event):
    try:
      for p in self.connectors[ConnectorTypes.PEER]:
        p.trigger_event(event)
    except:
      pass

  def send_self(self, event: Event):
    self.trigger_event(event)

  def simulation_tick(self):
    self.queue_handler()

  # noinspection PyArgumentList
  def queue_handler(self):
    num_items_processed = 0

    while (num_items_processed < self.process_items_per_tick) and (len(self.inputqueue) > 0):
      workitem = self.inputqueue.pop(0)

      if workitem.event in self.eventhandlers:
        self.eventhandlers[workitem.event](eventobj=workitem)  # call the handler
      else:
        self.logger.warn(f"Event Handler: {workitem.event} is not implemented")

      num_items_processed += 1

  def trigger_event(self, eventobj: Event):
    self.inputqueue.append(eventobj)


@singleton
class Topology:
  nodes = {}
  channels = {}

  def construct_from_graph(self, G: nx.Graph, nodetype, channeltype):
    self.G = G
    nodes = list(G.nodes)
    edges = list(G.edges)

    self.channeltype = channeltype

    for nodename in nodes:
      cc = nodetype(nodetype.__name__, nodename)

      if nodename[0] == "U":
        cc.appllayer.mobile_type = UVARMobileType.UAV
      if nodename[0] == "C":
        cc.appllayer.mobile_type = UVARMobileType.CAR

      self.nodes[nodename] = cc
    for k in edges:
      #ch = channeltype(channeltype.__name__, str(k[0]) + "-" + str(k[1]))
      #self.channels[k] = ch
      #self.nodes[k[0]].connect_me_to_channel(ConnectorTypes.DOWN, ch)
      #self.nodes[k[1]].connect_me_to_channel(ConnectorTypes.DOWN, ch)
      self.nodes[k[0]].connect_me_to_component(ConnectorTypes.DOWN, self.nodes[k[1]])
      self.nodes[k[1]].connect_me_to_component(ConnectorTypes.DOWN, self.nodes[k[0]])

  def update_graph_edges(self, new_G):
    #del self.channels

    #for ch in self.channels.values():
    #  ch.terminate()
    #  del ch
#
    #self.channels = {}

    edges = list(new_G.edges)

    for k in edges:
      #ch = self.channeltype(self.channeltype.__name__, str(k[0]) + "-" + str(k[1]))
      #self.channels[k] = ch
      #self.nodes[k[0]].connect_me_to_channel(ConnectorTypes.DOWN, ch)
      #self.nodes[k[1]].connect_me_to_channel(ConnectorTypes.DOWN, ch)

      self.nodes[k[0]].connect_me_to_component(ConnectorTypes.DOWN, self.nodes[k[1]])
      self.nodes[k[1]].connect_me_to_component(ConnectorTypes.DOWN, self.nodes[k[0]])

    self.G = new_G
    self.compute_forwarding_table()

  def construct_single_node(self, nodetype, instancenumber):
    self.singlenode = nodetype(nodetype.__name__, instancenumber)
    self.G = nx.Graph()
    self.G.add_nodes_from([0])
    self.nodes[0] = self.singlenode

  def construct_sender_receiver(self, sendertype, receivertype, channeltype):
    self.sender = sendertype(sendertype.__name__, 0)
    self.receiver = receivertype(receivertype.__name__, 1)
    ch = channeltype(channeltype.__name__, "0-1")
    self.G = nx.Graph()
    self.G.add_nodes_from([0, 1])
    self.G.add_edges_from([(0, 1)])
    self.nodes[self.sender.componentinstancenumber] = self.sender
    self.nodes[self.sender.componentinstancenumber] = self.receiver
    self.channels[ch.componentinstancenumber] = ch
    self.sender.connect_me_to_channel(ConnectorTypes.DOWN, ch)
    self.receiver.connect_me_to_channel(ConnectorTypes.DOWN, ch)

  def allpairs_shortest_path(self):
    return dict(nx.all_pairs_shortest_path(self.G))

  def shortest_path_to_all(self, myid):
    path = dict(nx.all_pairs_shortest_path(self.G))
    nodecnt = len(self.G.nodes)
    for i in range(nodecnt):
      print(path[myid][i])

  def start(self):
    # registry.printComponents()
    N = len(self.G.nodes)
    self.compute_forwarding_table()
    self.nodecolors = ['b'] * N
    self.nodepos = nx.drawing.spring_layout(self.G)
    self.lock = Lock()
    ComponentRegistry().init()

  def compute_forwarding_table(self):
    N = len(self.G.nodes)
    self.ForwardingTable = {n1: {n2: None for n2 in self.G.nodes} for n1 in self.G.nodes}
    path = dict(nx.all_pairs_shortest_path(self.G))
    # print(f"There are {N} nodes")
    nodes_list = list(self.G.nodes)
    for i in range(N):
      for j in range(N):
        n1 = nodes_list[i]
        n2 = nodes_list[j]

        try:
          mypath = path[n1][n2]
          # print(f"{i}to{j} path = {path[i][j]} nexthop = {path[i][j][1]}")
          self.ForwardingTable[n1][n2] = path[n1][n2][1]
        except KeyError:
          # print(f"{i}to{j}path = NONE")
          self.ForwardingTable[n1][n2] = inf  # No paths
        except IndexError:
          # print(f"{i}to{j} nexthop = NONE")
          self.ForwardingTable[n1][n2] = n1  # There is a path but length = 1 (self)

  # all-seeing eye routing table contruction
  def print_forwarding_table(self):
    registry.print_components()
    print(self.ForwardingTable)
    #print('\n'.join([''.join(['{:4}'.format(item) for item in row])
    #                 for row in self.ForwardingTable]))

  # returns the all-seeing eye routing based next hop id
  def get_next_hop(self, fromId, toId):
    return self.ForwardingTable[fromId][toId]

  # Returns the list of neighbors of a node
  def get_neighbors(self, nodeId):
    return sorted([neighbor for neighbor in self.G.neighbors(nodeId)])

  def get_predecessors(self, nodeId):
    return sorted([neighbor for neighbor in self.G.predecessors(nodeId)])

  def get_successors(self, nodeId):
    return sorted([neighbor for neighbor in self.G.neighbors(nodeId)])


  # Returns the list of neighbors of a node
  def get_neighbor_count(self, nodeId):
    # return len([neighbor for neighbor in self.G.neighbors(nodeId)])
    return self.G.degree[nodeId]

  def plot(self):
    #self.lock.acquire()
    nx.draw(self.G, self.nodepos, node_color=self.nodecolors, with_labels=True, font_weight='bold')
    plt.draw()
    print(self.nodecolors)
    #self.lock.release()
