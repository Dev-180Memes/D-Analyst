import numpy as np
from visual import Visual, RefVar
    
from analyst.tools import hsv_to_rgb

def colormap(x):
    """Colorize a 2D grayscale array.
    
    Arguments: 
      * x:an NxM array with values in [0,1] 
    
    Returns:
      * y: an NxMx3 array with a rainbow color palette.
    
    """
    x = np.clip(x, 0., 1.)
    
    col0 = np.array([.67, .91, .65]).reshape((1, 1, -1))
    col1 = np.array([0., 1., 1.]).reshape((1, 1, -1))
    
    col0 = np.tile(col0, x.shape + (1,))
    col1 = np.tile(col1, x.shape + (1,))
    
    x = np.tile(x.reshape(x.shape + (1,)), (1, 1, 3))
    
    return hsv_to_rgb(col0 + (col1 - col0) * x)

class TextureVisual(Visual):
    """Visual that displays a colored texture."""
    
    def points_compound(self, points=None):
        """Compound function for the coordinates of the texture."""
        if points is None:
            points = (-1, -1, 1, 1)
        x0, y0, x1, y1 = points
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        
        position = np.zeros((4,2))
        position[0,:] = (x0, y0)
        position[1,:] = (x1, y0)
        position[2,:] = (x0, y1)
        position[3,:] = (x1, y1)

        return dict(position=position)
        
    def texture_compound(self, texture):
        """Compound variable for the texture data."""
        return dict(tex_sampler=texture)
    
    def initialize_fragment(self):
        """Set the fragment shader code."""
        shader_pointcoord = ""
        fragment = """
        out_color = texture%dD(tex_sampler, varying_tex_coords%s);
        """ % (self.ndim, shader_pointcoord)
        self.add_fragment_main(fragment)
    
    def initialize(self, texture=None, points=None,
            mipmap=None, minfilter=None, magfilter=None):
        
        if isinstance(texture, RefVar):
            targettex = self.resolve_reference(texture)['data']
            shape, ncomponents = targettex.shape[:2], targettex.shape[2]
        elif texture is not None:
            
            if texture.ndim == 2:
                m, M = texture.min(), texture.max()
                if m < M:
                    texture = (texture - m) / (M - m)
                texture = colormap(texture)
                
            shape = texture.shape[:2]
            ncomponents = texture.shape[2]
        else:
            shape = (2, 2)
            ncomponents = 3
        if shape[0] == 1:
            ndim = 1
        elif shape[0] > 1:
            ndim = 2
        self.ndim = ndim
        
        self.size = 4
        self.texsize = shape
        self.primitive_type = 'TRIANGLE_STRIP'
        
        if points is None:
            ratio = shape[1] / float(shape[0])
            if ratio < 1:
                a = ratio
                points = (-a, -1., a, 1.)
            else:
                a = 1. / ratio
                points = (-1., -a, 1., a)
        
        if self.ndim == 1:
            tex_coords = np.array([0, 1, 0, 1])
        elif self.ndim == 2:
            tex_coords = np.zeros((4,2))
            tex_coords[0,:] = (0, 1)
            tex_coords[1,:] = (1, 1)
            tex_coords[2,:] = (0, 0)
            tex_coords[3,:] = (1, 0)
        
        self.add_attribute("position", vartype="float", ndim=2)
        self.add_compound("points", fun=self.points_compound,
            data=points)
        
        self.add_attribute("tex_coords", vartype="float", ndim=ndim,
            data=tex_coords)
        self.add_varying("varying_tex_coords", vartype="float", ndim=ndim)
        
        if texture is not None:
            self.add_texture("tex_sampler", size=shape, ndim=ndim,
                ncomponents=ncomponents,
                mipmap=mipmap,
                minfilter=minfilter,
                magfilter=magfilter,
                )
            self.add_compound("texture", fun=self.texture_compound, data=texture)

        self.add_vertex_main("""
            varying_tex_coords = tex_coords;
        """)
        
        self.initialize_fragment()