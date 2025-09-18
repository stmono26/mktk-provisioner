#!/usr/bin/env python3
"""
Mikrotik RouterBoard Config Generator
A Flask web application for generating RouterOS configuration files
"""

from flask import Flask, render_template, request, send_from_directory, jsonify
import os

app = Flask(__name__)

# Ensure config directory exists
os.makedirs('configs', exist_ok=True)

@app.route('/')
def index():
    """Main configuration interface"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate RouterOS configuration based on parameters"""
    data = request.form
    mac = data.get('mac', '').replace(':', '').lower()
    lan_ip = data.get('lan_ip', '')
    if not mac or not lan_ip:
        return jsonify({'error': 'MAC and LAN IP required'}), 400
    
    try:
        # Read LAN IP snippet and substitute
        with open('snippets/lan_ip.rsc') as f:
            snippet = f.read().replace('<LAN_IP>', lan_ip)
        
        config_path = os.path.join('configs', f'{mac}.rsc')
        with open(config_path, 'w') as f:
            f.write(snippet)
        
        return jsonify({'success': True, 'mac': mac, 'config_url': f'/config/{mac}.rsc'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/config/<mac>.rsc')
def serve_config(mac):
    """Serve RouterOS configuration files"""
    return send_from_directory('configs', f'{mac}.rsc', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
