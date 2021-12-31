class Config:
    def __init__(self):
        self.proposals = None
        self.votes = None
        self.base = None

    def get_proposals(self):
        return self.proposals

    def get_votes(self):
        return self.votes

    def set_tables(self, proposals, votes):
        self.proposals = proposals
        self.votes = votes

    def set_base(self, base):
        self.base = base


config = Config()
