from django.conf import settings
from django.http import JsonResponse
import jwt


class CustomAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ['/api/register/', '/api/login/', "/api/logout/", "/api/profile/"]:
            return self.get_response(request)

        token = request.COOKIES.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Access denied. No token provided.'}, status=401)

        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
            # Assign the decoded user information directly to request.user
            request.user = decoded
            print(request.user)
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=400)

        response = self.get_response(request)
        return response
