
Twoline
=======

A simple manager for two-line LCD displays.

Specifically, this was created for the
`Adafruit USB + Serial Backpack Kit with 16x2 RGB backlight negative LCD - RGB on Black <http://www.adafruit.com/products/784>`_,
but this should be easily adaptable to many other character LCD displays.


URLS
----

``/``: Index
  URL Index

  - *GET*: Display all endpoints and acceptable methods.

``/brightness/``: Brightness
  Screen brightness.

  - *GET*: Return brightness.
  - *PUT*: Set brightness.

``/contrast/``: Contrast
  Screen contrast.

  - *GET*: Return contrast.
  - *PUT*: Set contrast.

``/flash/``: Flash Messages
  Short-duration single-time announcements.

  - *GET*: Get the current flash message (if one exists).
  - *PUT*: Set the flash message to a given message object.
  - *DELETE*: Delete the current flash message (if one exists).

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

Message Object
--------------

.. code:: python

    {
        'message': 'Adam just turned 30! :-(',
        'id': 'An ID',  # Optional; will be set automatically if unspecified
        'color': [255, 255, 255], # Optional; set the color
        'blink': [
            [255, 0, 0],
            [0, 0, 0]
        ], # Optional; cycle through these colors
        'expires': '2014-03-02 00:00', # Optional;
                                       # Can also be an integer number of
                                       # seconds from the current time.
                                       # The parser (dateutil.parser) is
                                       # quite liberal, but your mileage may
                                       # vary.
        'interval': 5, # Optional; Only for regular messages;
                       # Number of seconds to display this message before
                       # switching to the next
        'timeout': 300,  # Optional; Only for flash messages;
                         # Number of seconds until message disappears
        'backlight': True,  # Optional; Backlight on or off
    }

