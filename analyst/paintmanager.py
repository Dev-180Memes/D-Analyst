import numpy as np
import OpenGL.GL as gl
from analyst import log_debug, log_info, log_warn, get_color, GLRenderer, \
    Manager, TextVisual, RectanglesVisual, SceneCreator, serialize, \
    GridVisual

__all__ = ['PaintManager']

class PaintManager(Manager):
    """Defines what to render in the widget."""

    bgcolor = (0., 0., 0., 0.)
    
    navigation_rectangle_color = (1., 1., 1., .25)
    
    def reset(self):
        """Reset the scene."""
        self.scene_creator = SceneCreator(
                    constrain_ratio=self.parent.constrain_ratio)
        self.data_updating = {}
        
    def set_rendering_options(self, **kwargs):
        """Set rendering options in the scene."""
        self.scene_creator.get_scene()['renderer_options'].update(**kwargs)

    def initialize_default(self, **kwargs):
        if self.parent.display_fps:
            self.add_visual(TextVisual, text='FPS: 000', name='fps',
                            fontsize=18,
                            coordinates=(-.80, .92),
                            visible=False,
                            is_static=True)

    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene_creator.get_visuals()
        
    def get_visual(self, name):
        return self.scene_creator.get_visual(name)
        
    def show_navigation_rectangle(self, coordinates):
        """Show the navigation rectangle with the specified coordinates 
        (in relative window coordinates)."""
        self.set_data(coordinates=coordinates, visible=True,
                      visual='navigation_rectangle')
            
    def hide_navigation_rectangle(self):
        """Hide the navigation rectangle."""
        self.set_data(visible=False, visual='navigation_rectangle')
        
        
    def reinitialize_visual(self, visual=None, **kwargs):
        """Reinitialize a visual, by calling visual.initialize() after
        initialization, just to update the data.
        
        This function retrieves the data of all variables, as specified in
        visual.initialize(), and call paint_manager.set_data with this 
        information.
        
        """
        if visual is None:
            visual = 'visual0'
        name = visual

        visual = self.scene_creator.get_visual_object(visual)
        visual.reinit()
        kwargs = visual.resolve_references(**kwargs)
        data_updating = {}
        data_updating0 = {}
        special_keywords = ['visible',
                            'size',
                            'bounds',
                            'primitive_type',
                            'constrain_ratio',
                            'constrain_navigation',
                            ]
        for kw in special_keywords:
            if kw in kwargs:
                data_updating0[kw] = kwargs.pop(kw)
        visual.initialize(**kwargs)
        visual.finalize()
        data_updating.update(visual.get_data_updating())
        data_updating.update(data_updating0)
        self.set_data(visual=name, **data_updating)

    def add_visual(self, visual_class, *args, **kwargs):
        """Add a visual. This method should be called in `self.initialize`.
        
        A visual is an instanciation of a `Visual`. A Visual
        defines a pattern for one, or a homogeneous set of plotting objects.
        Example: a text string, a set of rectangles, a set of triangles,
        a set of curves, a set of points. A set of points and rectangles
        does not define a visual since it is not an homogeneous set of
        objects. The technical reason for this distinction is that OpenGL
        allows for very fast rendering of homogeneous objects by calling
        a single rendering command (even if several objects of the same type
        need to be rendered, e.g. several rectangles). The lower the number
        of rendering calls, the better the performance.
        
        Hence, a visual is defined by a particular Visual, and by
        specification of fields in this visual (positions of the points,
        colors, text string for the example of the TextVisual, etc.). It
        also comes with a number `N` which is the number of vertices contained
        in the visual (N=4 for one rectangle, N=len(text) for a text since 
        every character is rendered independently, etc.)
        
        Several visuals can be created in the PaintManager, but performance
        decreases with the number of visuals, so that all homogeneous 
        objects to be rendered on the screen at the same time should be
        grouped into a single visual (e.g. multiple line plots).
        
        Arguments:
          * visual_class=None: the visual class, deriving from
            `Visual` (or directly from the base class `DataVisual`
            if you don't want the navigation-related functionality).
          * visible=True: whether this visual should be rendered. Useful
            for showing/hiding a transient element. When hidden, the visual
            does not go through the rendering pipeline at all.
          
        Returns:
          * visual: a dictionary containing all the information about
            the visual, and that can be used in `set_data`.
        
        """
        self.scene_creator.add_visual(visual_class, *args, **kwargs)
        
    def set_data(self, visual=None, **kwargs):
        """Specify or change the data associated to particular visual
        fields.
        
        Actual data upload on the GPU will occur during the rendering process, 
        in `paintGL`. It is just recorded here for later use.
        
        Arguments:
          * visual=None: the relevant visual. By default, the first one
            that has been created in `initialize`.
          * **kwargs: keyword arguments as `visual_field_name: value` pairs.
        
        """
        if visual is None:
            visual = 'visual0'
        if not hasattr(self, 'renderer'):
            self.data_updating[visual] = kwargs
        else:
            self.renderer.set_data(visual, **kwargs)
            if visual in self.data_updating:
                self.data_updating[visual] = {}

    def copy_texture(self, tex1, tex2, visual=None):
        if visual is None:
            visual = 'visual0'
        self.renderer.copy_texture(visual, tex1, tex2)
    
    def update_fps(self, fps):
        """Update the FPS in the corresponding text visual."""
        self.set_data(visual='fps', text="FPS: %03d" % fps, visible=True)
 
    def initializeGL(self):
        self.initialize()
        self.initialize_default()
        self.finalize()
        self.renderer = GLRenderer(self.scene_creator.get_scene())
        self.renderer.initialize()
        for visual, kwargs in self.data_updating.iteritems():
            self.set_data(visual=visual, **kwargs)
 
    def paintGL(self):
        if hasattr(self, 'renderer'):
            self.renderer.paint()
        gl.glFlush()
 
    def resizeGL(self, width, height):
        if hasattr(self, 'renderer'):
            self.renderer.resize(width, height)
        gl.glFlush()

    def updateGL(self):
        """Call updateGL in the parent widget."""
        self.parent.updateGL()
        
    def cleanup(self):
        """Cleanup all visuals."""
        if hasattr(self, 'renderer'):
            self.renderer.cleanup()

    def initialize(self):
        """Initialize the scene creation. To be overriden.

        This method can make calls to `add_visual` and `set_data` methods.
        
        """
        pass
        
    def finalize(self):
        """Finalize the scene creation. To be overriden.
        """
        pass

    def serialize(self):
        return self.scene_creator.serialize()