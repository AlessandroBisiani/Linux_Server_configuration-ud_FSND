from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.types import VARCHAR
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# sqlalchemy entry point
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(VARCHAR(350), nullable=False)
    name = Column(String(250), nullable=False)


class Category(Base):
    __tablename__ = 'categories'

    name = Column(String(100), primary_key=True)

    notes = relationship("Note", cascade='all, delete-orphan')

    @property
    def serialize(self):
        return {
            'name': self.name
        }


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    category_name = Column(Integer, ForeignKey('categories.name'))
    owner_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(100), nullable=False)
    body = Column(VARCHAR(10000))

    @property
    def serialize(self):
        return {
            'id':             self.id,
            'category_name':  self.category_name,
            'owner_id':       self.owner_id,
            'title':          self.title,
            'body':           self.body
        }


# create a database in notes.db and return a connection to it
engine = create_engine('sqlite:///notes.db')
# Instantiate the classes herein as tables.
Base.metadata.create_all(engine)
