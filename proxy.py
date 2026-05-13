import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SB_URL = os.environ.get('SUPABASE_URL', 'https://vtmzpjkjabuuyhsahhol.supabase.co')
SB_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0bXpwamtqYWJ1dXloc2FoaG9sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2MTE4OTMsImV4cCI6MjA5MzE4Nzg5M30.EokwncNDVHsinnAqoHKNI9S0DW79t2N0hWpQhmMFlNQ')

SB_HEADERS = {
    'apikey': SB_KEY,
    'Authorization': 'Bearer ' + SB_KEY,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

@app.route('/checklist', methods=['GET'])
def get_checklist():
    date = request.args.get('date')
    if not date:
        return jsonify([])
    res = requests.get(
        SB_URL + '/rest/v1/daily_checklist?date=eq.' + date + '&select=*',
        headers=SB_HEADERS
    )
    return jsonify(res.json())

@app.route('/checklist', methods=['POST'])
def save_checklist():
    data = request.get_json()
    date = data.get('date')
    state = data.get('state')
    if not date or state is None:
        return jsonify({'error': 'missing data'}), 400
    res = requests.post(
        SB_URL + '/rest/v1/daily_checklist',
        headers=SB_HEADERS,
        json={'date': date, 'state': state}
    )
    return jsonify({'ok': True, 'status': res.status_code})

@app.route('/punchlist', methods=['GET'])
def get_punchlist():
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify([])
    res = requests.get(
        SB_URL + '/rest/v1/projects?project_id=eq.' + str(project_id) + '&select=*',
        headers=SB_HEADERS
    )
    return jsonify(res.json())

@app.route('/punchlist', methods=['POST'])
def save_punchlist():
    data = request.get_json()
    res = requests.post(
        SB_URL + '/rest/v1/projects',
        headers=SB_HEADERS,
        json=data
    )
    return jsonify({'ok': True, 'status': res.status_code})

@app.route('/punchlist', methods=['PATCH'])
def update_punchlist():
    item_id = request.args.get('id')
    data = request.get_json()
    res = requests.patch(
        SB_URL + '/rest/v1/projects?id=eq.' + str(item_id),
        headers=SB_HEADERS,
        json=data
    )
    return jsonify({'ok': True, 'status': res.status_code})
@app.route('/health', methods=['GET'])
def get_health():
    date = request.args.get('date')
    if not date:
        return jsonify([])
    res = requests.get(
        SB_URL + '/rest/v1/health_stats?date=eq.' + date + '&select=*',
        headers=SB_HEADERS
    )
    return jsonify(res.json())

@app.route('/health', methods=['POST'])
def save_health():
    data = request.get_json()
    date = data.get('date')
    state = data.get('state')
    if not date or state is None:
        return jsonify({'error': 'missing data'}), 400
    res = requests.post(
        SB_URL + '/rest/v1/health_stats',
        headers=SB_HEADERS,
        json={'date': date, 'state': state}
    )
    return jsonify({'ok': True, 'status': res.status_code})
@app.route('/')
def health():
    return 'BOD Proxy OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
