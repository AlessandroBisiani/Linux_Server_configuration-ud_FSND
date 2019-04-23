#!/usr/bin/env python3
from flask import (
        Flask,
        render_template,
        request,
        flash,
        redirect,
        url_for,
        jsonify,
        make_response,
        session as login_session
    )

import httplib2
import random
import string
import json

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
# from sqlalchemy.exc import DBAPIError

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from database_setup import Base, Note, Category, User
import requests

from os import getenv
from dotenv import load_dotenv
from pathlib import Path

environment_path = Path('.') / '.env'
load_dotenv(dotenv_path=environment_path)

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

google_client_key = getenv('GOOGLE_CLIENT_ID')
app_secret = getenv('APP_SECRET')

# with open('keys.txt', 'r') as f:
#     keys = f.read()
#     for k in keys.split(' '):
#         if k.startswith('client_id'):
#             google_client_key = k.split('=')[-1]
#         elif k.startswith('app_secret'):
#             app_secret = k.split('=')[-1]


''' Create the engine, which is the connection source, then using same
Base (the same orm heirarchy!) as databse_setup, tie the connection supplier
to the base.'''
engine = create_engine('sqlite:///notes.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


@app.route('/login')
def show_login():
    '''Set the session state and render the login page

    Returns:
        Response object -- with login.html
    '''

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    # print(f'app state: {state}')
    login_session['state'] = state
    # print(f'login session state is: {login_session["state"]}')

    try:
        session = DBSession()
        categories = session.query(Category).all()
        session.close()
    except Exception as e:
        session.close()
        log_error(e)
    else:
        return render_template('login.html',
                               categories=categories,
                               STATE=state,
                               client_id=google_client_key)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = f'''https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=\
{access_token}'''
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print('Token\'s client ID does not match app\'s.')
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                 'Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['name'] = data['name']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    if get_user_id(login_session['email']):
        login_session['id'] = get_user_id(login_session['email'])
    else:
        create_user(login_session)
        login_session['id'] = get_user_id(login_session['email'])

    assert login_session['id'], 'id not added to session.'

    output = login_session['name']
    name = login_session['name']
    flash(f'Hi, {name} you are now logged in.')
    print('done!')
    return output


# DISCONNECT - Revoke a current user's token and reset the login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = f'https://accounts.google.com/o/oauth2/revoke?token={access_token}'
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['name']
        del login_session['email']
        del login_session['id']

    # response = make_response(json.dumps('Successfully disconnected.'), 200)
    # response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('show_categories'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


def create_user(login_session):
    session = DBSession()
    newUser = User(name=login_session['name'], email=login_session[
                   'email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    session.close()
    return user.id


def get_user_info(user_id):
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    session.close()
    return user


def get_user_id(email):
    try:
        session = DBSession()
        user = session.query(User).filter_by(email=email).one()
        session.close()
        return user.id
    except Exception as e:
        session.close()
        log_error(e)


@app.route('/notesbycategory/JSON')
def notes_by_category_json():
    '''
    Return all notes data divided by category, as JSON

    Returns:
        JSON -- All notes data saved in the database
    '''
    try:
        session = DBSession()
        catalog = {}
        # Nested dict builder Get 'note' data, assign it to catalo under
        # 'category'
        for category in session.query(Category).all():
            catalog[category.name] = []
            notes = session.query(
                    Note).filter_by(category_name=category.name).all()
            for note in notes:
                # print(type(note.serialize))
                catalog[category.name].append(note.serialize)

        return jsonify(catalog)
    except Exception as e:
        log_error(e)
        # return redirect(url_for('page_not_found'))
        raise
    finally:
        session.close()
    return redirect(url_for('page_not_found'))


@app.route('/note/<int:note_id>/JSON')
def show_note_json(note_id):
    try:
        session = DBSession()
        note = session.query(Note).filter_by(id=note_id).one()
        if note:
            return jsonify(note.serialize)
    except Exception as e:
        log_error(e)
        raise
        redirect(url_for('show_categories'))
    finally:
        session.close()

    return redirect(url_for('page_not_found'))


@app.route('/notes/JSON')
def show_notes_json():
    '''Return all notes in JSON format

    Returns:
        JSON -- note
                id,
                category_name,
                owner_id,
                title,
                body
    '''
    try:
        session = DBSession()
        notes = session.query(Note).all()
        return jsonify(notes=[note.serialize for note in notes])
    except Exception as e:
        log_error(e)
        # return redirect(url_for('page_not_found'))
        raise


@app.route('/categories/JSON')
def show_categores_json():
    '''Return all categories, in JSON format

    Returns:
        JSON -- category names
    '''
    try:
        session = DBSession()
        categories = session.query(Category).all()
        return jsonify(categories=[cat.serialize for cat in categories])
    except Exception as e:
        log_error(e)
        # return redirect(url_for('page_not_found'))
        raise


@app.route('/')
def show_categories():
    user_name = 'Guest'
    session = DBSession()
    try:
        categories = session.query(Category).all()
        all_notes = session.query(Note).all()

        user = verify_login(session)
        if user:
            user_name = user.name
        session.close()

    except Exception as e:
        session.close()
        log_error(e)
        raise
    else:
        '''
        Choose at most 10 notes at random before passing them to the
        index page
        '''
        if len(all_notes) >= 10:
            random_notes = random.sample(all_notes, 10)
        else:
            random_notes = random.sample(all_notes, len(all_notes))

        display_notes = random_notes
        return render_template('index.html',
                               categories=categories,
                               notes=display_notes,
                               user_name=user_name)

    return render_template('pageNotFound.html')


@app.route('/categories/<string:category_name>')
def show_notes(category_name):
    '''Render notes display template for a category

    Arguments:
        category_name {str} -- category specified in the url

    Returns:
        Response Object -- categoryNotesView.html
    '''

    user_name = 'Guest'
    session = DBSession()
    try:
        category_notes = session.query(Note).filter_by(
                category_name=category_name).all()
        categories = session.query(Category).all()

        user = verify_login(session)
        if user:
            user_name = user.name

    except Exception as e:
        session.close()
        log_error(e)
    else:
        return render_template('categoryNotesView.html',
                               notes=category_notes,
                               categories=categories,
                               category_name=category_name,
                               user_name=user_name)
    finally:
        session.close()
    return redirect(url_for('page_not_found'))


@app.route('/categories/<string:category_name>/notes/<int:id>')
def show_note(category_name, id):
    '''Render template for the single-note view page

    Arguments:
        category_name {str} -- category name from the url
        id {int} -- note id from the url

    Returns:
        Response object -- noteView.html
    '''

    try:
        session = DBSession()
        user = verify_login(session)
        categories = session.query(Category).all()
        note = session.query(Note).filter_by(id=id).one()
        user_name = 'Guest'
        if user:
            user_name = user.name
        return render_template('noteView.html',
                               note=note,
                               categories=categories,
                               user_name=user_name)

    except Exception as e:
        log_error(e)
        # return redirect(url_for('page_not_found'))
        raise
    finally:
        session.close()

    return redirect(url_for('page_not_found'))


@app.route('/categories/<string:category_name>/notes/new',
           methods=['GET', 'POST'])
def new_note(category_name):
    '''Handle GET and POST for note creation

    Arguments:
        category_name {str} -- category add the note to, from the url

    Returns:
        On GET: Response object -- A response with the appropriate page
    '''
    user_name = 'Guest'
    session = DBSession()
    # try getting relevant information from database and verify log in status.
    try:
        categories = session.query(Category).all()
        user = verify_login(session)
        session.close()

        if user:
            user_name = user.name

        else:
            flash('Please Log In.')
            return redirect(url_for('show_notes', category_name=category_name))

    except Exception as e:
        session.close()
        log_error(e)

    # If data exists and a used is logged in, handle GET and POST requests
    else:
        if request.method == 'GET':
            return render_template('newNote.html',
                                   categories=categories,
                                   category_name=category_name,
                                   user_name=user_name)

        if request.method == 'POST':
            newNote = Note(category_name=category_name,
                           owner_id=login_session['id'],
                           title=request.form['title'],
                           body=request.form['body'])
            try:
                session.add(newNote)
                session.commit()
                session.close()
            except Exception as e:
                session.close()
                log_error(e)
            else:
                return redirect(url_for('show_notes',
                                category_name=category_name))

    return redirect(url_for('page_not_found'))


@app.route('/categories/<string:category_name>/notes/<int:id>/edit',
           methods=['GET', 'POST'])
def edit_note(category_name, id):
    '''Handle GET and POST for note editing

    Arguments:
        category_name {str} -- category of the note to edit, from the url
        id {int} -- id of the not to edit, from the url

    Returns:
        Response object -- A response with the appropriate page
    '''

    try:
        session = DBSession()
        user = verify_login(session)
        if user:
            categories = session.query(Category).all()
            note = session.query(Note).filter_by(id=id).one()

            if request.method == 'POST':
                if note.owner_id == user.id:
                    if request.form['body'] and request.form['title']:
                        note.title = request.form['title']
                        note.body = request.form['body']
                        session.add(note)
                        session.commit()
                    else:
                        flash('Invalid Request. Try again.')
                else:
                    return redirect(url_for('show_notes',
                                            category_name=category_name))
            elif request.method == 'GET':
                if note.owner_id == user.id:
                    return render_template('editNote.html',
                                           categories=categories,
                                           user_name=user.name,
                                           note=note)
                else:
                    return redirect(url_for('show_notes',
                                            category_name=category_name))

        else:
            return redirect(url_for('show_login'))

    except Exception as e:
        log_error(e)
        # return redirect(url_for('page_note_found'))
        raise
    else:
        return redirect(url_for('show_note',
                                category_name=category_name,
                                id=id))
    finally:
        session.close()

    return redirect(url_for('page_not_found'))


@app.route('/categories/<string:category_name>/notes/<int:id>/delete',
           methods=['GET', 'POST'])
def delete_note(category_name, id):
    '''Handle note deletion GE and POST requests

    Arguments:
        category_name {str} -- category of the note to delete, from the url
        id {int} -- id of the note to delete

    Returns:
        Response object -- A response with the appropriate page
    '''

    try:
        session = DBSession()
        user = verify_login(session)
        if user:
            note_del = session.query(Note).filter_by(id=id).one()

            if request.method == 'POST':
                if note_del.owner_id == user.id:
                    session.delete(note_del)
                    session.commit()
                    flash(f'{note_del.title} was deleted from {category_name}')
                else:
                    return redirect(url_for('page_not_found'))
            elif request.method == 'GET':
                categories = session.query(Category).all()
                return render_template('deleteNote.html',
                                       note=note_del,
                                       categories=categories,
                                       user_name=user.name)

        else:
            return redirect(url_for('show_login'))

    except Exception as e:
        log_error(e)
        # TODO
        # return redirect(url_for('page_not_found'))
        raise
    else:
        print('Should have worked.')
        return redirect(url_for('show_notes', category_name=category_name))
    finally:
        session.close()

    return redirect(url_for('show_categories'))


@app.route('/error')
def page_not_found():
    '''Render a catch-all error page

    Returns:
        Response object -- A response containing the generic error page
    '''
    return render_template('pageNotFound.html')


def log_error(error):
    '''Handle error responses that should be logged

    Arguments:
        error {str} -- The exception or error response __repr__
    '''

    # TODO: append to a file
    print(error)


def log_message(response):
    '''Handle non-error responses that should be logged.

    Arguments:
        response {str} -- A description of app functionality that should be
        logged
    '''
    # TODO: append to a file
    print(response)


def verify_login(session):
    '''Helper function to return the user logged in, if present

    Arguments:
        session {DBSession} -- DBSession object created in the calling scope

    Returns:
        User -- The user logged in to the session, or false
    '''

    if 'access_token' in login_session:
        user = session.query(User).filter_by(
                name=login_session['name']).one()
        return user
    else:
        return False


if __name__ == '__main__':
    app.secret_key = app_secret
    # app.run(host='0.0.0.0', port=80, debug=True)
    app.run(host='0.0.0.0', port=80)
