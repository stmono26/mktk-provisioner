#!/usr/bin/env python3
"""
Mikrotik RouterBoard Provisioner
A Flask web application for RouterOS configuration management and serving
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import json
import logging
import os
from datetime import datetime
import socket
import threading
import time

# Import our custom modules
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
config_generator = ConfigGenerator()
status_manager = StatusManager()

# Ensure config directory exists
os.makedirs('configs', exist_ok=True)

# In-memory storage for configuration sessions
config_sessions = {}

def get_server_ip():
    """Get the server's IP address for generating fetch commands"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"

@app.route('/')
def index():
    """Main configuration interface"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_config():
    """Generate RouterOS configuration based on parameters"""
    try:
        data = request.get_json()
        
        # Create configuration session
        session_id = f"config_{int(time.time())}"
        config_sessions[session_id] = {
            'config_type': data.get('config_type', 'base'),
            'identifier': data.get('identifier', 'default'),
            'parameters': data,
            'status': 'started',
            'created_at': datetime.now().isoformat()
        }
        
        # Start configuration generation in background thread
        thread = threading.Thread(
            target=generate_config_async,
            args=(session_id, config_sessions[session_id])
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'session_id': session_id}), 200
        
    except Exception as e:
        logger.error(f"Error starting configuration generation: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_config_async(session_id: str, session_data: dict):
    """Asynchronous configuration generation with real-time status updates"""
    try:
        config_type = session_data['config_type']
        identifier = session_data['identifier']
        parameters = session_data['parameters']
        
        # Step 1: Initialize
        status_manager.update_status(session_id, "Starting configuration generation...")
        
        # Step 2: Generate configuration
        if config_type == 'base':
            status_manager.update_status(session_id, "Generating base RouterOS configuration...")
            server_ip = get_server_ip()
            config_content = config_generator.generate_base_config(server_ip)
            filename = 'base_config.rsc'
        else:
            status_manager.update_status(session_id, f"Generating personalized configuration for: {identifier}")
            config_content = config_generator.generate_personalized_config(identifier, parameters)
            filename = f'{identifier}_config.rsc'
        
        # Step 3: Save configuration
        status_manager.update_status(session_id, f"Saving configuration file: {filename}")
        config_path = os.path.join('configs', filename)
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Step 4: Generate fetch commands
        status_manager.update_status(session_id, "Generating RouterOS fetch commands...")
        server_ip = get_server_ip()
        fetch_commands = generate_fetch_commands(server_ip, filename)
        
        # Step 5: Complete
        config_sessions[session_id].update({
            'filename': filename,
            'config_url': f'http://{server_ip}:5000/config/{filename}',
            'fetch_commands': fetch_commands,
            'status': 'completed'
        })
        
        status_manager.update_status(
            session_id, 
            f"Configuration generated successfully: {filename}", 
            "success"
        )
        
        logger.info(f"Configuration generation completed for session: {session_id}")
        
    except Exception as e:
        logger.error(f"Error in configuration generation: {str(e)}")
        status_manager.update_status(session_id, f"Configuration generation failed: {str(e)}", "error")
        config_sessions[session_id]['status'] = 'error'

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get configuration generation status for a session"""
    status = status_manager.get_status(session_id)
    if session_id in config_sessions:
        # Merge session data with status
        session_data = config_sessions[session_id].copy()
        if status:
            session_data.update(status)
        return jsonify(session_data)
    return jsonify(status or {'error': 'Session not found'})

@app.route('/status/stream/<session_id>')
def status_stream(session_id):
    """Server-Sent Events stream for real-time status updates"""
    def generate():
        last_update = 0
        while True:
            status = status_manager.get_status(session_id)
            session_data = config_sessions.get(session_id, {})
            
            if status and status.get('last_update', 0) > last_update:
                last_update = status['last_update']
                # Merge status with session data
                response_data = session_data.copy()
                response_data.update(status)
                yield f"data: {json.dumps(response_data)}\n\n"
            
            # Break if completed or error
            if status and status.get('current_type') in ['success', 'error']:
                break
                
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')

def generate_fetch_commands(server_ip, filename):
    """Generate RouterOS commands for technicians to copy/paste"""
    base_url = f"http://{server_ip}:5000/config/{filename}"
    
    return {
        'fetch_command': f'/tool fetch url="{base_url}"',
        'import_command': f'/import file-name={filename}',
        'combined_command': f'/tool fetch url="{base_url}"; :delay 2; /import file-name={filename}',
        'winbox_steps': [
            f'1. Open Tools > Fetch',
            f'2. URL: {base_url}',
            f'3. Click Start',
            f'4. Open New Terminal',
            f'5. Type: /import file-name={filename}',
            f'6. Press Enter'
        ]
    }

@app.route('/config/<filename>')
def serve_config(filename):
    """Serve RouterOS configuration files"""
    try:
        config_path = os.path.join('configs', filename)
        
        # If file doesn't exist, try to generate it
        if not os.path.exists(config_path):
            if filename == 'base_config.rsc':
                server_ip = get_server_ip()
                config_content = config_generator.generate_base_config(server_ip)
                with open(config_path, 'w') as f:
                    f.write(config_content)
            else:
                return "Configuration file not found", 404
        
        return send_from_directory('configs', filename, mimetype='text/plain')
        
    except Exception as e:
        logger.error(f"Error serving config {filename}: {str(e)}")
        return f"# Error serving configuration: {str(e)}", 500

@app.route('/configs')
def list_configs():
    """List all available configuration files"""
    try:
        config_files = []
        configs_dir = 'configs'
        
        if os.path.exists(configs_dir):
            for filename in os.listdir(configs_dir):
                if filename.endswith('.rsc'):
                    file_path = os.path.join(configs_dir, filename)
                    stat = os.stat(file_path)
                    config_files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'download_url': f'/config/{filename}'
                    })
        
        return jsonify({
            'server_ip': get_server_ip(),
            'config_files': config_files
        })
        
    except Exception as e:
        logger.error(f"Error listing configs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sessions')
def list_sessions():
    """List all configuration sessions (for debugging/monitoring)"""
    return jsonify({
        'active_sessions': len(config_sessions),
        'sessions': config_sessions
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Mikrotik RouterBoard Configuration Server")
    server_ip = get_server_ip()
    logger.info(f"Server IP: {server_ip}")
    logger.info(f"Base config URL: http://{server_ip}:5000/config/base_config.rsc")
    
    # Generate base config on startup
    try:
        config_generator.generate_base_config(server_ip)
        logger.info("Base configuration generated successfully")
    except Exception as e:
        logger.error(f"Error generating base config: {e}")
    
    # Run Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
