from django.http import JsonResponse
from django.middleware.csrf import get_token

def checkHealth(request):
    # check if it is a get request

    if request.method == 'GET':
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error'})

def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})