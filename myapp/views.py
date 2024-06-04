import base64
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import jwt
import json
from myapp.models import Owner, Member
from django.views.decorators.http import require_http_methods
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
from myapp.models import Rule
import json
from django.db import models
from pymongo import MongoClient

User = get_user_model()

def get_user_model(role):
    return Owner if role == 'owner' else Member



def extract_token_from_headers(view_func):
    def _wrapped_view(request, *args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Token not provided'}, status=401)

        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            request.user = decoded
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=400)

        return view_func(request, *args, **kwargs)

    return _wrapped_view




@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role')
            fonction = data.get('fonction')

            if not username:
                return JsonResponse({'error': 'Username is required'}, status=400)

            Model = get_user_model(role)
            if Model.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)

            if not password or len(password) < 6:
                return JsonResponse({'error': 'Password is required and should be at least 6 characters long'}, status=400)

            if not email:
                return JsonResponse({'error': 'Email is required'}, status=400)

            if Model.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already exists'}, status=400)

            hashed_password = make_password(password)

            new_user = Model.objects.create(
                username=username,
                email=email,
                password=hashed_password,
                role=role,
                fonction=fonction
            )

            return JsonResponse({'id': new_user.id, 'username': new_user.username, 'email': new_user.email, 'role': new_user.role, 'fonction': new_user.fonction}, status=201)
        except Exception as e:
            print("Error while registering user", e)
            return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({'error': 'Email and password are required'}, status=400)

            user = Member.objects.filter(email=email).first() or Owner.objects.filter(email=email).first()

            if not user or not check_password(password, user.password):
                return JsonResponse({'error': 'Invalid email or password'}, status=400)

            token_payload = {
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'fonction': user.fonction,
                'members': list(user.members.values('id', 'username')) if user.role == "owner" else []
            }

            token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')

            response_data = {
                'token': token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'fonction': user.fonction
                },
                'members': token_payload['members'] if user.role == "owner" else []
            }

            response = JsonResponse(response_data)
            response.set_cookie('token', token, httponly=True)
            
            return response
        except Exception as e:
            print("Error while logging in user", e)
            return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
def get_profile(request):
    token = request.COOKIES.get('token')
    if token:
        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return JsonResponse(decoded_token)
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=400)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=400)
    else:
        return JsonResponse({'error': 'User not authenticated'}, status=400)

@csrf_exempt
def logout(request):
    response = JsonResponse({'message': 'Logged out'})
    response.delete_cookie('token')
    return response





@csrf_exempt
@extract_token_from_headers
@require_http_methods(["POST"])
def create_member_by_owner(request):
    owner = request.user

    if owner.role != "owner":
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    data = json.loads(request.body.decode('utf-8'))
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    fonction = data.get('fonction')

    if not fonction:
        return JsonResponse({'error': 'Fonction is required'}, status=400)

    try:
        if Member.objects.filter(username=username).exists() or Member.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Username or email already exists'}, status=400)

        hashed_password = make_password(password)
        new_member = Member.objects.create(
            username=username,
            email=email,
            password=hashed_password,
            role="member",
            fonction=fonction,
            owner=owner
        )

        owner.members.add(new_member)
        owner.save()

        return JsonResponse({
            'id': new_member.id,
            'username': new_member.username,
            'email': new_member.email,
            'role': new_member.role,
            'fonction': new_member.fonction,
            'owner': new_member.owner.id
        }, status=201)

    except Exception as e:
        print("Error creating member by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@extract_token_from_headers
@require_http_methods(["PUT"])
def update_member_by_owner(request, user_id):
    owner = request.user

    if owner.role != "owner":
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    data = json.loads(request.body.decode('utf-8'))
    username = data.get('username')
    email = data.get('email')
    fonction = data.get('fonction')

    if not fonction:
        return JsonResponse({'error': 'Fonction is required'}, status=400)

    try:
        updated_member = Member.objects.filter(id=user_id, owner=owner).update(
            username=username,
            email=email,
            fonction=fonction
        )

        if not updated_member:
            return JsonResponse({'error': 'Member not found or unauthorized'}, status=404)

        member = Member.objects.get(id=user_id)
        return JsonResponse({
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'role': member.role,
            'fonction': member.fonction,
            'owner': member.owner.id
        }, status=200)

    except Exception as e:
        print("Error updating member by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@extract_token_from_headers
@require_http_methods(["DELETE"])
def delete_member_by_owner(request, user_id):
    owner = request.user

    if owner.role != "owner":
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        member = Member.objects.filter(id=user_id, owner=owner).first()
        
        if not member:
            return JsonResponse({'error': 'Member not found or unauthorized'}, status=404)

        member.delete()
        return JsonResponse({'message': 'Member deleted successfully'}, status=200)

    except Exception as e:
        print("Error deleting member by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@extract_token_from_headers
@require_http_methods(["GET"])
def list_members_by_owner(request):
    owner = request.user

    if owner.role != "owner":
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        members = Member.objects.filter(owner=owner)
        members_list = [{'id': member.id, 'username': member.username, 'email': member.email, 'role': member.role, 'fonction': member.fonction} for member in members]

        return JsonResponse(members_list, safe=False, status=200)

    except Exception as e:
        print("Error listing members by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@extract_token_from_headers
@require_http_methods(["GET"])
def get_member_by_id(request, member_id):
    owner = request.user

    if owner.role != "owner":
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        member = Member.objects.filter(id=member_id, owner=owner).first()

        if not member:
            return JsonResponse({'error': 'Member not found or unauthorized'}, status=404)

        return JsonResponse({
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'role': member.role,
            'fonction': member.fonction,
            'owner': member.owner.id
        }, status=200)

    except Exception as e:
        print("Error getting member by ID", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)


# def create_dynamic_model_class(tag):
#     class Meta:
#         managed = False

#     attrs = {
#         '__module__': __name__,
#         'tag': models.CharField(max_length=100),
#         'name': models.CharField(max_length=255),
#         'description': models.TextField(),
#         'Meta': Meta,
#     }

#     model_class = type(f'Rule_{tag.replace(" ", "_")}', (models.Model,), attrs)
#     return model_class



# @extract_token_from_headers
# def get_rules_by_tag(request):
#     try:
#         fonction = request.user.get('fonction')
#         print(fonction)
#         query = {
#             "query": {
#                 "match": {
#                     "tag": fonction,
#                 },
#             },
#         }

#         url = "https://localhost:9200/rules/_search?filter_path=hits.hits._source"

#         auth_header = "Basic " + base64.b64encode(f"elastic:{settings.PASSWORD}".encode()).decode()

#         # Create an https agent to ignore self-signed certificate errors
#         response = requests.post(url, headers={"Content-Type": "application/json", "Authorization": auth_header}, json=query, verify=False)

#         if not response.ok:
#             raise Exception("Failed to fetch rules by tag")

#         data = response.json()
#         source_array = [hit["_source"] for hit in data["hits"]["hits"]]

#         existing_rules = Rule.objects.filter(tag__in=[rule["tag"] for rule in source_array])
#         existing_tags = [rule.tag for rule in existing_rules]

#         for rule in source_array:
#             if rule["tag"] not in existing_tags:
#                 new_rule = Rule.objects.create(
#                     name=rule["name"],
#                     description=rule["description"],
#                     tag=rule["tag"]
#                 )
     
#                 # In Django, you do not need to create dynamically named collections like in MongoDB

#         return JsonResponse(source_array, safe=False, status=200)  # Set safe parameter to False

#     except Exception as e:
#         print("Error while fetching rules by tag", e)
#         return JsonResponse({'error': 'Internal server error'}, status=500)
    

@extract_token_from_headers
def get_rules_by_tag(request):
    try:
        fonction = request.user.get('fonction')
        print(fonction)
        query = {
            "query": {
                "match": {
                    "tag": fonction,
                },
            },
        }

        url = "https://localhost:9200/rules/_search?filter_path=hits.hits._source"

        auth_header = "Basic " + base64.b64encode(f"elastic:{settings.PASSWORD}".encode()).decode()

        # Create an https agent to ignore self-signed certificate errors
        response = requests.post(url, headers={"Content-Type": "application/json", "Authorization": auth_header}, json=query, verify=False)

        if not response.ok:
            raise Exception("Failed to fetch rules by tag")

        data = response.json()
        source_array = [hit["_source"] for hit in data["hits"]["hits"]]

        # Connect to MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]

        # Iterate over the fetched rules and insert them into their respective collections if they don't already exist
        for rule in source_array:
            collection_name = f"rules_{rule['tag']}"
            collection = db[collection_name]

            if not collection.find_one({"name": rule["name"], "tag": rule["tag"]}):
                collection.insert_one({
                    "name": rule["name"],
                    "description": rule["description"],
                    "tag": rule["tag"]
                })

        return JsonResponse(source_array, safe=False, status=200)

    except Exception as e:
        print("Error while fetching rules by tag", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)


def delete_rule(request, rule_id):
    try:
        rule = Rule.objects.filter(id=rule_id).first()

        if not rule:
            return JsonResponse({'error': 'Rule not found'}, status=404)

        rule.delete()
        
        return JsonResponse({'message': 'Rule deleted successfully'}, status=200)

    except Exception as e:
        print("Error deleting rule", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)