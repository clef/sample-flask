# Clef + Python
![license:mit](https://img.shields.io/badge/license-mit-blue.svg)
![build:passing](https://img.shields.io/travis/joyent/node/v0.6.svg)
![language:Python](https://img.shields.io/pypi/pyversions/Django.svg)         

## Getting started
Clef is secure two-factor auth without passwords. With the wave of their phone, users can log in to your site — it's like :sparkles: magic :sparkles:!   
Get started in three easy steps:
* Download the [iOS](https://itunes.apple.com/us/app/clef/id558706348) or [Android](https://play.google.com/store/apps/details?id=io.clef&hl=en) app on your phone 
* Sign up for a Clef developer account at [https://www.getclef.com/developer](https://www.getclef.com/developer) and create an application. That's where you'll get your API credentials (`app_id` and `app_secret`) and manage settings for your Clef integration.
* Follow the directions below to integrate Clef into your site's log in flow.        
## Usage
We'll walk you through the full Clef integration with Python and Flask below. You can check out a live version of this sample app [here](http://clef-flask.herokuapp.com/) or run it [locally](#running-this-sample-app).     

### Adding the Clef button

The Clef button is the entry point into the Clef experience. Adding it to your site is as easy as dropping a `script` tag wherever you want the button to show up.        

Set the `data-redirect-url` to the URL in your app where you will complete the OAuth handshake. You'll also want to set `data-state` to an unguessable random string.          

```javascript
<script type='text/javascript'
    class='clef-button'
    src='https://clef.io/v3/clef.js'
    data-app-id='YOUR_APP_ID'
    data-redirect-url='{{ redirect_url }}'
    data-state='{{ state }}'>
</script>
```
*See the code in [action](/templates/index.html) or read more [here](http://docs.getclef.com/v1.0/docs/adding-the-clef-button).*         

### Completing the OAuth handshake
Once you've set up the Clef button, you need to be able to handle the OAuth handshake. This is what lets you retrieve information about a user after they authenticate with Clef. The easiest way to do this is to use the Clef API wrapper for Python, which you can install via `pip`:

`$ pip install clef`

To use it, pass your `app_id` and `app_secret` to the ClefAPI constructor:           
```python
import clef

clef.initialize(app_id="YOUR_CLEF_ID", app_secret="YOUR_CLEF_SECRET")
```

Then at the route you created for the OAuth callback, access the `code` URL parameter and exchange it for user information. 

Before exchanging the `code` for user information, you first need to verify the `state` parameter sent to the callback to make sure it's the same one as the one you set in the button. (You can find implementations of the <code><a href="/app.py#L75-L80" target="_blank">is_valid_state</a></code> and <code><a href="/app.py#L82-L85" target="_blank">generate_state</a></code> functions in in `app.py`.) 

```python
@app.route('/login')
def login():

    # abort request if it doesn't match what you passed in Clef button
    state = request.args.get('state')
    if not is_valid_state(state):
        return 'Error'

    # this is a valid request so make request for user information
    code = request.args.get('code')
    user_information = clef.get_login_information(code=code)
    clef_id = user_information.get('id')

    # look up the user in your database and set them in the session
    user = User.query.filter_by(clef_id=clef_id).first()
    session['user'] = user.id
    session['logged_in_at'] = time.time()
```
*See the code in [action](/app.py#L97-L131) or read more [here](http://docs.getclef.com/v1.0/docs/authenticating-users).*             

### Logging users out 
Logout with Clef allows users to have complete control over their authentication sessions. Instead of users individually logging out of each site, they log out once with their phone and are automatically logged out of every site they used Clef to log into.

To make this work, you need to [set up](#setting-up-timestamped-logins) timestamped logins, handle the [logout webhook](#handling-the-logout-webhook) and [compare the two](#checking-timestamped-logins) every time you load the user from your database. 

#### Setting up timestamped logins
Setting up timestamped logins is easy. You just add a timestamp to the session everywhere in your application code that you do the Clef OAuth handshake:

```python
session['logged_in_at'] = time.time()
```

*See the code in [action](/app.py#L55-L73) or read more [here](http://docs.getclef.com/v1.0/docs/checking-timestamped-logins)*

#### Handling the logout webhook
Every time a user logs out of Clef on their phone, Clef will send a `POST` to your logout hook with a `logout_token`. You can exchange this for a Clef ID:

```python
@app.route('/logout', methods=['POST'])
def logout():    
    # exchange the token for a clef_id
    logout_token = request.form.get('logout_token')
    clef_id = clef.get_logout_information(logout_token=logout_token)

    # update the user
    user = User.query.filter_by(id=clef_id).first()
    user.logged_out_at = time.time()
    db.session.add(user)
    db.session.commit()
```
*See the code in [action](/app.py#L133-L157) or read more [here](http://docs.getclef.com/v1.0/docs/handling-the-logout-webhook).*          

You'll want to make sure you have a `logged_out_at` attribute on your `User` model. Also, don't forget to specify this URL as the `logout_hook` in your Clef application settings so Clef knows where to notify you.

#### Checking timestamped logins
Every time you load user information from the database, you'll want to compare the `logged_in_at` session variable to the user `logged_out_at` field. If `logged_out_at` is after `logged_in_at`, the user's session is no longer valid and they should be logged out of your application.

An easy way to do this in Flask is through a decorator: 
```python
def logged_in(view):
    """
    Decorator that checks whether a user is currently logged in.
    """
    @functools.wraps(view)
    def decorated_view(*args, **kwargs):
        user_id = session.get('user', -1)
        logged_in_at = session.get('logged_in_at', None)
        user = User.query.get(user_id)

        # does check for database logout of user
        if user and user.logged_out_at > logged_in_at:
            session.clear()
            user = None

        return view(user=user, *args, **kwargs)
    return decorated_view
```
*See the code in action [here](/app.py#L55-L73) or read more [here](http://docs.getclef.com/v1.0/docs/checking-timestamped-logins)*

## Running this sample app 
To run this sample app, clone the repo:

```
$ git clone https://github.com/clef/sample-flask.git
```

Then install the dependencies and run on localhost.
```
$ pip install -r requirements.txt
$ python app.py
```

You can also see a live demo [here](http://clef-flask.herokuapp.com/).

## Documentation
You can find our most up-to-date documentation at [http://docs.getclef.com](http://docs.getclef.com/). It covers additional topics like customizing the Clef button and testing your integration.

## Support
Have a question or just want to chat? Send an email to [support@getclef.com](mailto: support@getclef.com) or join our community Slack channel :point_right: [http://community.getclef.com](http://community.getclef.com).

We're always around, but we do an official Q&A every Friday from 10am to noon PST :) — would love to see you there! 

## About 
Clef is an Oakland-based company building a better way to log in online. We power logins on more than 80,000 websites and are building a beautiful experience and inclusive culture. Read more about our [values](https://getclef.com/values), and if you like what you see, come [work with us](https://getclef.com/jobs)!





