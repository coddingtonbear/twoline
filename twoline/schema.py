message_schema = {
    'title': 'Message Schema',
    'type': 'object',
    'properties': {
        'message': {
            'type': 'string'
        },
        'expires': {
            'oneOf': [
                {
                    # String datetime; parsed by dateutil
                    'type': 'string',
                },
                {
                    # Seconds from now
                    'type': 'integer',
                    'minimum': 0,
                }
            ]
        },
        'color': {
            'type': 'array',
            'minItems': 3,
            'maxItems': 3,
            'items': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 255,
            }
        },
        'blink': {
            'type': 'array',
            'minItems': 1,
            'items': {
                'type': 'array',
                'minItems': 3,
                'maxItems': 3,
                'items': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 255,
                }
            }
        },
        'backlight': {
            'type': 'boolean',
        },
        'timeout': {
            'type': 'integer',
            'minimum': 1,
        },
        'id': {
            'type': 'string',
        }
    },
    'additionalProperties': False,
    'required': ['message']
}

integer_schema = {
    'title': 'Brightness/Contrast Schema',
    'type': 'integer',
    'minimum': 1,
    'maximum': 255
}
