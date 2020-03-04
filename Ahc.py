from abc import abstractmethod
import queue
from threading import Thread
import datetime
from enum import Enum


class PortNames( Enum ):
    DOWN = "PORTDOWN"
    UP = "PORTUP"


def singleton(cls):
    instance = [None]

    def wrapper(*args, **kwargs):
        if instance[0] is None:
            instance[0] = cls( *args, **kwargs )
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
                listOfKeys.append( item[0] )
        return listOfKeys

    def addComponent(self, component):
        key = component.componentname + str( component.componentinstancenumber )
        self.components[key] = component

    def getComponentByKey(self, componentname, componentinstancenumber):
        key = componentname + str( componentinstancenumber )
        return self.components[key]

    def printComponents(self):
        for itemkey in self.components:
            cmp = self.components[itemkey]
            print( f"I am {cmp.componentname}.{cmp.componentinstancenumber}" )
            for i in cmp.ports:
                connectedcmp = cmp.ports[i]
                print( f"\t{i} {connectedcmp.componentname}.{connectedcmp.componentinstancenumber}" )


class Event:
    def __init__(self, caller, event, content):
        self.caller = caller
        self.event = event
        self.content = content
        self.time = datetime.datetime.now()


class GenericComponentModel:

    def __init__(self, componentname, componentinstancenumber, handlerdict={}, num_worker_threads=1):
        self.inputqueue = queue.Queue()
        self.componentname = componentname
        self.componentinstancenumber = componentinstancenumber
        self.eventhandlers = {}
        try:
            if self.ports:
                pass
        except AttributeError:
            self.ports = {}

        for ev in handlerdict:
            self.eventhandlers[ev] = handlerdict[ev]

        self.registry = ComponentRegistry()
        self.registry.addComponent( self )

        for i in range( num_worker_threads ):
            t = Thread( target=self.worker )
            t.daemon = True
            t.start()

    def connectMeToComponent(self, name, component):
        try:
            self.ports[name] = component
        except AttributeError:
            self.ports = {}
            self.ports[name] = component

    def connectMeToChannel(self, name, channel):
        try:
            self.ports[name] = channel
        except AttributeError:
            self.ports = {}
            self.ports[name] = channel
        portnameforchannel = self.componentname + str( self.componentinstancenumber )
        channel.connectMeToComponent( portnameforchannel, self )

    def worker(self):
        while True:
            workitem = self.inputqueue.get()
            if workitem.event in self.eventhandlers:
                #print(
                #    f"I am {self.eventhandlers[workitem.event]}: {workitem.caller.componentname} called me at {workitem.time}" )
                self.eventhandlers[workitem.event]( self, eventobj=workitem )  # call the handler
            else:
                print( f"Event Handler: {workitem.event} is not implemented" )
            self.inputqueue.task_done()

    def trigger_event(self, eventobj: Event):
        self.inputqueue.put_nowait( eventobj )


class GenericChannel( GenericComponentModel ):
    pass


class P2PFIFOChannel( GenericChannel ):
    def onMessage(self, eventobj: Event):
        callername = eventobj.caller.componentname + str(eventobj.caller.componentinstancenumber)
        for item in self.ports:
            callee = self.ports[item]
            calleename = self.ports[item].componentname + str(self.ports[item].componentinstancenumber)
            #print(f"I am connected to {calleename}. Will check if I have to distribute it to {item}")
            if calleename == callername:
                pass
            else:
                myevent = Event( self, "messagefromchannel", eventobj.content)
                callee.trigger_event( myevent )


    handlerdict = {
        "message": onMessage
    }

    def __init__(self, componentname, componentid):
        super().__init__( componentname, componentid, self.handlerdict )

