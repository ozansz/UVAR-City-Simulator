from Ahc import GenericComponentModel, Event, ComponentRegistry, PortNames, P2PFIFOChannel, FIFOBroadcastChannel
import time, random
import threading

registry = ComponentRegistry()

class ApplicationLayerComponent( GenericComponentModel ):
    def onInit(self, eventobj: Event):
        print( f"Initializing {self.componentname}.{self.componentinstancenumber}" )
        proposedval = random.randint(0,100)
        randval = random.randint(0,1)
        if randval == 0:
            newmsg = MessageContent( proposedval, self.componentinstancenumber )
            randdelay = random.randint(0,5)
            time.sleep(randdelay)
            self.sendself(Event(self,"propose", newmsg))
        else:
            pass

    def onMessageFromBottom(self, eventobj: Event):
        print( f"{self.componentname}.{self.componentinstancenumber}: Gotton message {eventobj.content.value} from {eventobj.content.mynodeid}" )
        # value = eventobj.content.value
        # value += 1
        # newmsg = MessageContent( value )
        # myevent = Event( self, "agree", newmsg )
        # self.trigger_event(myevent)

    def onPropose(self, eventobj: Event):
        self.senddown( Event( self, "messagefromtop", eventobj.content ) )

    def onAgree(self, eventobj: Event):
        print(f"Agreed on {eventobj.content}")

    def onTimerExpired(self, eventobj: Event):
        pass

    eventhandlers = {
        "init": onInit,
        "propose": onPropose,
        "messagefrombottom": onMessageFromBottom,
        "agree": onAgree,
        "timerexpired": onTimerExpired
    }



class NetworkLayerComponent( GenericComponentModel ):
    def onInit(self, eventobj: Event):
        print( f"Initializing {self.componentname}.{self.componentinstancenumber}" )

    def onMessageFromTop(self, eventobj: Event):
        self.senddown(Event( self, "messagefromtop", eventobj.content ))

    def onMessageFromBottom(self, eventobj: Event):
        self.sendup(Event( self, "messagefrombottom", eventobj.content ))

    def onTimerExpired(self, eventobj: Event):
        pass

    eventhandlers = {
        "init": onInit,
        "messagefromtop": onMessageFromTop,
        "messagefrombottom": onMessageFromBottom,
        "timerexpired": onTimerExpired
    }



class LinkLayerComponent( GenericComponentModel ):
    def onInit(self, eventobj: Event):
        print( f"Initializing {self.componentname}.{self.componentinstancenumber}" )

    def onMessageFromTop(self, eventobj: Event):
        myevent = Event( self, "messagefromtop", eventobj.content )
        self.ports[PortNames.DOWN].trigger_event( myevent )

    def onMessageFromBottom(self, eventobj: Event):
        myevent = Event( self, "messagefrombottom", eventobj.content )
        self.ports[PortNames.UP].trigger_event( myevent )

    def onTimerExpired(self, eventobj: Event):
        pass

    eventhandlers = {
        "init": onInit,
        "messagefromtop": onMessageFromTop,
        "messagefrombottom": onMessageFromBottom,
        "timerexpired": onTimerExpired
    }



class CompositeComponent( GenericComponentModel ):

    def onInit(self, eventobj: Event):
        print( f"Initializing {self.componentname}.{self.componentinstancenumber}" )


    def onMessageFromTop(self, eventobj: Event):
        myevent = Event( self, "message", eventobj.content )
        self.ports[PortNames.DOWN].trigger_event( myevent )

    def onMessageFromChannel(self, eventobj: Event):
        myevent = Event( self, "messagefrombottom", eventobj.content )
        self.ports[PortNames.UP].trigger_event( myevent )

    eventhandlers = {
        "init": onInit,
        "messagefromtop": onMessageFromTop,
        "messagefromchannel": onMessageFromChannel
    }

    def __init__(self, componentname, componentid):
        # SUBCOMPONENTS
        self.appllayer = ApplicationLayerComponent( "ApplicationLayer", componentid )
        self.netlayer = NetworkLayerComponent( "NetworkLayer", componentid )
        self.linklayer = LinkLayerComponent( "LinkLayer", componentid )

        # CONNECTIONS AMONG SUBCOMPONENTS
        self.appllayer.connectMeToComponent( PortNames.DOWN, self.netlayer )
        self.netlayer.connectMeToComponent( PortNames.UP, self.appllayer )
        self.netlayer.connectMeToComponent( PortNames.DOWN, self.linklayer )
        self.linklayer.connectMeToComponent( PortNames.UP, self.netlayer )

        # Connect the bottom component to the composite component....
        self.linklayer.connectMeToComponent( PortNames.DOWN, self )
        self.connectMeToComponent( PortNames.UP, self.linklayer )

        super().__init__( componentname, componentid )


class MessageContent:
    def __init__(self, value, mynodeid):
        self.value = value
        self.mynodeid = mynodeid

def Main():
    nodes = []
    ch1 = FIFOBroadcastChannel( "FIFOBroadcastChannel", 1 )
    for i in range( 10 ):
        cc = CompositeComponent( "Node", i )
        nodes.append( cc )
        cc.connectMeToChannel( PortNames.DOWN, ch1 )

    # print(registry.getComponentByInstance(cc.linklayer))
    # print(registry.getComponentByInstance(cc.netlayer))
    # print(registry.getComponentByInstance(cc))

    registry.printComponents()

    while (True): pass


if __name__ == "__main__":
    Main()
