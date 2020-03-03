import abc
import queue
from threading import Thread
import datetime


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
        key = component.componentname + str( component.componentinstancenumber )
        return self.components[key]

    def linkComponents(self, up, down):
        up.downout = down
        down.upout = up

class Event:
    def __init__(self, caller, event, content):
        self.caller = caller
        self.event = event
        self.content = content
        self.time = datetime.datetime.now()


class GenericComponentModel( abc.ABC ):
    eventhandlers = {}

    def __init__(self, componentname, componentinstancenumber, handlerdict={}, ports={}, num_worker_threads=1):
        self.inputqueue = queue.Queue()
        self.componentname = componentname
        self.componentinstancenumber = componentinstancenumber
        self.upout = None
        self.downout = None

        for ev in handlerdict:
            self.eventhandlers[ev] = handlerdict[ev]
        for i in range( num_worker_threads ):
            t = Thread( target=self.worker )
            t.daemon = True
            t.start()

    def worker(self):
        while True:
            workitem = self.inputqueue.get()
            if workitem.event in self.eventhandlers:
                self.eventhandlers[workitem.event]( self, eventobj=workitem )  # call the handler
            else:
                print( f"Event Handler: {workitem.event} is not implemented" )
            self.inputqueue.task_done()

    def trigger_event(self, eventobj: Event):
        self.inputqueue.put_nowait( eventobj )
