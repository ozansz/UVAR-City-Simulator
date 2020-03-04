from Ahc import GenericComponentModel, Event, ComponentRegistry, PortNames, P2PFIFOChannel
import time
import threading

registry = ComponentRegistry()

class ApplicationLayerComponent( GenericComponentModel ):
    def onMessageFromBottom(self, eventobj: Event):
        print(f"{self.componentname}.{self.componentinstancenumber}: Gotton message {eventobj.content.value}")
        value = eventobj.content.value
        value += 1
        newmsg = MessageContent( value )
        myevent = Event( self, "agree", newmsg )
        self.trigger_event(myevent)

    def onAgree(self, eventobj: Event):
        myevent = Event( self, "messagefromtop", eventobj.content )
        self.ports[PortNames.DOWN].trigger_event(myevent)

    def onTimerExpired(self, eventobj: Event):
        pass

    handlerdict = {
        "messagefrombottom": onMessageFromBottom,
        "agree": onAgree,
        "timerexpired": onTimerExpired
    }

    def __init__(self, componentname, componentid):
        super().__init__( componentname, componentid, self.handlerdict )


class NetworkLayerComponent( GenericComponentModel ):
    def onMessageFromTop(self, eventobj: Event):
        myevent = Event( self, "messagefromtop", eventobj.content )
        self.ports[PortNames.DOWN].trigger_event(myevent)

    def onMessageFromBottom(self, eventobj: Event):
        myevent = Event( self, "messagefrombottom", eventobj.content )
        self.ports[PortNames.UP].trigger_event(myevent)

    def onTimerExpired(self, eventobj: Event):
        pass

    handlerdict = {
        "messagefromtop": onMessageFromTop,
        "messagefrombottom": onMessageFromBottom,
        "timerexpired": onTimerExpired
    }

    def __init__(self, componentname, componentid):
        super().__init__( componentname, componentid, self.handlerdict )


class LinkLayerComponent( GenericComponentModel ):
    def onMessageFromTop(self, eventobj: Event):
        myevent = Event( self, "messagefromtop", eventobj.content )
        self.ports[PortNames.DOWN].trigger_event(myevent)

    def onMessageFromBottom(self, eventobj: Event):
        myevent = Event( self, "messagefrombottom", eventobj.content )
        self.ports[PortNames.UP].trigger_event(myevent)

    def onTimerExpired(self, eventobj: Event):
        pass

    handlerdict = {
        "messagefromtop": onMessageFromTop,
        "messagefrombottom": onMessageFromBottom,
        "timerexpired": onTimerExpired
    }

    def __init__(self, componentname, componentid):
        super().__init__( componentname, componentid, self.handlerdict )


class CompositeComponent( GenericComponentModel ):

    def onMessageFromTop(self, eventobj: Event):
        myevent = Event( self, "message", eventobj.content)
        self.ports[PortNames.DOWN].trigger_event( myevent )

    def onMessageFromChannel(self, eventobj: Event):
        myevent = Event( self, "messagefrombottom", eventobj.content)
        self.ports[PortNames.UP].trigger_event( myevent )


    handlerdict = {
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

        super().__init__( componentname, componentid, self.handlerdict )


class MessageContent:
    def __init__(self, value):
        self.value = value

def Main():
    cc1 = CompositeComponent( "Node", 1 )
    cc2 = CompositeComponent( "Node", 2 )
    ch1 = P2PFIFOChannel( "P2PFIFOChannel", 1 )
    cc1.connectMeToChannel( PortNames.DOWN, ch1 )
    cc2.connectMeToChannel( PortNames.DOWN, ch1 )

    # print(registry.getComponentByInstance(cc.linklayer))
    # print(registry.getComponentByInstance(cc.netlayer))
    # print(registry.getComponentByInstance(cc))

    registry.printComponents()

    time.sleep( 2 )

    msg = MessageContent(5);
    myevent = Event( cc1.appllayer, "agree", msg )
    cc1.appllayer.trigger_event( myevent )

    while (True): pass


if __name__ == "__main__":
    Main()
