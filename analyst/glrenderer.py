try:
    import OpenGL.GL as gl
except:
    from analyst import log_warn
    log_warn(("PyOpenGL is not available and Analyst won't be"
        " able to render plots."))
    class _gl(object):
        def mock(*args, **kwargs):
            return None
        def __getattr__(self, name):
            return self.mock
    gl = _gl()
from collections import OrderedDict
import numpy as np
import sys
from analyst import enforce_dtype, DataNormalizer, log_info, log_debug, \
    log_warn, RefVar
    
__all__ = ['GLVersion', 'GLRenderer']

class GLVersion(object):
    """Methods related to the GL Version"""
    @staticmethod
    def get_renderer_info():
        """Return information about the client renderer.
        
        Arguments:
          * info: a dictionary with the following keys:
              * renderer_name
              * opengl_version
              * glsl_version
              
        """
        return {
            'renderer_name': gl.glGetString(gl.GL_RENDERER),
            'opengl_version': gl.glGetString(gl.GL_VERSION),
            'glsl_version': gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION)
        }
    
    @staticmethod
    def version_header():
        if GLVersion.get_renderer_info()['opengl_version'][0:3] < '2.1':
            return '#version 110\n'
        else:
            return '#version 120\n'
        
    @staticmethod
    def precision_header():
        if GLVersion.get_renderer_info()['glsl_version'] >= '1.3':
            return 'precision mediump float;'
        else:
            return ''

class Attribute(object):
    """Contains OpenGL functions related to attributes."""
    @staticmethod
    def create():
        """Create a new buffer and return a `buffer` index."""
        return gl.glGenBuffers(1)
    
    @staticmethod
    def get_gltype(index=False):
        if not index:
            return gl.GL_ARRAY_BUFFER
        else:
            return gl.GL_ELEMENT_ARRAY_BUFFER
        
    @staticmethod
    def bind(buffer, location=None, index=False):
        """Bind a buffer and associate a given location."""
        gltype = Attribute.get_gltype(index)
        gl.glBindBuffer(gltype, buffer)
        if location >= 0:
            gl.glEnableVertexAttribArray(location)
        
    @staticmethod
    def set_attribute(location, ndim):
        """Specify the type of the attribute before rendering."""
        gl.glVertexAttribPointer(location, ndim, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
    
    @staticmethod
    def convert_data(data, index=False):
        """Force 32-bit floating point numbers for data."""
        if not index:
            return enforce_dtype(data, np.float32)
        else:
            return np.array(data, np.int32)
        
    
    @staticmethod
    def load(data, index=False):
        """Load data in the buffer for the first time. The buffer must
        have been bound before."""
        data = Attribute.convert_data(data, index=index)
        gltype = Attribute.get_gltype(index)
        gl.glBufferData(gltype, data, gl.GL_DYNAMIC_DRAW)
        
    @staticmethod
    def update(data, onset=0, index=False):
        """Update data in the currently bound buffer."""
        gltype = Attribute.get_gltype(index)
        data = Attribute.convert_data(data, index=index)
        if data.ndim == 1:
            ndim = 1
        elif data.ndim == 2:
            ndim = data.shape[1]
        onset *= ndim * data.itemsize
        gl.glBufferSubData(gltype, int(onset), data)
    
    @staticmethod
    def delete(*buffers):
        """Delete buffers."""
        if buffers:
            gl.glDeleteBuffers(len(buffers), buffers)
        
        
class Uniform(object):
    """Contains OpenGL functions related to uniforms."""
    float_suffix = {True: 'f', False: 'i'}
    array_suffix = {True: 'v', False: ''}

    @staticmethod
    def convert_data(data):
        if isinstance(data, np.ndarray):
            data = enforce_dtype(data, np.float32)
        if type(data) == np.float64:
            data = np.float32(data)
        if type(data) == np.int64:
            data = np.int32(data)
        if type(data) == list:
            data = map(Uniform.convert_data, data)
        if type(data) == tuple:
            data = tuple(map(Uniform.convert_data, data))
        return data
    
    @staticmethod
    def load_scalar(location, data):
        data = Uniform.convert_data(data)
        is_float = (type(data) == float) or (type(data) == np.float32)
        funname = 'glUniform1%s' % Uniform.float_suffix[is_float]
        getattr(gl, funname)(location, data)

    @staticmethod
    def load_vector(location, data):
        if len(data) > 0:
            data = Uniform.convert_data(data)
            is_float = (type(data[0]) == float) or (type(data[0]) == np.float32)
            ndim = len(data)
            funname = 'glUniform%d%s' % (ndim, Uniform.float_suffix[is_float])
            getattr(gl, funname)(location, *data)
    
    @staticmethod
    def load_array(location, data):
        data = Uniform.convert_data(data)
        is_float = (data.dtype == np.float32)
        size, ndim = data.shape
        funname = 'glUniform%d%sv' % (ndim, Uniform.float_suffix[is_float])
        getattr(gl, funname)(location, size, data)
        
    @staticmethod
    def load_matrix(location, data):
        data = Uniform.convert_data(data)
        is_float = (data.dtype == np.float32)
        n, m = data.shape
        if n == m:
            funname = 'glUniformMatrix%d%sv' % (n, Uniform.float_suffix[is_float])
        else:
            funname = 'glUniformMatrix%dx%d%sv' % (n, m, Uniform.float_suffix[is_float])
        getattr(gl, funname)(location, 1, False, data)


class Texture(object):
    """Contains OpenGL functions related to textures."""
    @staticmethod
    def create(ndim=2, mipmap=False, minfilter=None, magfilter=None):
        """Create a texture with the specifyed number of dimensions."""
        buffer = gl.glGenTextures(1)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        Texture.bind(buffer, ndim)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
        
        if mipmap:
            if hasattr(gl, 'glGenerateMipmap'):
                gl.glGenerateMipmap(textype)
            else:
                minfilter = 'NEAREST'
                magfilter = 'NEAREST'
            
        if minfilter is None:
            minfilter = 'NEAREST'
        if magfilter is None:
            magfilter = 'NEAREST'
            
        minfilter = getattr(gl, 'GL_' + minfilter)
        magfilter = getattr(gl, 'GL_' + magfilter)
            
        gl.glTexParameteri(textype, gl.GL_TEXTURE_MIN_FILTER, minfilter)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_MAG_FILTER, magfilter)
        
        return buffer
        
    @staticmethod
    def bind(buffer, ndim):
        """Bind a texture buffer."""
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        gl.glBindTexture(textype, buffer)
    
    @staticmethod
    def get_info(data):
        """Return information about texture data."""
        shape = data.shape
        if shape[0] == 1:
            ndim = 1
        elif shape[0] > 1:
            ndim = 2
        ncomponents = shape[2]
        component_type = getattr(gl, ["GL_INTENSITY8", None, "GL_RGB", "GL_RGBA"] \
                                            [ncomponents - 1])
        return ndim, ncomponents, component_type

    @staticmethod    
    def convert_data(data):
        """convert data in a array of uint8 in [0, 255]."""
        if data.dtype == np.float32 or data.dtype == np.float64:
            return np.array(255 * data, dtype=np.uint8)
        elif data.dtype == np.uint8:
            return data
        else:
            raise ValueError("The texture is in an unsupported format.")
    
    @staticmethod
    def copy(fbo, tex_src, tex_dst, width, height):

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0,
                                gl.GL_TEXTURE_2D, tex_src, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_dst)
        gl.glCopyTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, 0, 0, width, height)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    @staticmethod
    def load(data):
        """Load texture data in a bound texture buffer."""
        data = Texture.convert_data(data)
        shape = data.shape
        ndim, ncomponents, component_type = Texture.get_info(data)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        if ndim == 1:
            gl.glTexImage1D(textype, 0, component_type, shape[1], 0, component_type,
                            gl.GL_UNSIGNED_BYTE, data)
        elif ndim == 2:
            gl.glTexImage2D(textype, 0, component_type, shape[1], shape[0], 0,
                            component_type, gl.GL_UNSIGNED_BYTE, data)

    @staticmethod
    def update(data):
        """Update a texture."""
        data = Texture.convert_data(data)
        shape = data.shape
        ndim, ncomponents, component_type = Texture.get_info(data)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        if ndim == 1:
            gl.glTexSubImage1D(textype, 0, 0, shape[1],
                               component_type, gl.GL_UNSIGNED_BYTE, data)
        elif ndim == 2:
            gl.glTexSubImage2D(textype, 0, 0, 0, shape[1], shape[0],
                               component_type, gl.GL_UNSIGNED_BYTE, data)

    @staticmethod
    def delete(*buffers):
        """Delete texture buffers."""
        gl.glDeleteTextures(buffers)


class FrameBuffer(object):
    """Contains OpenGL functions related to FBO."""
    @staticmethod
    def create():
        """Create a FBO."""
        if hasattr(gl, 'glGenFramebuffers') and gl.glGenFramebuffers:
            buffer = gl.glGenFramebuffers(1)
        else:
            buffer = None
        return buffer
        
    @staticmethod
    def bind(buffer=None):
        """Bind a FBO."""
        if buffer is None:
            buffer = 0
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, buffer)
        
    @staticmethod
    def bind_texture(texture, i=0):
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER,
            getattr(gl, 'GL_COLOR_ATTACHMENT%d' % i),
            gl.GL_TEXTURE_2D, texture, 0)

    @staticmethod
    def draw_buffers(n):
        gl.glDrawBuffers([getattr(gl, 'GL_COLOR_ATTACHMENT%d' % i) for i in xrange(n)])
            
    @staticmethod
    def unbind():
        """Unbind a FBO."""
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

class ShaderManager(object):
    """Handle vertex and fragment shaders.
    
    TODO: integrate in the renderer the shader code creation module.
    
    """
    def __init__(self, vertex_shader, fragment_shader):
        """Compile shaders and create a program."""
        vertex_shader = GLVersion.version_header() + vertex_shader
        fragment_shader = GLVersion.version_header() + fragment_shader
        self.vertex_shader = vertex_shader
        self.fragment_shader = fragment_shader
        self.compile()
        self.program = self.create_program()

    def compile_shader(self, source, shader_type):
        """Compile a shader (vertex or fragment shader).
        
        Arguments:
          * source: the shader source code as a string.
          * shader_type: either gl.GL_VERTEX_SHADER or gl.GL_FRAGMENT_SHADER.
        
        """
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        
        result = gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS)
        infolog = gl.glGetShaderInfoLog(shader)
        if infolog:
            infolog = "\n" + infolog.strip()
        if not(result) and infolog:
            msg = "Compilation error for %s." % str(shader_type)
            if infolog is not None:
                msg += infolog
            msg += source
            raise RuntimeError(msg)
        else:
            log_debug("Compilation succeeded for %s.%s" % (str(shader_type), infolog))
        return shader
        
    def compile(self):
        """Compile the shaders."""
        self.vs = self.compile_shader(self.vertex_shader, gl.GL_VERTEX_SHADER)
        self.fs = self.compile_shader(self.fragment_shader, gl.GL_FRAGMENT_SHADER)
        
    def create_program(self):
        """Create shader program and attach shaders."""
        program = gl.glCreateProgram()
        gl.glAttachShader(program, self.vs)
        gl.glAttachShader(program, self.fs)
        gl.glLinkProgram(program)

        result = gl.glGetProgramiv(program, gl.GL_LINK_STATUS)
        if not(result):
            msg = "Shader program linking error:"
            info = gl.glGetProgramInfoLog(program)
            if info:
                msg += info
                raise RuntimeError(msg)
        
        self.program = program
        return program
        
    def get_attribute_location(self, name):
        """Return the location of an attribute after the shaders have compiled."""
        return gl.glGetAttribLocation(self.program, name)
  
    def get_uniform_location(self, name):
        """Return the location of a uniform after the shaders have compiled."""
        return gl.glGetUniformLocation(self.program, name)
    
    def activate_shaders(self):
        """Activate shaders for the rest of the rendering call."""
        gl.glUseProgram(self.program)

    def deactivate_shaders(self):
        """Deactivate shaders for the rest of the rendering call."""
        gl.glUseProgram(0)

    def detach_shaders(self):
        """Detach shaders from the program."""
        if gl.glIsProgram(self.program):
            gl.glDetachShader(self.program, self.vs)
            gl.glDetachShader(self.program, self.fs)
            
    def delete_shaders(self):
        """Delete the vertex and fragment shaders."""
        if gl.glIsProgram(self.program):
            gl.glDeleteShader(self.vs)
            gl.glDeleteShader(self.fs)

    def delete_program(self):
        """Delete the shader program."""
        if gl.glIsProgram(self.program):
            gl.glDeleteProgram(self.program)
        
    def cleanup(self):
        """Clean up all shaders."""
        self.detach_shaders()
        self.delete_shaders()
        self.delete_program()

MAX_VBO_SIZE = 65000

class Slicer(object):
    """Handle attribute slicing, necessary because of the size
    of buffer objects which is limited on some GPUs."""
    @staticmethod
    def _get_slices(size, maxsize=None):
        """Return a list of slices for a given dataset size.
        
        Arguments:
          * size: the size of the dataset, i.e. the number of points.
          
        Returns:
          * slices: a list of pairs `(position, slice_size)` where `position`
            is the position of this slice in the original buffer, and
            `slice_size` the slice size.
        
        """
        if maxsize is None:
            maxsize = MAX_VBO_SIZE
        if maxsize > 0:
            nslices = int(np.ceil(size / float(maxsize)))
        else:
            nslices = 0
        return [(i*maxsize, min(maxsize+1, size-i*maxsize)) for i in xrange(nslices)]

    @staticmethod
    def _slice_bounds(bounds, position, slice_size, regular=False):
        """Slice data bounds in a *single* slice according to the VBOs slicing.
        
        Arguments:
          * bounds: the bounds as specified by the user in `create_dataset`.
          * position: the position of the current slice.
          * slice_size: the size of the current slice.
        
        Returns:
          * bounds_sliced: the bounds for the current slice. It is a list an
            1D array of integer indices.
        
        """
        if bounds[0] >= position + slice_size:
            bounds_sliced = None
        elif bounds[-1] < position:
            bounds_sliced = None
        else:
            bounds_sliced = bounds
            if not regular:
                ind = (bounds_sliced>=position) & (bounds_sliced<position + slice_size)
                bounds_sliced = bounds_sliced[ind]
            else:
                d = float(regular)
                p = position
                b0 = bounds_sliced[0]
                b1 = bounds_sliced[-1]
                s = slice_size
                i0 = max(0, int(np.ceil((p-b0)/d)))
                i1 = max(0, int(np.floor((p+s-b0)/d)))
                bounds_sliced = bounds_sliced[i0:i1+1].copy()
                ind = ((b0 >= p) and (b0 < p+s), (b1 >= p) and (b1 < p+s))
            bounds_sliced -= position
            if not ind[0]:
                bounds_sliced = np.hstack((0, bounds_sliced))
            if not ind[-1]:
                bounds_sliced = np.hstack((bounds_sliced, slice_size))
        return enforce_dtype(bounds_sliced, np.int32)
    
    def set_size(self, size, doslice=True):
        """Update the total size of the buffer, and update the slice information accordingly."""
        if not doslice:
            maxsize = 2 * size
        else:
            maxsize = None
        self.size = size
        self.slices = self._get_slices(self.size, maxsize)
        self.slice_count = len(self.slices)

    def set_bounds(self, bounds=None):
        """Update the bound size, and update the slice information
        accordingly."""
        if bounds is None:
            bounds = np.array([0, self.size], dtype=np.int32)
        self.bounds = bounds
        
        d = np.diff(bounds)
        r = False
        if len(d) > 0:
            dm, dM = d.min(), d.max()
            if dm == dM:
                r = dm
        
        self.subdata_bounds = [self._slice_bounds(self.bounds, pos, size, r) \
            for pos, size in self.slices]
       
       
class SlicedAttribute(object):
    """Encapsulate methods for slicing an attribute and handling several buffer objects for a single attribute."""
    def __init__(self, slicer, location, buffers=None):
        self.slicer = slicer
        self.location = location
        if buffers is None:
            self.create()
        else:
            log_debug("Creating sliced attribute with existing buffers " +
                str(buffers))
            self.load_buffers(buffers)
        
    def create(self):
        """Create the sliced buffers."""
        self.buffers = [Attribute.create() for _ in self.slicer.slices]
    
    def load_buffers(self, buffers):
        """Load existing buffers instead of creating new ones."""
        self.buffers = buffers
    
    def delete_buffers(self):
        """Delete all sub-buffers."""
        Attribute.delete(*self.buffers)

    def load(self, data):
        """Load data on all sliced buffers."""
        for buffer, (pos, size) in zip(self.buffers, self.slicer.slices):
            Attribute.bind(buffer, None)
            Attribute.load(data[pos:pos + size,...])

    def bind(self, slice=None):
        if slice is None:
            slice = 0
        Attribute.bind(self.buffers[slice], self.location)
        
    def update(self, data, mask=None):
        """Update data on all sliced buffers."""
        if mask is None:
            mask = np.ones(self.slicer.size, dtype=np.bool)
        within = False
        for buffer, (pos, size) in zip(self.buffers, self.slicer.slices):
            subdata = data[pos:pos + size,...]
            submask = mask[pos:pos + size]
            if submask.any():
                subonset = submask.argmax()
                suboffset = len(submask) - 1 - submask[::-1].argmax()
                Attribute.bind(buffer, self.location)
                Attribute.update(subdata[subonset:suboffset + 1,...], subonset)

class Painter(object):
    """Provides low-level methods for calling OpenGL rendering commands."""
    
    @staticmethod
    def draw_arrays(primtype, offset, size):
        """Render an array of primitives."""
        gl.glDrawArrays(primtype, offset, size)
        
    @staticmethod
    def draw_multi_arrays(primtype, bounds):
        """Render several arrays of primitives."""
        first = bounds[:-1]
        count = np.diff(bounds)
        primcount = len(bounds) - 1
        gl.glMultiDrawArrays(primtype, first, count, primcount)
        
    @staticmethod
    def draw_indexed_arrays(primtype, size):
        gl.glDrawElements(primtype, size, gl.GL_UNSIGNED_INT, None)

class GLVisualRenderer(object):
    """Handle rendering of one visual"""
    
    def __init__(self, renderer, visual):
        """Initialize the visual renderer, create the slicer, initialize
        all variables and the shaders."""
        self.renderer = renderer
        self.scene = renderer.scene
        self.visual = visual
        self.framebuffer = visual.get('framebuffer', None)
        self.options = visual.get('options', {})
        self.data_updating = {}
        self.textures_to_copy = []
        self.set_primitive_type(self.visual['primitive_type'])
        self.use_index = None
        self.use_slice = True
        self.slicer = Slicer()
        self.noslicer = Slicer()
        size = self.visual['size']
        bounds = np.array(self.visual.get('bounds', [0, size]), np.int32)
        self.slicer.set_size(size)
        self.slicer.set_bounds(bounds)
        self.noslicer.set_size(size, doslice=False)
        self.noslicer.set_bounds(bounds)
        self.shader_manager = ShaderManager(self.visual['vertex_shader'],
                                            self.visual['fragment_shader'])
        self.initialize_variables()
        self.initialize_fbocopy()
        self.load_variables()

    def set_primitive_type(self, primtype):
        """Set the primitive type from its name (without the GL_ prefix)."""
        self.primitive_type = getattr(gl, "GL_%s" % primtype.upper())
    
    def getarg(self, name):
        """Get a visual parameter."""
        return self.visual.get(name, None)
    
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene['visuals']
        
    def get_visual(self, name):
        """Return a visual dictionary from its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            return None
        return visuals[0]
        
    def get_variables(self, shader_type=None):
        """Return all variables defined in the visual."""
        if not shader_type:
            return self.visual.get('variables', [])
        else:
            return [var for var in self.get_variables() \
                            if var['shader_type'] == shader_type]
        
    def get_variable(self, name, visual=None):
        """Return a variable by its name, and for any given visual which 
        is specified by its name."""
        if visual is None:
            variables = self.get_variables()
        else:
            variables = self.get_visual(visual)['variables']
        variables = [v for v in variables if v.get('name', '') == name]
        if not variables:
            return None
        return variables[0]
        
    def resolve_reference(self, refvar):
        """Resolve a reference variable: return its true value (a Numpy array).
        """
        return self.get_variable(refvar.variable, visual=refvar.visual)

    def initialize_fbocopy(self):
        """Create a FBO used when copying textures."""
        self.fbocopy = FrameBuffer.create()
    
    def initialize_variables(self):
        """Initialize all variables, after the shaders have compiled."""
        if self.get_variables('index'):
            self.slicer = self.noslicer
            log_debug("deactivating slicing because there's an indexed buffer")
            self.use_index = True
        else:
            self.use_index = False
        for var in self.get_variables():
            shader_type = var['shader_type']
            if shader_type == 'varying':
                continue
            name = var['name']
            getattr(self, 'initialize_%s' % shader_type)(name)
        uniforms = self.get_variables('uniform')
        self.set_data(**dict([(v['name'], v.get('data', None)) for v in uniforms]))

    def initialize_attribute(self, name):
        """Initialize an attribute: get the shader location, create the
        sliced buffers, and load the data."""
        location = self.shader_manager.get_attribute_location(name)
        variable = self.get_variable(name)
        variable['location'] = location
        if isinstance(variable.get('data', None), RefVar):
            
            if self.renderer.visual_renderers[variable['data'].visual].use_index:
                log_debug("deactivating slicing")
                self.slicer = self.noslicer
            
            target = self.resolve_reference(variable['data'])
            variable['sliced_attribute'] = SlicedAttribute(self.slicer, location,
                buffers=target['sliced_attribute'].buffers)
        else:
            variable['sliced_attribute'] = SlicedAttribute(self.slicer, location)
        
    def initialize_index(self, name):
        variable = self.get_variable(name)
        variable['buffer'] = Attribute.create()
        
    def initialize_texture(self, name):
        variable = self.get_variable(name)
        if isinstance(variable.get('data', None), RefVar):
            target = self.resolve_reference(variable['data'])
            variable['buffer'] = target['buffer']
            variable['location'] = target['location']
        else:
            variable['buffer'] = Texture.create(variable['ndim'],
                mipmap=variable.get('mipmap', None),
                minfilter=variable.get('minfilter', None),
                magfilter=variable.get('magfilter', None),
                )
            location = self.shader_manager.get_uniform_location(name)
            variable['location'] = location
    
    def initialize_framebuffer(self, name):
        variable = self.get_variable(name)
        variable['buffer'] = FrameBuffer.create()
        
        FrameBuffer.bind(variable['buffer'])
        
        if isinstance(variable['texture'], basestring):
            variable['texture'] = [variable['texture']]
        
        FrameBuffer.draw_buffers(len(variable['texture']))
            
        for i, texname in enumerate(variable['texture']):
            texture = self.get_variable(texname)
            FrameBuffer.bind_texture(texture['buffer'], i)
        
        FrameBuffer.unbind()

    def initialize_uniform(self, name):
        """Initialize an uniform: get the location after the shaders have
        been compiled."""
        location = self.shader_manager.get_uniform_location(name)
        variable = self.get_variable(name)
        variable['location'] = location
    
    def initialize_compound(self, name):
        pass

    def load_variables(self):
        """Load data for all variables at initialization."""
        for var in self.get_variables():
            shader_type = var['shader_type']
            if shader_type == 'uniform' or shader_type == 'varying' or shader_type == 'framebuffer':
                continue
            getattr(self, 'load_%s' % shader_type)(var['name'])
        
    def load_attribute(self, name, data=None):
        """Load data for an attribute variable."""
        variable = self.get_variable(name)
        if variable['sliced_attribute'].location < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        olddata = variable.get('data', None)
        if isinstance(olddata, RefVar):
            log_debug("Skipping loading data for attribute '%s' since it "
                "references a target variable." % name)
            return
        if data is None:
            data = olddata
        if data is not None:
            variable['sliced_attribute'].load(data)
        
    def load_index(self, name, data=None):
        """Load data for an index variable."""
        variable = self.get_variable(name)
        if data is None:
            data = variable.get('data', None)
        if data is not None:
            self.indexsize = len(data)
            Attribute.bind(variable['buffer'], index=True)
            Attribute.load(data, index=True)
        
    def load_texture(self, name, data=None):
        """Load data for a texture variable."""
        variable = self.get_variable(name)
        
        if variable['buffer'] < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        if data is None:
            data = variable.get('data', None)

        self.update_samplers = True
        
        if isinstance(data, RefVar):
            log_debug("Skipping loading data for texture '%s' since it "
                "references a target variable." % name)
            return
            
        if data is not None:
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.load(data)
            
    def load_uniform(self, name, data=None):
        """Load data for an uniform variable."""
        variable = self.get_variable(name)
        location = variable['location']
        
        if location < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        if data is None:
            data = variable.get('data', None)
        if data is not None:
            ndim = variable['ndim']
            size = variable.get('size', None)
            if not size:
                if type(ndim) == int or type(ndim) == long:
                    if ndim == 1:
                        Uniform.load_scalar(location, data)
                    else:
                        Uniform.load_vector(location, data)
                elif type(ndim) == tuple:
                    Uniform.load_matrix(location, data)
            else:
                if type(ndim) == int or type(ndim) == long:
                    Uniform.load_array(location, data)
            
    def load_compound(self, name, data=None):
        pass

    def update_variable(self, name, data, **kwargs):
        """Update data of a variable."""
        variable = self.get_variable(name)
        if variable is None:
            log_debug("Variable '%s' was not found, unable to update it." % name)
        else:
            shader_type = variable['shader_type']
            if shader_type == 'compound' or shader_type == 'varying' or shader_type == 'framebuffer':
                pass
            else:
                getattr(self, 'update_%s' % shader_type)(name, data, **kwargs)
    
    def update_attribute(self, name, data):
        """Update data for an attribute variable."""
        variable = self.get_variable(name)
        
        if variable['sliced_attribute'].location < 0:
            log_debug(("Variable '%s' could not be updated, probably because "
                      "it is not used in the shaders") % name)
            return
        
        olddata = variable.get('data', None)
        if isinstance(olddata, RefVar):
            raise ValueError("Unable to load data for a reference " +
                "attribute. Use the target variable directly.""")
        variable['data'] = data
        att = variable['sliced_attribute']
        
        if olddata is None:
            oldshape = 0
        else:
            oldshape = olddata.shape

        if data.shape[0] != oldshape[0]:
            log_debug(("Creating new buffers for variable %s, old size=%s,"
                "new size=%d") % (name, oldshape[0], data.shape[0]))
            if self.use_index:
                newsize = self.slicer.size
            else:
                newsize = data.shape[0]
            self.slicer.set_size(newsize, doslice=not(self.use_index))
            
            if len(self.slicer.bounds) == 2:
                self.slicer.set_bounds()
            
            att.delete_buffers()
            att.create()
            att.load(data)           
        else:
            att.update(data)
        
    def update_index(self, name, data):
        """Update data for a index variable."""
        variable = self.get_variable(name)
        prevsize = len(variable['data'])
        variable['data'] = data
        newsize = len(data)
        if newsize != prevsize:
            self.indexsize = newsize
            Attribute.delete(variable['buffer'])
            variable['buffer'] = Attribute.create()
            Attribute.bind(variable['buffer'], variable['ndim'], index=True)
            Attribute.load(data, index=True)
        else:
            Attribute.bind(variable['buffer'], variable['ndim'], index=True)
            Attribute.update(data, index=True)
        
    def update_texture(self, name, data):
        """Update data for a texture variable."""
        variable = self.get_variable(name)
        
        if variable['buffer'] < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        prevshape = variable['data'].shape
        variable['data'] = data
        if data.shape != prevshape:
            variable['ndim'], variable['ncomponents'], _ = Texture.get_info(data)
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.load(data)
        else:
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.update(data)
        
    def update_uniform(self, name, data):
        """Update data for an uniform variable."""
        variable = self.get_variable(name)
        variable['data'] = data
        self.load_uniform(name, data)
        
    special_keywords = ['visible',
                        'size',
                        'bounds',
                        'primitive_type',
                        'constrain_ratio',
                        'constrain_navigation',
                        ]

    def set_data(self, **kwargs):
        """Load data for the specified visual. Uploading does not happen here
        but in `update_all_variables` instead, since this needs to happen
        after shader program binding in the paint method.
        
        Arguments:
          * **kwargs: the data to update as name:value pairs. name can be
            any field of the visual, plus one of the following keywords:
              * visible: whether this visual should be visible,
              * size: the size of the visual,
              * primitive_type: the GL primitive type,
              * constrain_ratio: whether to constrain the ratio of the visual,
              * constrain_navigation: whether to constrain the navigation,
        
        """
        kwargs2 = kwargs.copy()
        for name, data in kwargs2.iteritems():
            variable = self.get_variable(name)
            if variable is None:
                continue
            if variable is not None and variable['shader_type'] == 'compound':
                fun = variable['fun']
                kwargs.pop(name)
                kwargs.update(**fun(data))

            if not variable.get('visible', True):
                kwargs.pop(name)

        visible = kwargs.pop('visible', None)
        if visible is not None:
            self.visual['visible'] = visible
        
        size = kwargs.pop('size', None)
        if size is not None:
            self.slicer.set_size(size)
        
        bounds = kwargs.pop('bounds', None)
        if bounds is not None:
            self.slicer.set_bounds(bounds)

        primitive_type = kwargs.pop('primitive_type', None)
        if primitive_type is not None:
            self.visual['primitive_type'] = primitive_type
            self.set_primitive_type(primitive_type)
        
        constrain_ratio = kwargs.pop('constrain_ratio', None)
        if constrain_ratio is not None:
            self.visual['constrain_ratio'] = constrain_ratio
        
        constrain_navigation = kwargs.pop('constrain_navigation', None)
        if constrain_navigation is not None:
            self.visual['constrain_navigation'] = constrain_navigation
        
        self.data_updating.update(**kwargs)

    def copy_texture(self, tex1, tex2):
        self.textures_to_copy.append((tex1, tex2))
        
    def update_all_variables(self):
        """Upload all new data that needs to be updated."""
        for name, data in self.data_updating.iteritems():
            if data is not None:
                self.update_variable(name, data)
            else:
                log_debug("Data for variable '%s' is None" % name)
        self.data_updating.clear()
        
    def copy_all_textures(self):
        for tex1, tex2 in self.textures_to_copy:
            tex1 = self.resolve_reference(tex1)
            tex2 = self.get_variable(tex2)
            Texture.copy(self.fbocopy, tex1['buffer'], tex2['buffer'],
                tex1['shape'][0], tex1['shape'][1])
        self.textures_to_copy = []

    def bind_attributes(self, slice=None):
        """Bind all attributes of the visual for the given slice.
        This method is used during rendering."""
        attributes = self.get_variables('attribute')
        for variable in attributes:
            loc = variable['location']
            if loc < 0:
                log_debug(("Unable to bind attribute '%s', probably because "
                "it is not used in the shaders.") % variable['name'])
                continue
            variable['sliced_attribute'].bind(slice)
            Attribute.set_attribute(loc, variable['ndim'])
            
    def bind_indices(self):
        indices = self.get_variables('index')
        for variable in indices:
            Attribute.bind(variable['buffer'], index=True)
            
    def bind_textures(self):
        """Bind all textures of the visual.
        This method is used during rendering."""
        
        textures = self.get_variables('texture')
        for i, variable in enumerate(textures):
            buffer = variable.get('buffer', None)
            if buffer is not None:
                if self.update_samplers and not isinstance(variable['data'], RefVar):
                    Uniform.load_scalar(variable['location'], i)
                
                gl.glActiveTexture(getattr(gl, 'GL_TEXTURE%d' % i))
                
                Texture.bind(buffer, variable['ndim'])
            else:
                log_debug("Texture '%s' was not properly initialized." % \
                         variable['name'])
        if not textures:
            Texture.bind(0, 1)
            Texture.bind(0, 2)
        self.update_samplers = False

    def paint(self):
        """Paint the visual slice by slice."""
        if not self.visual.get('visible', True):
            return
            
        try:
            self.shader_manager.activate_shaders()
        except Exception as e:
            log_info("Error while activating the shaders: " + str(e))
            return
            
        self.update_all_variables()
        self.bind_textures()
        if self.use_index:
            self.bind_attributes()
            self.bind_indices()
            Painter.draw_indexed_arrays(self.primitive_type, self.indexsize)
        elif self.use_slice:
            for slice in xrange(len(self.slicer.slices)):
                slice_bounds = self.slicer.subdata_bounds[slice]
                self.bind_attributes(slice)
                if len(slice_bounds) <= 2:
                    Painter.draw_arrays(self.primitive_type, slice_bounds[0], 
                        slice_bounds[1] -  slice_bounds[0])
                else:
                    Painter.draw_multi_arrays(self.primitive_type, slice_bounds)
            
        self.copy_all_textures()
        
        self.shader_manager.deactivate_shaders()

    def cleanup_attribute(self, name):
        """Cleanup a sliced attribute (all sub-buffers)."""
        variable = self.get_variable(name)
        variable['sliced_attribute'].delete_buffers()
    
    def cleanup_texture(self, name):
        """Cleanup a texture."""
        variable = self.get_variable(name)
        Texture.delete(variable['buffer'])
        
    def cleanup(self):
        """Clean up all variables."""
        log_debug("Cleaning up all variables.")
        for variable in self.get_variables():
            shader_type = variable['shader_type']
            if shader_type in ('attribute', 'texture'):
                getattr(self, 'cleanup_%s' % shader_type)(variable['name'])
        self.shader_manager.cleanup()

class GLRenderer(object):
    """OpenGL renderer for a Scene.
    
    This class takes a Scene object (dictionary) as an input, and
    renders the scene. It provides methods to update the data in real-time.
    
    """
    def __init__(self, scene):
        """Initialize the renderer using the information on the scene.
        
        Arguments:
          * scene: a Scene dictionary with a `visuals` field containing
            the list of visuals.
        
        """
        self.scene = scene
        self.viewport = (1., 1.)
        self.visual_renderers = {}
    
    def set_renderer_options(self):
        """Set the OpenGL options."""
        options = self.scene.get('renderer_options', {})

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        if options.get('antialiasing', None):
            gl.glEnable(gl.GL_MULTISAMPLE)
            
        if options.get('sprites', True):
            gl.glEnable(gl.GL_VERTEX_PROGRAM_POINT_SIZE)
            gl.glEnable(gl.GL_POINT_SPRITE)
        
        if options.get('transparency', True):
            gl.glEnable(gl.GL_BLEND)
            blendfunc = options.get('transparency_blendfunc',
                ('SRC_ALPHA', 'ONE_MINUS_SRC_ALPHA')
                )
            blendfunc = [getattr(gl, 'GL_' + x) for x in blendfunc]
            gl.glBlendFunc(*blendfunc)
            
        if options.get('activate3D', None):
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE)
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glDepthRange(0.0, 1.0)
            gl.glClearDepth(1.0)
    
        background = options.get('background', (0, 0, 0, 0))
        gl.glClearColor(*background)

    def get_renderer_option(self, name):
        return self.scene.get('renderer_options', {}).get(name, None)
        
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene.get('visuals', [])
        
    def get_visual(self, name):
        """Return a visual by its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            raise ValueError("The visual %s has not been found" % name)
        return visuals[0]
        
    def set_data(self, name, **kwargs):
        """Load data for the specified visual. Uploading does not happen here
        but in `update_all_variables` instead, since this needs to happen
        after shader program binding in the paint method.
        
        Arguments:
          * visual: the name of the visual as a string, or a visual dict.
          * **kwargs: the data to update as name:value pairs. name can be
            any field of the visual, plus one of the following keywords:
              * size: the size of the visual,
              * primitive_type: the GL primitive type,
              * constrain_ratio: whether to constrain the ratio of the visual,
              * constrain_navigation: whether to constrain the navigation,
        
        """
        if name in self.visual_renderers:
            self.visual_renderers[name].set_data(**kwargs)

    def copy_texture(self, name, tex1, tex2):
        self.visual_renderers[name].copy_texture(tex1, tex2)
    
    def initialize(self):
        """Initialize the renderer."""
        for key, value in GLVersion.get_renderer_info().iteritems():
            if key is not None and value is not None:
                log_debug(key + ": " + value)
        self.set_renderer_options()
        self.visual_renderers = OrderedDict()
        for visual in self.get_visuals():
            name = visual['name']
            self.visual_renderers[name] = GLVisualRenderer(self, visual)
            
        self.fbos = []
        for name, vr in self.visual_renderers.iteritems():
            fbos = vr.get_variables('framebuffer')
            if fbos:
                self.fbos.extend([fbo['buffer'] for fbo in fbos])
            
    def clear(self):
        """Clear the scene."""
        if self.scene.get('renderer_options', {}).get('activate3D', None):
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        else:
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    def paint(self):
        """Paint the scene."""
        
        if not self.fbos:
            self.clear()
            for name, visual_renderer in self.visual_renderers.iteritems():
                visual_renderer.paint()
        
        else:
            for fbo in self.fbos:
                FrameBuffer.bind(fbo)
                
                ifbo = self.fbos.index(fbo)
                
                self.clear()
                
                for name, visual_renderer in self.visual_renderers.iteritems():
                    if visual_renderer.framebuffer == ifbo:
                        visual_renderer.paint()
    
            FrameBuffer.unbind()
    
            self.clear()
            for name, visual_renderer in self.visual_renderers.iteritems():
                if visual_renderer.framebuffer == 'screen':
                    visual_renderer.paint()

    def resize(self, width, height):
        """Resize the canvas and make appropriate changes to the scene."""
        gl.glViewport(0, 0, width, height)
        x = y = 1.0
        if self.get_renderer_option('constrain_ratio'):
            if height > 0:
                aw = float(width) / height
                ar = self.get_renderer_option('constrain_ratio')
                if ar is True:
                    ar = 1.
                if ar < aw:
                    x, y = aw / ar, 1.
                else:
                    x, y = 1., ar / aw
        self.viewport = x, y
        width = float(width)
        height = float(height)
        for visual in self.get_visuals():
            self.set_data(visual['name'],
                          viewport=self.viewport,
                          window_size=(width, height))
    
    def cleanup(self):
        """Clean up all allocated OpenGL objects."""
        for name, renderer in self.visual_renderers.iteritems():
            renderer.cleanup()