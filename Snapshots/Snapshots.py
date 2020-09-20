import time
from enum import Enum

from Ahc import ComponentModel, Event, GenericMessageHeader, GenericMessagePayload, GenericMessage, Topology, \
  MessageDestinationIdentifiers, EventTypes

"A snapshot of an execution of a distributed algorithm is a configuration of this execution, consisting of the local states of the processes and the messages in transit. Snapshots are useful to try to determine offline properties that will remain true as soon as they have become true, such as deadlock, termination or garbage. Moreover, snapshots can be used for checkpointing to restart after a failure, or for debugging. " \
"" \
"Suppose that a process that is involved in the execution of a distributed algorithm wants to make a snapshot of a configuration of the ongoing execution. Then it should ask all processes to take a snapshot of their local state. Processes moreover have to compute channel states, of messages that were in transit at the moment of the snapshot. The challenge is to develop a snapshot algorithm that works at run-time, that is, without freezing the execution of the basic algorithm of which the snapshot is taken. Messages of the basic algorithm are called basic messages, while messages of the snapshot algorithm are called control messages." \
"" \
"A complication is that processes take local snapshots and compute channel states at different moments in time. Therefore, a snapshot may actually not represent a configuration of the ongoing execution, but a configuration of an execution in the same computation is good enough. Such a snapshot is called consistent."

"The  state-detection  algorithm  plays  the  role  of  a  group  of  photographers observing a panoramic,  dynamic  scene, such as a sky filled  with  migrating  birds- a scene so vast  that  it  cannot  be captured  by  a single  photograph.  The  photog- raphers  must  take  several snapshots  and piece the  snapshots  together  to  form  a picture  of the  overall  scene. The  snapshots  cannot  all  be taken  at precisely  the same instant  because of synchronization  problems.  Furthermore,  the  photographers  should  not  disturb  the  process that  is  being  photographed;  for  instance, they  cannot  get  all  the  birds  in  the  heavens  to  remain  motionless  while  the photographs  are taken.  Yet,  the  composite  picture  should  be meaningful.  The problem  before  us  is  to  define  “meaningful”  and  then  to  determine  how  the photographs  should  be taken. "

class SnapshotsEventTypes(Enum):
  TAKESNAPSHOT = "takesnapshot"

# define your own message types
class SnapshotsMessageTypes(Enum):
  MARKER = "marker"

# define your own message header structure
class SnapshotsMessageHeader(GenericMessageHeader):
  pass

# define your own message payload structure
class SnapshotsMessagePayload(GenericMessagePayload):
  pass

# CHANDY-LAMPORT SNAPSHOT ALGORITHM
"K. Mani Chandy and Leslie Lamport. 1985. Distributed snapshots: determining global states of distributed systems. ACM Trans. Comput. Syst. 3, 1 (Feb. 1985), 63–75. DOI:https://doi.org/10.1145/214451.214456"

"The Chandy-Lamport snapshot algorithm requires that channels are FIFO. Any initiator can decide to take a local snapshot of its state. It then sends a control message marker through all its outgoing channels to let its neighbors take a snapshot too. When a process that has not yet taken a snapshot receives a marker message, it takes a local snapshot of its state, and sends a marker message through all its outgoing channels. A process q computes as channel state for an incoming channel pq the (basic) messages that it receives via pq after taking its local snapshot and before receiving a marker message from p. The Chandy-Lamport algorithm terminates at a process when it has received a marker message through all its incoming channels."

# Assumption 1: Directed network: A  distributed  system  consists  of  a  finite  set  of  processes and  a  finite  set  of channels.  It  is described  by  a  labeled,  directed  graph  in  which  the  vertices represent  processes and the  edges represent  channels.
# Assumption 2: FIFO channel Channels  are assumed to  have infinite  buffers,  to  be error-free,  and to  deliver messages in  the  order  sent.

class ChandyLamportSnapshot(ComponentModel):

  def update_topology(self):
#    Topology().lock.acquire()
    Topology().nodecolors[self.componentinstancenumber] = 'r'
    Topology().plot()
#    Topology().lock.release()

  # Default initiator for all processes
  def on_init(self, eventobj: Event):
    self.uniquebroadcastidentifier = 0
    self.recorded = False
    self.marker = {}
    self.my_predecessors = Topology().get_predecessors(self.componentinstancenumber)
    self.myneighbors = Topology().get_neighbors(self.componentinstancenumber)
    for i in self.my_predecessors:
      ch = str(i) + "-" + str(self.componentinstancenumber)
      self.marker[ch] = False
    #print(f"\nI am {self.componentinstancenumber}, My markers={self.marker}")
    # The following piece of code is for debugging: Node 0 initiates the snapshot algorithm
    if self.componentinstancenumber == 0:
      time.sleep(2)
      self.send_self(Event(self, SnapshotsEventTypes.TAKESNAPSHOT, None))

  def send_down_broadcast(self, eventobj: Event, whosends):
    applmsg = eventobj.eventcontent
    destination = MessageDestinationIdentifiers.NETWORKLAYERBROADCAST
    nexthop = MessageDestinationIdentifiers.LINKLAYERBROADCAST
    hdr = SnapshotsMessageHeader(SnapshotsMessageTypes.MARKER, whosends, destination, nexthop,
                                 self.uniquebroadcastidentifier)
    self.uniquebroadcastidentifier = self.uniquebroadcastidentifier + 1
    #print(f"\n{self.componentinstancenumber} will broadcast {hdr.messagetype} ")
    payload = applmsg
    broadcastmessage = GenericMessage(hdr, payload)
    self.send_down(Event(self, EventTypes.MFRT, broadcastmessage))

  def send_down_onebyone(self, eventobj: Event, whosends):
    for i in self.myneighbors:
      applmsg = eventobj.eventcontent
      destination = i
      nexthop = i
      hdr = SnapshotsMessageHeader(SnapshotsMessageTypes.MARKER, whosends, destination, nexthop,
                                   self.uniquebroadcastidentifier)
      self.uniquebroadcastidentifier = self.uniquebroadcastidentifier + 1
      #print(f"\n{self.componentinstancenumber} will send {hdr.messageto} a {hdr.messagetype} message")
      payload = applmsg
      broadcastmessage = GenericMessage(hdr, payload)
      self.send_down(Event(self, EventTypes.MFRT, broadcastmessage))

  def take_local_snapshot(self):
    if not self.recorded:
      self.update_topology()
      self.recorded = True
      # Take local snapshot
      print(f"\n{self.componentinstancenumber} TOOK THE SNAPHOT")
      # Send marker message from each outgoing channels
      self.uniquebroadcastidentifier = self.uniquebroadcastidentifier + 1
      eventobj = Event(self, SnapshotsEventTypes.TAKESNAPSHOT, None)
      #time.sleep(1)
      self.send_down_onebyone(eventobj, self.componentinstancenumber)
      #self.send_down_broadcast(eventobj, self.componentinstancenumber)

  # TakeSnapShot initites the snaphot algorithm, the process who will start the whole procedure will generate TAKESNAPSHOT event
  def on_take_snapshot(self, eventobj: Event):
    print(f"I WILL START SNAPHOT: My id={self.componentname}:{self.componentinstancenumber}")
    self.take_local_snapshot()

  def on_message_from_top(self, eventobj: Event):
    pass

  def on_message_from_bottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    ch = eventobj.fromchannel
    if ch in self.marker:
      if hdr.messagetype == SnapshotsMessageTypes.MARKER:
        #print(f"{self.componentname}:{self.componentinstancenumber} The message comes from {eventobj.fromchannel}")
        self.take_local_snapshot()
        self.marker[ch] = True
        #print(f"I am {self.componentinstancenumber} and my markers={self.marker}")
        res = all(self.marker.values())  # Test Boolean Value of Dictionary
        if res:
          print(f"{self.componentinstancenumber} TERMINATED")
          print(Topology().nodecolors)
          self.update_topology()
          #self.terminate()
          # terminate
      else:
        if self.recorded == True and self.marker[ch] == False:
          # put the message in snapshot state data structure (whatever that is)
          # statep[c0] ← append(statep[c0],m);
          pass
        else:
          pass

  def __init__(self, componentname, componentinstancenumber):
    super().__init__(componentname, componentinstancenumber)
    self.eventhandlers[SnapshotsEventTypes.TAKESNAPSHOT] = self.on_take_snapshot
    # add events here
