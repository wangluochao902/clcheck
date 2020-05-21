import os

ROOTDIR = os.path.dirname(__file__)
CLCHECKERDIR = os.path.join(ROOTDIR, "clchecker")
EMANDIR = os.path.join(ROOTDIR, 'eman')
EMAN = os.path.join(CLCHECKERDIR, 'eman.tx')
DOCKERFILE_RECORD = os.path.join(ROOTDIR, 'dockerfiles/dockerfile_records.pkl')

# host to pass into Flask's app.run.
HOST_IP = os.getenv('HOST_IP', False)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost')
DEBUG = True

COMMON_COMMANDS = ['apt-get', 'rm', 'cd', 'cp', 'mkdir', 'mv', 'chown', 'chmod']
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
        'clcheck': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
