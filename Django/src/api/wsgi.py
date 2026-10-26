"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

django_application = get_wsgi_application()


def application(environ, start_response):
    """WSGI application that ensures responses are properly rendered"""
    
    # Call Django app
    app_iter = django_application(environ, start_response)
    
    # Check if it's a TemplateResponse and render it
    try:
        # Render TemplateResponse if needed
        if hasattr(app_iter, 'render'):
            app_iter.render()
        for data in app_iter:
            yield data
    except Exception:
        logging.getLogger(__name__).exception('WSGI response failed')
        raise
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
