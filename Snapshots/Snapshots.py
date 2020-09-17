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
  SNAPSHOT = "snapshot"

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

  def updateTopology(self):
    Topology().nodecolors[self.componentinstancenumber] = 'r'
    Topology().plot()

  # Default initiator for all processes
  def onInit(self, eventobj: Event):
    self.uniquebroadcastidentifier = 0
    self.recorded = False
    degree = Topology().getNeighborCount(self.componentinstancenumber)
    self.marker = {}
    myneighbors = Topology().getNeighbors(self.componentinstancenumber)
    print(f"I am {self.componentinstancenumber}, neighbors={myneighbors}")
    for i in myneighbors:
      ch = str(i) + "-" + str(self.componentinstancenumber)
      print(f"Channel={ch} {i}-{self.componentinstancenumber}")
      self.marker[ch] = False
    print(f"I am {self.componentinstancenumber}, My markers={self.marker}")

  def onSnapshot(self, eventobj: Event):
    pass

  def senddownbroadcast(self, eventobj: Event, whosends, sequencenumber):
    applmsg = eventobj.eventcontent
    destination = MessageDestinationIdentifiers.NETWORKLAYERBROADCAST
    nexthop = MessageDestinationIdentifiers.LINKLAYERBROADCAST
    print(f"{self.componentinstancenumber} will SEND a message to {destination} over {nexthop}")
    hdr = SnapshotsMessageHeader(SnapshotsMessageTypes.MARKER, whosends, destination,
                                 nexthop, sequencenumber)
    payload = applmsg
    broadcastmessage = GenericMessage(hdr, payload)
    self.senddown(Event(self, EventTypes.MFRT, broadcastmessage))

  def takeSnapshot(self):
    if self.recorded == False:
      self.recorded = True
      # Send marker message from each outgoing channels
      # Take local snapshot
      print(f"I TOOK THE SNAPHOT: My id={self.componentname}:{self.componentinstancenumber}")
      self.uniquebroadcastidentifier = self.uniquebroadcastidentifier + 1
      eventobj = Event(self, SnapshotsEventTypes.TAKESNAPSHOT, None)
      self.senddownbroadcast(eventobj, self.componentinstancenumber, self.uniquebroadcastidentifier)

  # TakeSnapShot initites the snaphot algorithm, the process who will start the whole procedure will generate TAKESNAPSHOT event
  def onTakeSnapshot(self, eventobj: Event):
    print(f"I WILL START SNAPHOT: My id={self.componentname}:{self.componentinstancenumber}")
    self.takeSnapshot()

  def onMessageFromTop(self, eventobj: Event):
    pass

  def onMessageFromBottom(self, eventobj: Event):
    msg = eventobj.eventcontent
    hdr = msg.header
    payload = msg.payload
    ch = eventobj.fromchannel
    if ch in self.marker:
      if hdr.messagetype == SnapshotsMessageTypes.MARKER:
        print(f"{self.componentname}:{self.componentinstancenumber} The message comes from {eventobj.fromchannel}")
        self.takeSnapshot()
        self.marker[ch] = True
        print(f"I am {self.componentinstancenumber} and my markers={self.marker}")
        res = all(self.marker.values())  # Test Boolean Value of Dictionary
        if res == True:
          print(f"{self.componentinstancenumber} TERMINATED")
          self.updateTopology()
          self.terminate()

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
    self.eventhandlers[SnapshotsEventTypes.SNAPSHOT] = self.onSnapshot
    self.eventhandlers[SnapshotsEventTypes.TAKESNAPSHOT] = self.onTakeSnapshot
    # add events here
