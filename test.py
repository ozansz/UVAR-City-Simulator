from Ahc import GenericComponentModel
from Ahc import Event
from Ahc import ComponentRegistry
import threading


class Component( GenericComponentModel ):
    def onMessage(self, eventobj: Event):
        print( f"I am {self.componentname}: {eventobj.caller.componentname} called me at {eventobj.time}" )
        myevent = Event( self, "message", "content" )
        if self.upout:
            self.upout.trigger_event( myevent )
        if self.downout:
            self.downout.trigger_event( myevent )

    def onTimerExpired(self, eventobj: Event):
        print( f"I am {self.componentname}:event {eventobj.event} happened at {eventobj.time}" )

    handlerdict = {
        "message": onMessage,
        "timerexpired": onTimerExpired
    }

    def __init__(self, componentname, componentid):
        super().__init__( componentname, componentid, self.handlerdict )


registry = ComponentRegistry()


class CompositeComponent( GenericComponentModel ):

    def onMessage(self, eventobj: Event):
        print( f"I am {self.componentname}: {eventobj.caller.componentname} called me at {eventobj.time}" )
        myevent = Event( self, "message", "content" )
        if self.upout:
            self.upout.trigger_event( myevent )
#        if self.downout:
#            self.downout.trigger_event( myevent )

    handlerdict = {
        "message": onMessage
    }

    def __init__(self, componentname, componentid):
        self.linklayer = Component( "LinkLayer", 1 )
        registry.addComponent( self.linklayer )
        self.netlayer = Component( "NetworkLayer", 2 )
        registry.addComponent( self.netlayer )
        registry.linkComponents( self.linklayer, self.netlayer )

        super().__init__( componentname, componentid, self.handlerdict )




def Main():
    cc = CompositeComponent("CompositeNodeComponent", 1)
    myevent = Event( cc, "message", "content" )
    cc.trigger_event( myevent )

    registry.linkComponents(cc, cc.linklayer)

    print( registry.getComponentByInstance( cc.linklayer ) )
    print( registry.getComponentByInstance( cc.netlayer ) )
    print( registry.getComponentByInstance( cc ) )

    while (True): pass


if __name__ == "__main__":
    Main()
