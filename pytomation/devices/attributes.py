class Attributes(object):
    
    def __init__(self, *args, **kwargs):
        self.command = None
        self.mapped = None
        self.source = None
        self.time = None
        self.secs = None
        
        for k, v in kwargs.items():
            setattr(self, k, v)