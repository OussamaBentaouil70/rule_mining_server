import base64
import os
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
from django.core.files.storage import default_storage
import cloudinary.uploader

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
                "username": user.username,
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
                    "username": user.username,
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
@extract_token_from_headers
def get_profile(request):
    print("Decoded user from token:", request.user)
    if request.user:
        return JsonResponse(request.user)
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
    try:
        owner_data = request.user

        # Retrieve the Owner instance based on the user_id from the token
        owner = Owner.objects.get(id=owner_data['user_id'])

        if owner.role != "owner":
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        data = json.loads(request.body.decode('utf-8'))
        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        fonction = data.get('fonction')
        phone_number = data.get('phone_number')
        bio = data.get('bio')
        address = data.get('address')

        if not fonction:
            return JsonResponse({'error': 'Fonction is required'}, status=400)

        if Member.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        if Member.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already exists'}, status=400)

        hashed_password = make_password(password)
        new_member = Member.objects.create(
            full_name=full_name,
            username=username,
            email=email,
            password=hashed_password,
            role="member",
            fonction=fonction,
            phone_number=phone_number,
            bio=bio,
            address=address,
            owner=owner  # Assign the Owner instance directly
        )

        return JsonResponse({
            'id': new_member.id,
            'username': new_member.username,
            'full_name': new_member.full_name,
            'email': new_member.email,
            'role': new_member.role,
            'fonction': new_member.fonction,
            'phone_number': new_member.phone_number,
            'bio': new_member.bio,
            'address': new_member.address,
            'owner': new_member.owner.id
        }, status=201)

    except Owner.DoesNotExist:
        return JsonResponse({'error': 'Owner not found'}, status=404)
    except Exception as e:
        print("Error creating member by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)



@csrf_exempt
@extract_token_from_headers
@require_http_methods(["PUT"])
def update_member_by_owner(request, user_id):
    owner_data = request.user

        # Retrieve the Owner instance based on the user_id from the token
    owner = Owner.objects.get(id=owner_data['user_id'])
    
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
            'full_name': member.full_name,
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
    owner_data = request.user

        # Retrieve the Owner instance based on the user_id from the token
    owner = Owner.objects.get(id=owner_data['user_id'])

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
    owner_data = request.user

    try:
        owner = Owner.objects.get(id=owner_data['user_id'])

        if owner.role != "owner":
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        members = Member.objects.filter(owner=owner.id)
        members_list = [{
            'id': member.id, 
            'username': member.username, 
            'email': member.email, 
            'role': member.role, 
            'fonction': member.fonction,
            'avatar': member.avatar.url if member.avatar else None  # Convert avatar to URL
        } for member in members]

        return JsonResponse(members_list, safe=False, status=200)

    except Owner.DoesNotExist:
        return JsonResponse({'error': 'Owner not found'}, status=404)
    except Exception as e:
        print("Error listing members by owner", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@extract_token_from_headers
@require_http_methods(["GET"])
def get_member_by_id(request, member_id):
    print("View function called with method:", request.method)
    owner_data = request.user

        # Retrieve the Owner instance based on the user_id from the token
    owner = Owner.objects.get(id=owner_data['user_id'])

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
            'full_name': member.full_name,
            'address': member.address,
            'phone_number': member.phone_number,
            'bio': member.bio,
            'avatar': member.avatar.url if member.avatar else None,# Convert avatar to URL
            'owner': member.owner.id
        }, status=200)

    except Exception as e:
        print("Error getting member by ID", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)



    
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
    





@csrf_exempt
@require_http_methods(["PUT"])
def update_user_profile(request):
    try:
        user_data = request.user
        user_id = user_data['user_id']
        role = user_data['role']

        Model = get_user_model(role)
        user = Model.objects.get(id=user_id)

        data = request.POST.get('data')
        if data:
            data = json.loads(data)  # Extracting JSON data

        avatar_file = request.FILES.get('avatar')  # Extracting avatar file

        if avatar_file:  # If avatar file is provided, handle avatar update with Cloudinary
            upload_result = cloudinary.uploader.upload(avatar_file)
            user.avatar = upload_result['url']

        # Update other user fields based on the JSON data
        if data:
            if 'username' in data:
                user.username = data['username']
            if 'email' in data:
                user.email = data['email']
            if 'full_name' in data:
                user.full_name = data['full_name']
            if 'address' in data:
                user.address = data['address']
            if 'phone_number' in data:
                user.phone_number = data['phone_number']
            if 'bio' in data:
                user.bio = data['bio']

        user.save()

        response_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'address': user.address,
            'phone_number': user.phone_number,
            'bio': user.bio,
            'role': user.role,
            'fonction': user.fonction,
            'avatar': user.avatar.url if user.avatar else None
        }

        return JsonResponse(response_data, status=200)

    except Model.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)
    except Exception as e:
        print("Error updating user profile", e)
        return JsonResponse({'error': 'Internal server error'}, status=500)