from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base


async def wrapped_models(Base: declarative_base):
    class Proposals(Base):
        __tablename__ = 'proposals'

        id = Column(Integer, primary_key=True, autoincrement=True)
        proposal_id = Column(String, unique=True)
        start_block = Column(Integer)
        end_block = Column(Integer)

    class Votes(Base):
        __tablename__ = 'votes'

        id = Column(Integer, primary_key=True, autoincrement=True)
        proposal_id = Column(String)
        voter = Column(String)
        support = Column(String)
        block_number = Column(Integer)
        votes = Column(Integer)
        reason = Column(String)
        influencing = Column(Boolean)

    return Proposals, Votes
