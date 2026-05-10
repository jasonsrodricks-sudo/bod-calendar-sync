import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

SUPABASE_URL = 'https://vtmzpjkjabuuyhsahhol.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0bXpwamtqYWJ1dXloc2FoaG9sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2MTE4OTMsImV4cCI6MjA5MzE4Nzg5M30.EokwncNDVHsinnAqoHKNI9S0DW79t2N0hWpQhmMFlNQ')

SB_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
}

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
}

@app.route('/checklist', methods=['GET', 'POST', 'OPTIONS'])
def checklist():
    if request.method == 'OPTIONS':
        return '', 204, CORS_HEADERS
    
    if request.method == 'GET':
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'date required'}), 400, CORS_HEADERS
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/daily_checklist?date=eq.{date}&select=state',
            headers=SB_HEADERS
        )
        return jsonify(res.json()), 200, CORS_HEADERS
    
    if request.method == 'POST':
        data = request.get_json()
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/daily_checklist',
            headers=SB_HEADERS,
            json=data
        )
        return jsonify({'ok': True}), 200, CORS_HEADERS

@app.route('/punchlist', methods=['GET', 'POST', 'PATCH', 'OPTIONS'])
def punchlist():
    if request.method == 'OPTIONS':
        return '', 204, CORS_HEADERS
    
    if request.method == 'GET':
        project_id = request.args.get('project_id')
        if not project_id:
            return jsonify({'error': 'project_id required'}), 400, CORS_HEADERS
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/project_punchlist?project_id=eq.{project_id}&order=created_at.asc',
            headers=SB_HEADERS
        )
        return jsonify(res.json()), 200, CORS_HEADERS
    
    if request.method == 'POST':
        data = request.get_json()
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/project_punchlist',
            headers=SB_HEADERS,
            json=data
        )
        return jsonify({'ok': True}), 200, CORS_HEADERS
    
    if request.method == 'PATCH':
        item_id = request.args.get('id')
        data = request.get_json()
        res = requests.patch(
            f'{SUPABASE_URL}/rest/v1/project_punchlist?id=eq.{item_id}',
            headers=SB_HEADERS,
            json=data
        )
        return jsonify({'ok': True}), 200, CORS_HEADERS

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
