#!/usr/bin/env python3
"""
Mikrotik RouterBoard Provisioner
A Flask web application for automated RouterOS device provisioning
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import json
import logging
import os
from datetime import datetime
import threading
import time

# Import our custom modules
from modules.network_discovery import NetworkDiscovery
from modules.ssh_operations import SSHManager
from modules.config_generator import ConfigGenerator
from modules.status_manager import StatusManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('provisioner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize components
network_discovery = NetworkDiscovery()
ssh_manager = SSHManager()
config_generator = ConfigGenerator()
status_manager = StatusManager()

# In-memory storage for provisioning sessions
provisioning_sessions = {}

@app.route('/')
def index():
    """Main provisioning interface"""
    return render_template('index.html')

@app.route('/provision', methods=['POST'])
def provision_router():
    """Handle router provisioning request"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('mac_address'):
            return jsonify({'error': 'MAC address is required'}), 400
        
        # Create provisioning session
        session_id = f"session_{int(time.time())}"
        provisioning_sessions[session_id] = {
            'mac_address': data['mac_address'],
            'ssh_password': data.get('ssh_password', ''),
            'lan_ip': data.get('lan_ip', '192.168.1.1/24'),
            'pppoe_username': data.get('pppoe_username', ''),
            'pppoe_password': data.get('pppoe_password', ''),
            'additional_params': data.get('additional_params', {}),
            'status': 'started',
            'created_at': datetime.now().isoformat()
        }
        
        # Start provisioning in background thread
        thread = threading.Thread(
            target=provision_router_async,
            args=(session_id, provisioning_sessions[session_id])
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'session_id': session_id}), 200
        
    except Exception as e:
        logger.error(f"Error starting provisioning: {str(e)}")
        return jsonify({'error': str(e)}), 500

def provision_router_async(session_id, session_data):
    """Asynchronous router provisioning workflow"""
    try:
        mac_address = session_data['mac_address']
        ssh_password = session_data['ssh_password']
        
        # Step 1: Network discovery
        status_manager.update_status(session_id, "Scanning network for router...")
        logger.info(f"Starting network discovery for MAC: {mac_address}")
        
        router_ip = network_discovery.find_router_by_mac(mac_address)
        
        if not router_ip:
            status_manager.update_status(session_id, f"Router with MAC {mac_address} not found on network", "error")
            return
        
        logger.info(f"Found router at IP: {router_ip}")
        status_manager.update_status(session_id, f"Router found at IP: {router_ip}")
        
        # Step 2: SSH connection and base config delivery
        status_manager.update_status(session_id, "Connecting to router via SSH...")
        
        server_ip = network_discovery.get_server_ip()
        fetch_command = f"/tool fetch url=http://{server_ip}:5000/config/base.rsc"
        
        ssh_result = ssh_manager.execute_command(router_ip, fetch_command, ssh_password)
        
        if not ssh_result['success']:
            status_manager.update_status(session_id, f"SSH connection failed: {ssh_result['error']}", "error")
            return
        
        status_manager.update_status(session_id, "Base configuration sent successfully")
        
        # Step 3: Generate personalized config
        status_manager.update_status(session_id, "Generating personalized configuration...")
        
        config_generator.generate_personalized_config(mac_address, session_data)
        
        # Step 4: Wait for personalized config fetch
        status_manager.update_status(session_id, "Waiting for router to fetch personalized configuration...")
        
        # Wait a bit for the router to process and potentially fetch personalized config
        time.sleep(5)
        
        status_manager.update_status(session_id, "Provisioning completed successfully!", "success")
        logger.info(f"Provisioning completed for MAC: {mac_address}")
        
    except Exception as e:
        logger.error(f"Error in provisioning workflow: {str(e)}")
        status_manager.update_status(session_id, f"Provisioning failed: {str(e)}", "error")

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get provisioning status for a session"""
    return jsonify(status_manager.get_status(session_id))

@app.route('/status/stream/<session_id>')
def status_stream(session_id):
    """Server-Sent Events stream for real-time status updates"""
    def generate():
        last_update = 0
        while True:
            status = status_manager.get_status(session_id)
            if status and status.get('last_update', 0) > last_update:
                last_update = status['last_update']
                yield f"data: {json.dumps(status)}\n\n"
            
            # Break if completed or error
            if status and status.get('type') in ['success', 'error']:
                break
                
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/config/base.rsc')
def serve_base_config():
    """Serve base RouterOS configuration"""
    try:
        server_ip = network_discovery.get_server_ip()
        base_config = config_generator.generate_base_config(server_ip)
        
        response = Response(base_config, mimetype='text/plain')
        response.headers['Content-Disposition'] = 'attachment; filename=base.rsc'
        logger.info("Served base configuration")
        return response
        
    except Exception as e:
        logger.error(f"Error serving base config: {str(e)}")
        return f"# Error generating base config: {str(e)}", 500

@app.route('/config/<mac_address>.rsc')
def serve_personalized_config(mac_address):
    """Serve personalized RouterOS configuration for specific MAC address"""
    try:
        personalized_config = config_generator.get_personalized_config(mac_address)
        
        if not personalized_config:
            logger.warning(f"No personalized config found for MAC: {mac_address}")
            return "# No personalized configuration available", 404
        
        response = Response(personalized_config, mimetype='text/plain')
        response.headers['Content-Disposition'] = f'attachment; filename={mac_address}.rsc'
        logger.info(f"Served personalized configuration for MAC: {mac_address}")
        return response
        
    except Exception as e:
        logger.error(f"Error serving personalized config for {mac_address}: {str(e)}")
        return f"# Error generating personalized config: {str(e)}", 500

@app.route('/sessions')
def list_sessions():
    """List all provisioning sessions (for debugging/monitoring)"""
    return jsonify(provisioning_sessions)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Mikrotik RouterBoard Provisioner")
    logger.info(f"Server IP: {network_discovery.get_server_ip()}")
    
    # Run Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
