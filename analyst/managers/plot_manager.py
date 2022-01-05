import numpy as np
from analyst.processors import NavigationEventProcessor
from default_manager import DefaultPaintManager, DefaultInteractionManager, \
    DefaultBindings
from analyst import GridEventProcessor, RectanglesVisual, GridVisual, Bindings, \
    DataNormalizer

class PlotPaintManager(DefaultPaintManager):
    def initialize_default(self):
        super(PlotPaintManager, self).initialize_default()
        self.add_visual(RectanglesVisual, coordinates=(0.,) * 4,
                        color=self.navigation_rectangle_color, 
                        is_static=True,
                        name='navigation_rectangle',
                        visible=False)
        
        if self.parent.activate_grid:
            self.add_visual(GridVisual, name='grid', visible=False)

    def finalize(self):
        if not hasattr(self, 'normalization_viewbox'):
            self.normalization_viewbox = (None,) * 4
        visuals = self.get_visuals()
        xmin, ymin, xmax, ymax = self.normalization_viewbox
        nx0 = xmin is None
        nx1 = xmax is None
        ny0 = ymin is None
        ny1 = ymax is None
        alldata = []
        for visual in visuals:
            vars = visual['variables']
            attrs = [var for var in vars if var['shader_type'] == 'attribute']
            datalist = [attr['data'] for attr in attrs if 'data' in attr and \
                isinstance(attr['data'], np.ndarray) and \
                attr['data'].size > 0 and attr['data'].ndim == 2 and \
                attr.get('autonormalizable', None)]
            alldata.extend(datalist)
            for data in datalist:
                if nx0:
                    x0 = data[:,0].min()
                    if xmin is None:
                        xmin = x0
                    else:
                        xmin = min(xmin, x0)
                        
                if nx1:
                    x1 = data[:,0].max()
                    if xmax is None:
                        xmax = x1
                    else:
                        xmax = max(xmax, x1)
                        
                if ny0:
                    y0 = data[:,1].min()
                    if ymin is None:
                        ymin = y0
                    else:
                        ymin = min(ymin, y0)
                if ny1:
                    
                    y1 = data[:,1].max()
                    if ymax is None:
                        ymax = y1
                    else:
                        ymax = max(ymax, y1)

        self.normalization_viewbox = (xmin, ymin, xmax, ymax)
        normalizer = DataNormalizer()
        normalizer.normalize(self.normalization_viewbox)
        tr_x = normalizer.normalize_x
        tr_y = normalizer.normalize_y
        for data in alldata:
            data[:,0] = tr_x(data[:,0])
            data[:,1] = tr_y(data[:,1])
            

class PlotInteractionManager(DefaultInteractionManager):
    def initialize_default(self, constrain_navigation=None,
        momentum=False,
        ):
        super(PlotInteractionManager, self).initialize_default()
        self.add_processor(NavigationEventProcessor,
            constrain_navigation=constrain_navigation,
            momentum=momentum,
            name='navigation')
        self.add_processor(GridEventProcessor, name='grid')
        
class PlotBindings(DefaultBindings):
    """A default set of bindings for interactive navigation.
    
    This binding set makes use of the keyboard and the mouse.
    
    """
    def set_grid(self):
        self.set('KeyPress', 'Grid', key='G')
    
    def set_panning_mouse(self):
        """Set panning bindings with the mouse."""
        self.set('LeftClickMove', 'Pan',
                    param_getter=lambda p: (p["mouse_position_diff"][0],
                                            p["mouse_position_diff"][1]))

    def set_panning_keyboard(self):
        """Set panning bindings with the keyboard."""
        self.set('KeyPress', 'Pan',
                    key='Left', description='Left',
                    param_getter=lambda p: (.24, 0))
        self.set('KeyPress', 'Pan',
                    key='Right', description='Right',
                    param_getter=lambda p: (-.24, 0))
        self.set('KeyPress', 'Pan',
                    key='Up', description='Up',
                    param_getter=lambda p: (0, -.24))
        self.set('KeyPress', 'Pan',
                    key='Down', description='Down',
                    param_getter=lambda p: (0, .24))
                
    def set_zooming_mouse(self):
        """Set zooming bindings with the mouse."""
        self.set('RightClickMove', 'Zoom',
                    param_getter=lambda p: (p["mouse_position_diff"][0]*2.5,
                                            p["mouse_press_position"][0],
                                            p["mouse_position_diff"][1]*2.5,
                                            p["mouse_press_position"][1]))
    
    def set_zoombox_mouse(self):
        """Set zoombox bindings with the mouse."""
        self.set('MiddleClickMove', 'ZoomBox',
                    param_getter=lambda p: (p["mouse_press_position"][0],
                                            p["mouse_press_position"][1],
                                            p["mouse_position"][0],
                                            p["mouse_position"][1]))

    def set_zoombox_keyboard(self):
        """Set zoombox bindings with the keyboard."""
        self.set('LeftClickMove', 'ZoomBox',
                    key_modifier='Control',
                    param_getter=lambda p: (p["mouse_press_position"][0],
                                            p["mouse_press_position"][1],
                                            p["mouse_position"][0],
                                            p["mouse_position"][1]))
                 
    def set_zooming_keyboard(self):
        """Set zooming bindings with the keyboard."""
        self.set('KeyPress', 'Zoom',
                    key='Left', description='X-', key_modifier='Control', 
                    param_getter=lambda p: (-.25, 0, 0, 0))
        self.set('KeyPress', 'Zoom',
                    key='Right', description='X+', key_modifier='Control', 
                    param_getter=lambda p: (.25, 0, 0, 0))
        self.set('KeyPress', 'Zoom',
                    key='Up', description='Y+', key_modifier='Control', 
                    param_getter=lambda p: (0, 0, .25, 0))
        self.set('KeyPress', 'Zoom',
                    key='Down', description='Y-', key_modifier='Control', 
                    param_getter=lambda p: (0, 0, -.25, 0))
        
    def set_zooming_wheel(self):
        """Set zooming bindings with the wheel."""
        self.set('Wheel', 'Zoom',
                    param_getter=lambda p: (
                                    p["wheel"]*.002, 
                                    p["mouse_position"][0],
                                    p["wheel"]*.002, 
                                    p["mouse_position"][1]))
        
    def set_zooming_pinch(self):
        self.set('Pinch', 'Zoom', param_getter=lambda p: 
            (
             p["pinch_scale_diff"],
             0,  
             p["pinch_scale_diff"],
             0,
             ))

    def set_reset(self):
        """Set reset bindings."""
        self.set('KeyPress', 'Reset', key='R')
        self.set('DoubleClick', 'Reset')
        
    def initialize_default(self):
        super(PlotBindings, self).initialize_default()
        """Initialize all bindings. Can be overriden."""
        self.set_base_cursor()
        self.set_grid()
        self.set_panning_mouse()
        self.set_panning_keyboard()
        self.set_zooming_mouse()
        self.set_zoombox_mouse()
        self.set_zoombox_keyboard()
        self.set_zooming_keyboard()
        self.set_zooming_wheel()
        self.set_zooming_pinch()
        self.set_reset()