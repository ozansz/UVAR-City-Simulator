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
    SnapshotsEventTypes = "snapshot"


# define your own message types
class SnapshotsMessageTypes(Enum):
    MARKER = "marker"


# define your own message header structure
class SnapshotsMessageHeader(GenericMessageHeader):
    pass


# define your own message payload structure
class SnapshotsMessagePayload(GenericMessagePayload):
    pass




#CHANDY-LAMPORT SNAPSHOT ALGORITHM
"K. Mani Chandy and Leslie Lamport. 1985. Distributed snapshots: determining global states of distributed systems. ACM Trans. Comput. Syst. 3, 1 (Feb. 1985), 63–75. DOI:https://doi.org/10.1145/214451.214456"

"The Chandy-Lamport snapshot algorithm requires that channels are FIFO. Any initiator can decide to take a local snapshot of its state. It then sends a control message marker through all its outgoing channels to let its neighbors take a snapshot too. When a process that has not yet taken a snapshot receives a marker message, it takes a local snapshot of its state, and sends a marker message through all its outgoing channels. A process q computes as channel state for an incoming channel pq the (basic) messages that it receives via pq after taking its local snapshot and before receiving a marker message from p. The Chandy-Lamport algorithm terminates at a process when it has received a marker message through all its incoming channels."


#Assumption 1: Directed network
#Assumption 2: FIFO channel

class ChandyLamportSnapshot(ComponentModel):
    def onInit(self, eventobj: Event):
        pass

    def onSnapshot(self, eventobj: Event):
        pass

    def onMessageFromTop(self, eventobj: Event):
        pass

    def onMessageFromBottom(self, eventobj: Event):
        pass

    def __init__(self, componentname, componentinstancenumber):
        super().__init__(componentname, componentinstancenumber)
        self.eventhandlers[SnapshotsEventTypes.SnapshotsEventTypes] = self.onSnapshot
        # add events here
