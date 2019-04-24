#!/usr/src/env python3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Category, Note

from sys import argv

engine = create_engine('sqlite:///notes.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
# session.rollback()
session = DBSession()

categories = [
        'World News',
        'Programming',
        'Reference Guides',
        'Questions',
        'Bookmarks'
    ]

notes = [
        {
            'category_name': 'Questions',
            'owner_id': 1,
            'title': 'html5: Inserting and retrieving formatted text',
            'body': '''Hey, i\'m trying to add a <textarea> on my website \
            for users to insert their notes which would get saved to a \
            database and could be retrieved with new lines and things like \
            bold and italics.&#13;&#10Is thatdoable?&#13;&#10Anysuggestions \
            or overview info will be most welcome, thankyou.'''
        },
        {
            'category_name': 'Programming',
            'owner_id': 1,
            'title': 'python3.7: New fstrings are dope',
            'body': '''I just read the article on realpython.com. Oh, the \
            quality of this life!'''
        },
        {
            'category_name': 'Reference Guides',
            'owner_id': 1,
            'title': 'Python Tutorials And Guides',
            'body': '''* http://book.pythontips.com/en/latest/index.html \
            &#13;&#10* https://realpython.com/&#13;&#10* \
            https://google.github.io/styleguide/pyguide.html&#13;&#10* \
            https://pymotw.com/3/'''
        }
    ]


def commit_categories():
    for c in categories:
        new_cat = Category(name=c)
        # print(new_cat.name)
        session.add(new_cat)
        session.commit()


def commit_notes():
    for n in notes:
        new_note = Note(
                category_name=n['category_name'],
                owner_id=n['owner_id'],
                title=n['title'],
                body=n['body']
            )
        session.add(new_note)
        session.commit()


if __name__ == '__main__':
    if argv[1] == 'test':
        print(f'\r\n{categories}')
        for n in notes:
            print(f'\r\n{n}')
        print('\r')

    if argv[1] == 'commit':
        commit_categories()
        commit_notes()

# \
# {
#     'category_name': ,
#     'owner_id': 1,
#     'title': ,
#     'body':
# }
