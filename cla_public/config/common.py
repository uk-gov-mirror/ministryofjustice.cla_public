import os
import datetime
from flask.ext.babel import lazy_gettext as _


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DEBUG = False

TESTING = False

CLEAR_SESSION = True

# Disable eligibility check and allow users to request a callback only
CONTACT_ONLY = os.environ.get('CALLMEBACK_ONLY', False) == 'True'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': (
                '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d '
                '%(message)s')
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'logstash': {
            '()': 'logstash_formatter.LogstashFormatter'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG'
        }
    }
}

SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))

# Should be True when served over HTTPS, False otherwise (or CSRF will break)
SESSION_COOKIE_SECURE = True

PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=5)

APP_SETTINGS = {
    'app_title': _('Civil Legal Advice'),
    'proposition_title': _('Civil Legal Advice')
}

# Timeout for api get requests so they don't hang waiting for a response
API_CLIENT_TIMEOUT = 10

BACKEND_API = {
    'url': 'http://localhost:8000/checker/api/v1/'
}

SENTRY_DSN = os.environ.get('RAVEN_CONFIG_DSN', '')
SENTRY_SITE_NAME = os.environ.get('RAVEN_CONFIG_SITE', '')

ADDRESSFINDER_API_HOST = os.environ.get('ADDRESSFINDER_API_HOST')
ADDRESSFINDER_API_TOKEN = os.environ.get('ADDRESSFINDER_API_TOKEN')

ZENDESK_API_USERNAME = os.environ.get('ZENDESK_API_USERNAME')
ZENDESK_API_TOKEN = os.environ.get('ZENDESK_API_TOKEN')

GA_ID = os.environ.get('GA_ID')

CACHE_TYPE = 'simple'

STATSD_PREFIX = 'public'
STATSD_HOST = os.environ.get('STATSD_HOST', 'localhost')
STATSD_PORT = os.environ.get('STATSD_PORT', 8125)

EXTENSIONS = []

CLA_ENV = os.environ.get('CLA_ENV', 'dev')

LANGUAGES = [
    ('en', 'English'),
    ('cy', 'Welsh'),
]

config_path = lambda x: os.path.join(PROJECT_ROOT, 'config', 'forms', x, 'forms_config.yml')

FORM_CONFIG_TRANSLATIONS = {l: config_path(l) for l, label in LANGUAGES}

OPERATOR_HOURS = {
    'weekday': (datetime.time(9, 0), datetime.time(20, 0)),
    'saturday': (datetime.time(9, 0), datetime.time(12, 30)),
    '2014-12-24': (datetime.time(9, 0), datetime.time(18, 30)),
    '2014-12-31': (datetime.time(9, 0), datetime.time(18, 30)),
}

TIMEZONE = 'Europe/London'

LAALAA_API_HOST = os.environ.get(
    'LAALAA_API_HOST',
    'https://prod.laalaa.dsd.io')

# local.py overrides all the common settings.
try:
    from cla_public.config.local import *
except ImportError:
    pass
