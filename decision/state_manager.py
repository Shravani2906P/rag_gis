class State:
    def __init__(self):
        self.intent=None
        self.type=None
        self.area=None
        self.depth=None
        self.slope=None

    def update(self,intent=None,t=None,features=None):
        if intent:
            self.intent=intent
        if t:
            self.type=t
        if features:
            for k,v in features.items():
                if v is not None:
                    setattr(self,k,v)