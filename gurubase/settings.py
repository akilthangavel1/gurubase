from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-4-yjb8&k%l434=^!-n+rx17-aaynyy0olz%3-9=4zhjw!y^f-5'


DEBUG = True

ALLOWED_HOSTS = ['*']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    'channels',
    'django_celery_beat',
    'social_django',
    'blog',
    'dasoptions',
    'ddfuture',
    'indfuture',
    'staticfuture',
    'maindas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'gurubase.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'gurubase.wsgi.application'

ASGI_APPLICATION = 'gurubase.asgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'gurubase',        
        'USER': 'akil',         
        'PASSWORD': 'Akil@2007',   
        'HOST': 'localhost',         
        'PORT': '5432',             
    }
}




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

if DEBUG:
    STATIC_URL = '/static/'
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'),
    ]
else:
    STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# Fyers API Settings
FYERS_CONFIG = {
    'client_id': os.getenv('FYERS_CLIENT_ID'),
    'api_secret_key': os.getenv('FYERS_API_SECRET_KEY'),
    'redirect_url': os.getenv('FYERS_REDIRECT_URL'),
    'access_token': os.getenv('FYERS_ACCESS_TOKEN'),
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Use Redis as message broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'  # Set to Indian timezone

# Security Settings - Disable SSL redirect in development
SECURE_SSL_REDIRECT = True # Set to True in production
SESSION_COOKIE_SECURE = True # Set to True in production
CSRF_COOKIE_SECURE = True # Set to True in production
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SOCIAL_AUTH_REDIRECT_IS_HTTPS = False

# Remove or comment out these HSTS settings in development
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Additional Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'


# Authentication backends
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Google OAuth2 settingsx
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH2_SECRET')

# Add these settings
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True # Set to True in production
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_URL = 'logout'
LOGOUT_REDIRECT_URL = 'login'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
SECURE_CROSS_ORIGIN_OPENER_POLICY=None

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'file': {
#             'level': 'DEBUG',
#             'class': 'logging.FileHandler',
#             'filename': 'logfile.log',
#         },
#         'console': {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['file', 'console'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#     },
# }