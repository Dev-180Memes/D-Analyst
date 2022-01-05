import numpy as np
from visual import Visual
from plot_visual import process_coordinates
from analyst import get_color, get_next_color
    
class SpriteVisual(Visual):
    """Template displaying one texture in multiple positions with
    different colors."""
    
    def initialize(self, x=None, y=None, color=None, autocolor=None,
            texture=None, position=None, point_size=None, zoomable=False):
            
        if position is not None:
            position = np.array(position, dtype=np.float32)
        else:
            position, shape = process_coordinates(x=x, y=y)
            
        texsize = float(max(texture.shape[:2]))
        shape = texture.shape
        ncomponents = texture.shape[2]
        self.size = position.shape[0]
        
        if shape[0] == 1:
            self.ndim = 1
        elif shape[0] > 1:
            self.ndim = 2
        
        self.primitive_type = 'POINTS'
        
        if color is None:
            color = self.default_color
        
        if autocolor is not None:
            color = get_next_color(autocolor)
            
        
        color = get_color(color)
        
        if type(color) is list:
            if color and (type(color[0]) != tuple) and (3 <= len(color) <= 4):
                color = tuple(color)
            else:
                color = np.array(color)
        if isinstance(color, np.ndarray):
            colors_ndim = color.shape[1]
            single_color = False
        elif type(color) is tuple:
            single_color = True
            colors_ndim = len(color)
            
            
        texture_shader = """
        out_color = texture%NDIM%(tex_sampler, gl_PointCoord%POINTCOORD%) * %COLOR%;
        """
            
        
        shader_ndim = "%dD" % self.ndim
        if self.ndim == 1:
            shader_pointcoord = ".x"
        else:
            shader_pointcoord = ""
            
        if single_color:
            self.add_uniform("color", ndim=colors_ndim, data=color)   
            shader_color_name = "color"
        else:
            self.add_attribute("color", ndim=colors_ndim, data=color)
            self.add_varying("varying_color", vartype="float", ndim=colors_ndim)
            self.add_vertex_main("""
            varying_color = color;
            """)
            shader_color_name = "varying_color"
            
        if colors_ndim == 3:
            shader_color = "vec4(%s, 1.0)" % shader_color_name
        elif colors_ndim == 4:
            shader_color = shader_color_name
        
        texture_shader = texture_shader.replace('%COLOR%', shader_color)
        texture_shader = texture_shader.replace('%NDIM%', shader_ndim)
        texture_shader = texture_shader.replace('%POINTCOORD%', shader_pointcoord)
        self.add_fragment_main(texture_shader)
        
        self.add_attribute("position", vartype="float", ndim=2, data=position,
            autonormalizable=True)
        self.add_texture("tex_sampler", size=shape, ndim=self.ndim,
            ncomponents=ncomponents)
        self.add_compound("texture", fun=lambda texture: \
                         dict(tex_sampler=texture), data=texture)
        
        if point_size is None:
            point_size = texsize
        
        if isinstance(point_size, np.ndarray):
            self.add_attribute("point_size", vartype="float", ndim=1,
                data=point_size)
        else:
            self.add_uniform("point_size", vartype="float", ndim=1, data=point_size)
        
        if zoomable:
            self.add_vertex_main("""
            gl_PointSize = point_size * max(scale.x, scale.y);
            """)
        else:
            self.add_vertex_main("""
            gl_PointSize = point_size;
            """)