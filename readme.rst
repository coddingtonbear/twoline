
Twoline
=======

Easily display messages on your `two-line LCD screen <http://www.adafruit.com/products/784>`_.

Features
--------

* **Network accessible**:  Posting a message on your screen is as easy as a simple ``curl`` command.
* **Automatic rotation**:  If you send multiple messages to the screen for display, Twoline will rotate through them for you automatically.
* **Automatic paging**:  Your screen can only show 32 characters at a time?  Don't worry; Twoline will page through your message for you.
* **Easy color and blinking configuration**: Every message can have its own color.
* **Message expiration**: Can't be bothered to send a ``DELETE`` to remove your message when its no longer relevant?  Just set your messages's ``expires`` key and Twoline will automatically remove the message when it's over.


URLS
----

``/``: Index
  URL Index

  - *GET*: Display all endpoints and acceptable methods.

``/message/``: Messages
  List or create a message to add to the message rotation.

  - *GET*: Get a list of all current messages.
  - *POST*: Add a new message to the list of messages to cycle through.

``/message/<message_id>/``: Message Details
  Create, delete, or alter an existing message.

  - *GET*: Get an existing message object for a given ID.
  - *PUT*: Replace an existing message object for a given ID.
  - *PATCH*: Update an existing message object for a given ID.
  - *DELETE*: Delete an existing message object for a given ID.

``/flash/``: Flash Messages
  Short-duration single-time announcements.

  - *GET*: Get the current flash message (if one exists).
  - *PUT*: Set the flash message to a given message object.
  - *DELETE*: Delete the current flash message (if one exists).

``/brightness/``: Brightness
  Screen brightness.

  - *PUT*: Set brightness.

``/contrast/``: Contrast
  Screen contrast.

  - *PUT*: Set contrast.


Message Object
--------------

.. code:: python

    {
        'message': 'Until this message disappears, Adam is not yet 30',
        'color': [255, 255, 255], # Optional; set the color
        'blink': [
            [255, 0, 0],
            [0, 0, 0]
        ], # Optional; cycle through these colors
        'expires': '2014-03-02 00:00', # Optional;  The parser -- dateutil --
                                       # is very liberal, but your mileage may
                                       # vary.  If no timezone is specified
                                       # defaults to the local system timezone.
                                       # Can also be an integer number of
                                       # seconds from the current time.
        'interval': 5, # Optional; Only for regular messages;
                       # Number of seconds to display this message before
                       # switching to the next
        'timeout': 300,  # Optional; Only for flash messages;
                         # Number of seconds until message disappears
        'backlight': True,  # Optional; Backlight on or off
    }

Simple Curl Example
-------------------

To post a message to your screen using ``curl`` just run a command like the below:

::
    curl -i -X POST -H "Content-Type: application/json" -d '{"message": "Hello World"}' http://127.0.0.1:6224/message/
