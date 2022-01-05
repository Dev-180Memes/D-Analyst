import numpy as np
from analyst import get_color, get_next_color
from visual import Visual

__all__ = ['process_coordinates', 'PlotVisual']

def process_coordinates(x=None, y=None, thickness=None):
    if y is None and x is not None:
        if x.ndim == 1:
            x = x.reshape((1, -1))
        nplots, nsamples = x.shape
        y = x
        x = np.tile(np.linspace(0., 1., nsamples).reshape((1, -1)), (nplots, 1))
        
    x = np.array(x, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    
    assert x.shape == y.shape
    
    if x.ndim == 1:
        x = x.reshape((1, -1))
        y = y.reshape((1, -1))
    
    position = np.empty((x.size, 2), dtype=np.float32)
    position[:, 0] = x.ravel()
    position[:, 1] = y.ravel()
    
    return position, x.shape

class PlotVisual(Visual):
    def initialize(self, x=None, y=None, color=None, point_size=1.0, position=None, 
            nprimitives=None, index=None, color_array_index=None, thickness=None, 
            options=None, autocolor=None, autonormalizable=True):

        if position is not None:
            position = np.array(position, dtype=np.float32)
            if thickness:
                shape = (2 * position.shape[0], 1)
            else:
                shape = (1, position.shape[0])
        else:
            position, shape = process_coordinates(x=x, y=y)
            if thickness:
                shape = (shape[0], 2 * shape[1])

        self.size = np.prod(shape)
        
        if not nprimitives:
            nprimitives = shape[0]
            nsamples = shape[1]
        else:
            nsamples = self.size // nprimitives
        
        if thickness and position.shape[0] >= 2:
            w = thickness
            n = self.size
            X = position
            Y = np.zeros((n, 2))
            u = np.zeros((n/2, 2))
            X2 = np.vstack((X, 2*X[-1,:]-X[-2,:]))
            u[:,0] = -np.diff(X2[:,1])
            u[:,1] = np.diff(X2[:,0])
            r = (u[:,0] ** 2 + u[:,1] ** 2) ** .5
            rm = r.mean()
            r[r == 0.] = rm
            u[:,0] /= r
            u[:,1] /= r
            Y[::2,:] = X - w * u
            Y[1::2,:] = X + w * u
            position = Y
            x = Y[:,0]
            y = Y[:,1]
            self.primitive_type = 'TRIANGLE_STRIP'

        if nsamples <= 1:
            self.bounds = [0, self.size]
        else:
            self.bounds = np.arange(0, self.size + 1, nsamples)

        if color is None:
            if nprimitives <= 1:
                color = self.default.color

        if autocolor is not None:
            if nprimitives <= 1:
                color = get_next_color(autocolor)
            else:
                color = [get_next_color(i + autocolor) for i in xrange(nprimitives)]

        color = get_color(color)

        if type(color) is list:
            if color and (type(color[0]) != tuple) and (3 <= len(color) <= 4):
                color = tuple(color)
            else:
                color = np.array(color)

        use_color_array = color_array_index is not None
        if isinstance(color, np.ndarray):
            colors_ndim = color.shape[1]
            if color.shape[0] == self.size:
                single_color = False
            else:
                use_color_array = True
                single_color = False
        elif type(color) is tuple:
            single_color = True
            colors_ndim = len(color)

        self.add_attribute("position", ndim=2, data=position, 
            autonormalizable=autonormalizable)
        
        if index is not None:
            index = np.array(index)
            self.add_index("index", data=index)
        
        if single_color and not use_color_array:
            self.add_uniform("color", ndim=colors_ndim, data=color)
            if colors_ndim == 3:
                self.add_fragment_main("""out_color = vec4(color, 1.0);""")
            elif colors_ndim == 4:
                self.add_fragment_main("""out_color = color;""")
        
        elif not use_color_array:
            self.add_attribute("color", ndim=colors_ndim, data=color)
            self.add_varying("varying_color", vartype="float", ndim=colors_ndim)
            
            self.add_vertex_main("""varying_color = color;""")

            if colors_ndim == 3:
                self.add_fragment_main("""out_color = vec4(varying_color, 1.0);""")
            elif colors_ndim == 4:
                self.add_fragment_main("""out_color = varying_color;""")

        elif use_color_array:
            if color_array_index is None:
                color_array_index = np.repeat(np.arange(nprimitives), nsamples)
            color_array_index = np.array(color_array_index)
                
            ncolors = color.shape[0]
            ncomponents = color.shape[1]
            color = color.reshape((1, ncolors, ncomponents))
            
            dx = 1. / ncolors
            offset = dx / 2.
            
            self.add_texture('colormap', ncomponents=ncomponents, ndim=1, data=color)
            self.add_attribute('index', ndim=1, vartype='int', data=color_array_index)
            self.add_varying('vindex', vartype='int', ndim=1)
            
            self.add_vertex_main("""vindex = index;""")
            
            self.add_fragment_main("""
            float coord = %.5f + vindex * %.5f;
            vec4 color = texture1D(colormap, coord);
            out_color = color;
            """ % (offset, dx))

        self.add_uniform("point_size", data=point_size)
        self.add_vertex_main("""gl_PointSize = point_size;""")