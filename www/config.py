#config.py

import config_default

class Dict(dict):
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Dict' object has no attribute '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value
        
def merge(defaults, override):
    d = dict()
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                d[k] = merge(v, override[k])
            else:
                d[k] = override[k]
        else:
            d[k] = v
    return d
    
def toDict(dt):
    D = Dict()
    for k, v in dt.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D
    
try:
    import config_override
    config = config_default.config
    configs = merge(config, config_override.config)
except ImportError:
    pass
    
configs = toDict(configs)