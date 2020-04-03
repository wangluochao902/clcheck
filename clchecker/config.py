import os

ROOTDIR = os.path.dirname(os.path.dirname(__file__))
CLCHECKERDIR = os.path.join(ROOTDIR, "clchecker")
SYNOPDIR = os.path.join(ROOTDIR, 'ShellSynopsis')
SYNOPSIS = os.path.join(CLCHECKERDIR, 'synopsis.tx')


# host to pass into Flask's app.run.
HOST_IP = os.getenv('HOST_IP', False)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost')
DEBUG = True

LOGGING_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level' : 'INFO',
            'class' : 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'filename': 'application.log',
            'mode': 'a',
        },
    },
    'loggers': {
        'explainshell': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
