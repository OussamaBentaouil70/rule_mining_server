import json
from operator import lt
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
from django.http import JsonResponse, HttpResponse
from pymongo import MongoClient
import os
import uuid
import urllib3
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
import zipfile
import csv
from mistral.views import extract_token_from_headers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Node, Edge
from .serializers import NodeSerializer, EdgeSerializer









# Suppress only the single InsecureRequestWarning from urllib3 needed in this context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define the Elasticsearch endpoint and index name
ELASTICSEARCH_URL = 'https://localhost:9200/'
INDEX_NAME = 'index_rules'
 
# Define the authentication credentials for Elasticsearch
USERNAME = 'elastic'
PASSWORD = 'kl8mEE84P8a+_zZPofjn'

# Connect to MongoDB Atlas
client = MongoClient(settings.MONGO_URI)
db = client['vectorDB']


@csrf_exempt
def create_index_with_mapping(request):
    headers = {'Content-Type': 'application/json'}
    index_mapping = {
        "mappings": {
            "properties": {
                "name": {"type": "text"},
                "description": {"type": "text"},
                "tag": {"type": "keyword"}
            }
        }
    }
    response = requests.put(
        ELASTICSEARCH_URL + INDEX_NAME,
        json=index_mapping,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers=headers,
        verify=False
    )
    
    if response.status_code == 200:
        return JsonResponse({'message': f"Index '{INDEX_NAME}' created successfully."})
    else:
        return JsonResponse({'error': f"Failed to create index '{INDEX_NAME}'. Status code: {response.status_code}", 'details': response.text}, status=400)


@csrf_exempt
@extract_token_from_headers
def upload_file(request):
    if request.method == 'POST' and request.FILES['file']:
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)
        
        # Determine file type and call the appropriate extraction function
        if filename.endswith('.zip'):
            extracted_data = extract_data_from_zip(file_path)
        elif filename.endswith('.csv'):
            extracted_data = extract_data_from_csv(file_path)
        elif filename.endswith('.txt'):
            extracted_data = extract_data_from_file(file_path)
        else:
            return JsonResponse({'error': "Unsupported file type."}, status=400)
        
        if not extracted_data:
            return JsonResponse({'error': "No data extracted from the file."}, status=400)

        save_to_mongodb(extracted_data)
        index_to_elasticsearch(extracted_data)

        return JsonResponse({'message': "File uploaded and data indexed successfully."})
    return JsonResponse({'error': 'Invalid request method or no file uploaded'}, status=405)


@csrf_exempt
@extract_token_from_headers
def search_rules(request):
    if request.method == 'POST':
        user = request.user
        print(user)
        tag = user.get('fonction', '')
        print(tag)
        rules = search_in_elasticsearch(tag)
        return JsonResponse(rules, safe=False)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
@extract_token_from_headers
def generate_brl_files(request):
    if request.method == 'POST':
        user = request.user
        tag = user.get('fonction', '')
        rules = search_in_elasticsearch(tag)
        if rules:
            directory = f"Rules_{tag}"
            for rule in rules:
                generate_brl_file(rule, directory)
            return JsonResponse({'message': f"BRL files generated in {directory}"})
        return JsonResponse({'message': 'No rules found for the given tag'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# Helper functions
def extract_data_from_file(file_path):
    extracted_data = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
        i = 0
        while i < len(lines):
            if 'name: ' in lines[i] and 'description: ' in lines[i + 1]:
                name = lines[i].split(': ')[1].strip()
                description = lines[i + 1].split(': ')[1].strip()
                tag_name = os.path.basename(file_path).split('.')[0]
                extracted_data.append({'name': name, 'description': description, 'tag': tag_name})
                i += 2
            else:
                print(f"Skipping malformed data at line {i} and {i + 1} in the input file.")
                i += 1
    return extracted_data


def extract_data_from_zip(zip_file_path):
    extracted_data = []
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall("extracted_zip")
        for file_name in zip_ref.namelist():
            if file_name.endswith('.txt'):
                extracted_data.extend(extract_data_from_file(os.path.join("extracted_zip", file_name)))
            elif file_name.endswith('.csv'):
                extracted_data.extend(extract_data_from_csv(os.path.join("extracted_zip", file_name)))
    return extracted_data


def extract_data_from_csv(csv_file_path):
    extracted_data = []
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get('name')
            description = row.get('description')
            tag = os.path.basename(csv_file_path).split('.')[0]
            if name and description:
                extracted_data.append({'name': name, 'description': description, 'tag': tag})
    return extracted_data


def save_to_mongodb(data):
    for item in data:
        collection_name = f"Rule_{item['tag']}"
        collection = db[collection_name]
        collection.insert_one(item)


def index_to_elasticsearch(data):
    headers = {'Content-Type': 'application/json'}
    bulk_data = ""
    
    for item in data:
        item.pop('_id', None)
        
        action = {
            "index": {
                "_index": INDEX_NAME,
                "_id": item["name"]
            }
        }
        
        bulk_data += json.dumps(action) + "\n" + json.dumps(item) + "\n"

    response = requests.post(
        ELASTICSEARCH_URL + "_bulk",
        data=bulk_data,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers=headers,
        verify=False
    )

    if response.status_code == 200:
        print(f"Data indexed successfully.")
    else:
        print(f"Failed to index data. Status code: {response.status_code}")
        print(response.text)


def search_in_elasticsearch(tag):
    headers = {'Content-Type': 'application/json'}
    query = {
        "query": {
            "match": {
                "tag": tag
            }
        }
    }

    response = requests.post(
        ELASTICSEARCH_URL + INDEX_NAME + "/_search",
        json=query,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers=headers,
        verify=False
    )

    if response.status_code == 200:
        response_data = response.json()
        rules = [{'name': hit['_source']['name'], 'description': hit['_source']['description']} for hit in response_data.get('hits', {}).get('hits', [])]
        return rules
    else:
        print(f"Failed to search in index. Status code: {response.status_code}")
        print(response.text)
        return []


def generate_brl_file(rule, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_name = os.path.join(directory, rule['name'].replace(" ", "_") + ".brl")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ilog.rules.studio.model.brl:ActionRule xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:ilog.rules.studio.model.brl="http://ilog.rules.studio/model/brl.ecore">
  <name>{rule['name']}</name>
  <uuid>{uuid.uuid4()}</uuid>
  <locale>en_US</locale>
  <definition><![CDATA[{rule['description']}]]></definition>
</ilog.rules.studio.model.brl:ActionRule>"""

    with open(file_name, 'w') as file:
        file.write(xml_content)
    print(f"Generated BRL file: {file_name}")


@api_view(['GET'])
def get_flow(request):
    nodes = Node.objects.all()
    edges = Edge.objects.all()

    node_serializer = NodeSerializer(nodes, many=True)
    edge_serializer = EdgeSerializer(edges, many=True)

    return Response({
        "nodes": node_serializer.data,
        "edges": edge_serializer.data
    })

@api_view(['POST'])
def save_flow(request):
    nodes_data = request.data.get('nodes', [])
    edges_data = request.data.get('edges', [])

    Node.objects.all().delete()
    Edge.objects.all().delete()

    for node_data in nodes_data:
        position = node_data.pop('position')
        node_data['position_x'] = position['x']
        node_data['position_y'] = position['y']
        serializer = NodeSerializer(data=node_data)
        if serializer.is_valid():
            serializer.save()

    for edge_data in edges_data:
        serializer = EdgeSerializer(data=edge_data)
        if serializer.is_valid():
            serializer.save()

    return Response({"status": "Flow saved successfully!"})