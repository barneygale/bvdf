import io
import struct

class Node:
    terminator = '\x08'
    child_type = None

    def __init__(self, **kwargs):
        self.data = {'children': []}
        
        if 'path' in kwargs:
            self.buff = io.BufferedReader(io.FileIO(kwargs['path'], 'r'))
        elif 'buff' in kwargs:
            self.buff = kwargs['buff']
    
    def read_header(self):
        pass
    
    def read_children(self):
        l = len(self.terminator)
        while self.buff.peek()[:l] != self.terminator:
            yield self.read_child()
        
        self.buff.read(l)
            
    def read_child(self):
        if self.child_type:
            child = self.child_type(buff = self.buff)
            child.decode()
            return child
        else:
            raise Exception("You must define child_type or overwrite read_child")
    
    def decode(self):
        self.read_header()
        for c in self.read_children():
            self.data['children'].append(c)
    
    def __getitem__(self, name):
        return self.data[name]

    def unpack(self, data_type):
        return struct.unpack(data_type, self.buff.read(struct.calcsize(data_type)))

    def unpack_string(self):
        out = ''
        while True:
            c = self.buff.read(1)
            if c == '\x00':
                return out
            out += c
    
    def dump_bytes(self, l):
        bytes = self.buff.peek()[:l]
        print ' '.join(['0x%02x' % ord(i) for i in bytes])
    
    def __repr__(self):
        out = ['%s:' % self.__class__.__name__]
        for k, v in self.data.iteritems():
            if k != 'children':
                out.append("\t%s\t%s" % (k,v))
        if self.data['children']:
            out.append("\tchildren:")
        for c in self.data['children']:
            out += ["\t\t%s" % l for l in repr(c).split('\n')]
        
        return '\n'.join(out)
                
        
class LeafNode(Node):
    pass


class DictNode(Node):
    terminator = '\x08'
    def read_child(self):
        type = self.unpack('B')[0]
        name = self.unpack_string()
        
        #Nested list node
        if type == 0:
            child = DictNode(buff = self.buff)
            child.decode()
        #String
        elif type in (1,5):
            child = LeafNode()
            child.data['value'] = self.unpack_string()
        #Int
        elif type in (2,4,6):
            child = LeafNode()
            child.data['value'] = self.unpack('<i')[0]
        #Float
        elif type == 3:
            child = LeafNode()
            child.data['value'] = self.unpack('<f')[0]
        #uint64
        elif type == 7:
            child = LeafNode()
            child.data['value'] = self.unpack('<Q')[0]
        else:
            raise Exception('Unknown DictNode element type 0x%x at offset 0x%x' % (type, self.buff.tell()))
        
        child.data['type'] = type
        child.data['name'] = name
        return child

###
### normal binary vdf files
###

class VDFFile(DictNode):
    pass

###
### packageinfo.vdf
###

class PackageNode(Node):
    child_type = DictNode
    def read_header(self):
        self.data['unknown1'] = self.unpack('<I')[0]
        self.data['unknown2'] = self.buff.read(20)
        self.data['unknown3'] = self.unpack('<H')[0]

class PackageInfoFile(Node):
    terminator = '\xFF\xFF\xFF\xFF'
    child_type = PackageNode

    def read_header(self):
        self.data['header'] = self.unpack('<II')

###
### appinfo.vdf
###

class AppParameterNode(Node):
    child_type = DictNode
    def read_header(self):
        self.data['type'] = self.unpack('<H')[0]
        self.data['key'] = self.unpack_string()
        assert self.data['type'] in (2, 3, 4, 6, 7, 10, 14)

class AppNode(Node):
    terminator = '\x00'
    child_type = AppParameterNode
    
    def read_header(self):
        self.data['id']          = self.unpack('<I')[0]
        self.data['data_len']    = self.unpack('<I')[0]
        self.data['offset']      = self.buff.tell()
        self.data['type']        = self.unpack('<I')[0]
        self.data['unknown1']    = self.unpack('<I')[0]
        self.data['last_change'] = self.unpack('<I')[0]
    
    def read_children(self):
        self.buff.seek(self.data['offset']+12, 0)
        for c in Node.read_children(self):
            yield c
    
class AppInfoFile(Node):
    terminator = '\x00\x00\x00\x00'
    full_decode = True

    def read_header(self):
        self.data['header'] = self.unpack('<II')
   
    def read_child(self):
        child = AppNode(buff = self.buff)
        if self.full_decode:
            child.decode()
        else:
            child.read_header()
            self.buff.seek(child['offset'] + child['data_len'], 0)
            
        return child

###
### This checks the magic byte to determine file type, and returns an appropriate node object
### Note that this object will still need a .decode() (or whatever)
###

def get_root(path):
    i = io.BufferedReader(io.FileIO(path, 'r'))
    h = i.peek()[:4]
    if h[2] == '\x56':
        if h[1] == '\x44':
            ty = AppInfoFile
        elif h[1] == '\x55':
            ty = PackageInfoFile
        else:
            raise Exception("Unknown file type!")
    else:
        ty = VDFFile
    
    root = ty(buff = i)
    return root
