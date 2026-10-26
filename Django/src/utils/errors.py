import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def server_error(request):
    """Call inside an exception handler; never include request secrets in logs."""
    logger.exception('Unhandled error during %s %s', request.method, request.path)
    return JsonResponse({'error': 'Internal server error'}, status=500)
