
Twoline
=======

A simple manager for two-line LCD displays.


URLS
----

``/``: Index
  *GET*: Display all endpoints and acceptable methods.

``/brightness/``: Brightness
  *GET*: Return brightness.
  *PUT*: Set brightness.

``/contrast/``: Contrast
  *GET*: Return contrast.
  *PUT*: Set contrast.

``/flash/``: Flash Messages
  *GET*: Get the current flash message (if one exists).
  *PUT*: Set the flash message to a given message object.
  *DELETE*: Delete the current flash message (if one exists).

``/message/``: Messages
  *GET*: Get a list of all current messages.
  *POST*: Add a new message to the list of messages to cycle through.

``/message/<message_id>/``: Message Details
  *GET*: Get an existing message object for a given ID.
  *PUT*: Replace an existing message object for a given ID.
  *PATCH*: Update an existing message object for a given ID.
  *DELETE*: Delete an existing message object for a given ID.

Message Object
--------------

.. code:: python

    {
        'message': 'Any message',
        'id': 'An ID',  # Optional; will be set automatically if unspecified
        'color': [255, 255, 255], # Optional; set the color
        'blink': [
            [255, 0, 0],
            [0, 0, 0]
        ], # Optional; cycle through these colors
        'expires': 'Sun, 9 June 2013, 22:45 PDT', # Optional; Can also be an integer number of seconds from the current time
        'timeout': 300,  # Optional; Only for flash messages; Number of seconds until message disappears
        'backlight': True,  # Optional; Backlight on or off
    }

