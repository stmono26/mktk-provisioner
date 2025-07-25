"""
SSH Operations Module
Handles SSH connections and command execution on RouterOS devices
"""

import paramiko
import logging
import socket
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SSHManager:
    def __init__(self):
        self.default_username = 'admin'
        self.connection_timeout = 10
        self.command_timeout = 30
    
    def execute_command(self, host: str, command: str, password: str = '') -> Dict[str, any]:
        """
        Execute a command on RouterOS device via SSH
        
        Args:
            host: Router IP address
            command: RouterOS command to execute
            password: SSH password (empty for default access)
            
        Returns:
            Dictionary with success status, output, and error information
        """
        result = {
            'success': False,
            'output': '',
            'error': '',
            'host': host,
            'command': command
        }
        
        ssh_client = None
        
        try:
            logger.info(f"Attempting SSH connection to {host}")
            
            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try connection with provided password
            try:
                ssh_client.connect(
                    hostname=host,
                    port=22,
                    username=self.default_username,
                    password=password,
                    timeout=self.connection_timeout,
                    look_for_keys=False,
                    allow_agent=False
                )
                logger.info(f"SSH connected to {host} with provided password")
                
            except paramiko.AuthenticationException:
                # Try with empty password for default RouterOS setup
                if password:  # Only try empty password if we haven't already
                    logger.info(f"Trying empty password for {host}")
                    ssh_client.connect(
                        hostname=host,
                        port=22,
                        username=self.default_username,
                        password='',
                        timeout=self.connection_timeout,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    logger.info(f"SSH connected to {host} with empty password")
                else:
                    raise
            
            # Execute command
            logger.info(f"Executing command on {host}: {command}")
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=self.command_timeout)
            
            # Get command output
            output = stdout.read().decode('utf-8').strip()
            error_output = stderr.read().decode('utf-8').strip()
            exit_code = stdout.channel.recv_exit_status()
            
            result['output'] = output
            result['error'] = error_output
            result['exit_code'] = exit_code
            
            if exit_code == 0:
                result['success'] = True
                logger.info(f"Command executed successfully on {host}")
                if output:
                    logger.debug(f"Command output: {output}")
            else:
                result['success'] = False
                logger.warning(f"Command failed on {host} with exit code {exit_code}")
                if error_output:
                    logger.warning(f"Command error: {error_output}")
            
        except paramiko.AuthenticationException as e:
            error_msg = f"SSH authentication failed for {host}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            
        except paramiko.SSHException as e:
            error_msg = f"SSH error connecting to {host}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            
        except socket.timeout:
            error_msg = f"SSH connection timeout to {host}"
            logger.error(error_msg)
            result['error'] = error_msg
            
        except socket.error as e:
            error_msg = f"Socket error connecting to {host}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error executing SSH command on {host}: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            
        finally:
            if ssh_client:
                try:
                    ssh_client.close()
                    logger.debug(f"SSH connection to {host} closed")
                except Exception:
                    pass
        
        return result
    
    def test_ssh_connection(self, host: str, password: str = '') -> bool:
        """
        Test SSH connectivity to a RouterOS device
        
        Args:
            host: Router IP address
            password: SSH password
            
        Returns:
            True if connection successful, False otherwise
        """
        result = self.execute_command(host, '/system identity print', password)
        return result['success']
    
    def get_router_identity(self, host: str, password: str = '') -> Optional[str]:
        """
        Get RouterOS device identity
        
        Args:
            host: Router IP address
            password: SSH password
            
        Returns:
            Router identity string or None if failed
        """
        result = self.execute_command(host, '/system identity print', password)
        
        if result['success'] and result['output']:
            # Parse identity from output
            # RouterOS identity output format: "name: RouterBoardName"
            lines = result['output'].split('\n')
            for line in lines:
                if 'name:' in line:
                    return line.split('name:')[1].strip()
        
        return None
    
    def send_config_fetch_command(self, host: str, server_ip: str, config_file: str, password: str = '') -> Dict[str, any]:
        """
        Send command to fetch configuration file from server
        
        Args:
            host: Router IP address
            server_ip: Provisioning server IP
            config_file: Configuration file name (e.g., 'base.rsc')
            password: SSH password
            
        Returns:
            Command execution result
        """
        fetch_url = f"http://{server_ip}:5000/config/{config_file}"
        command = f"/tool fetch url={fetch_url}"
        
        logger.info(f"Sending config fetch command to {host}: {command}")
        return self.execute_command(host, command, password)
    
    def execute_config_script(self, host: str, script_name: str, password: str = '') -> Dict[str, any]:
        """
        Execute a downloaded RouterOS script
        
        Args:
            host: Router IP address
            script_name: Name of the script file to execute
            password: SSH password
            
        Returns:
            Command execution result
        """
        command = f"/import {script_name}"
        
        logger.info(f"Executing config script on {host}: {command}")
        return self.execute_command(host, command, password)
    
    def wait_for_router_reboot(self, host: str, max_wait_time: int = 120) -> bool:
        """
        Wait for router to reboot and become accessible again
        
        Args:
            host: Router IP address
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            True if router becomes accessible, False if timeout
        """
        logger.info(f"Waiting for router {host} to reboot...")
        
        start_time = time.time()
        
        # Wait for router to go down first
        time.sleep(10)
        
        while time.time() - start_time < max_wait_time:
            try:
                # Try to connect
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(
                    hostname=host,
                    port=22,
                    username=self.default_username,
                    password='',
                    timeout=5,
                    look_for_keys=False,
                    allow_agent=False
                )
                ssh_client.close()
                
                logger.info(f"Router {host} is accessible after reboot")
                return True
                
            except Exception:
                time.sleep(5)
                continue
        
        logger.warning(f"Timeout waiting for router {host} to reboot")
        return False
