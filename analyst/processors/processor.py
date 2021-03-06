import inspect
import numpy as np
from analyst import Manager, TextVisual, get_color
import analyst

__all__ = ['EventProcessor']

class EventProcessor(object):
    """Process several related events."""
    def __init__(self, interaction_manager, *args, **kwargs):
        self.interaction_manager = interaction_manager
        self.parent = interaction_manager.parent
        self.handlers = {}
        
        self.cursor = None
        
        self.activate()
        
        self.initialize(*args, **kwargs)
        
    def get_processor(self, name):
        """Return a processor in the Manager from its name."""
        return self.interaction_manager.get_processor(name)
        
    def _get_paint_manager(self):
        return self.interaction_manager.paint_manager
    paint_manager = property(_get_paint_manager)
        
    def set_data(self, *args, **kwargs):
        """PaintManager.set_data."""
        return self.parent.paint_manager.set_data(*args, **kwargs)
        
    def get_visual(self, name):
        """Get a visual in the PaintManager from its name."""
        return self.parent.paint_manager.get_visual(name)
        
    def add_visual(self, *args, **kwargs):
        """Add a new visual in the paint manager."""
        name = kwargs.get('name')
        if not self.get_visual(name):
            self.parent.paint_manager.add_visual(*args, **kwargs)
        
    def set_cursor(self, cursor):
        self.cursor = cursor
        
    def get_cursor(self):
        """Return the current cursor."""
        return self.cursor

    def activate(self, boo=True):
        """Activate or deactivate a processor."""
        self.activated = boo
    
    def deactivate(self):
        """Deactive the processor."""
        self.activated = False
    
    def register(self, event, method):
        """Register a handler for the event."""
        self.handlers[event] = method
        
    def registered(self, event):
        """Return whether the specified event has been registered by this
        processor."""
        return self.handlers.get(event, None) is not None
        
    def process(self, event, parameter):
        """Process an event by calling the registered handler if there's one.
        """
        method = self.handlers.get(event, None)
        if method:
            if (inspect.ismethod(method) and 
                (EventProcessor in inspect.getmro(method.im_class) or
                 analyst.InteractionManager in inspect.getmro(method.im_class))):
                method(parameter)
            else:
                fig = self.interaction_manager.figure
                if not hasattr(fig, 'set_data'):
                    fig.set_data = self.parent.paint_manager.set_data
                    fig.copy_texture = self.parent.paint_manager.copy_texture
                    fig.set_rendering_options = self.parent.paint_manager.set_rendering_options
                    fig.get_processor = self.interaction_manager.get_processor
                    fig.get_visual = self.paint_manager.get_visual
                    fig.process_interaction = self.parent.process_interaction
                
                fig.resizeGL = self.parent.paint_manager.resizeGL
                method(fig, parameter)

    def process_none(self):
        """Process the None event, occuring when there's no event, or when
        an event has just finished."""
        self.process(None, None)
        
    def initialize(self, *args, **kwargs):
        """Initialize the event processor by calling self.register to register
        handlers for different events."""
        pass
        
        
