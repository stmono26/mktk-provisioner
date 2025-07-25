"""
Network Discovery Module
Handles network scanning and MAC address resolution
"""

import subprocess
import socket
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class NetworkDiscovery:
    def __init__(self):
        self.server_ip = self._detect_server_ip()
        self.network_subnet = self._get_network_subnet()
    
    def _detect_server_ip(self) -> str:
        """Detect the server's primary IP address"""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                logger.info(f"Detected server IP: {ip}")
                return ip
        except Exception as e:
            logger.error(f"Error detecting server IP: {str(e)}")
            return "127.0.0.1"
    
    def _get_network_subnet(self) -> str:
        """Get the network subnet based on server IP"""
        try:
            ip_parts = self.server_ip.split('.')
            subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
            logger.info(f"Using network subnet: {subnet}")
            return subnet
        except Exception as e:
            logger.error(f"Error determining network subnet: {str(e)}")
            return "192.168.1.0/24"
    
    def get_server_ip(self) -> str:
        """Get the server's IP address"""
        return self.server_ip
    
    def find_router_by_mac(self, mac_address: str) -> Optional[str]:
        """
        Find router IP address by MAC address using arp-scan
        
        Args:
            mac_address: Router's MAC address (format: XX:XX:XX:XX:XX:XX)
            
        Returns:
            Router IP address if found, None otherwise
        """
        try:
            # Normalize MAC address format
            mac_address = self._normalize_mac_address(mac_address)
            
            logger.info(f"Scanning network {self.network_subnet} for MAC: {mac_address}")
            
            # First try arp-scan if available
            router_ip = self._scan_with_arp_scan(mac_address)
            
            if router_ip:
                return router_ip
            
            # Fallback to ping sweep + arp table
            router_ip = self._scan_with_ping_and_arp(mac_address)
            
            return router_ip
            
        except Exception as e:
            logger.error(f"Error finding router by MAC {mac_address}: {str(e)}")
            return None
    
    def _normalize_mac_address(self, mac: str) -> str:
        """Normalize MAC address to XX:XX:XX:XX:XX:XX format"""
        # Remove any separators and convert to uppercase
        mac_clean = re.sub(r'[:-]', '', mac.upper())
        
        # Add colons every 2 characters
        if len(mac_clean) == 12:
            return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])
        else:
            raise ValueError(f"Invalid MAC address format: {mac}")
    
    def _scan_with_arp_scan(self, mac_address: str) -> Optional[str]:
        """Use arp-scan to find device by MAC address"""
        try:
            # Try arp-scan command
            cmd = ['arp-scan', '--local', '--plain']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse arp-scan output
                for line in result.stdout.strip().split('\n'):
                    if mac_address.lower() in line.lower():
                        # Extract IP address (first column)
                        ip_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)', line.strip())
                        if ip_match:
                            ip = ip_match.group(1)
                            logger.info(f"Found router at IP {ip} via arp-scan")
                            return ip
            else:
                logger.warning(f"arp-scan failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning("arp-scan timeout")
        except FileNotFoundError:
            logger.warning("arp-scan not found, falling back to ping sweep")
        except Exception as e:
            logger.error(f"Error with arp-scan: {str(e)}")
        
        return None
    
    def _scan_with_ping_and_arp(self, mac_address: str) -> Optional[str]:
        """Fallback method using ping sweep and ARP table lookup"""
        try:
            logger.info("Using ping sweep + ARP table fallback method")
            
            # Get network base (e.g., 192.168.1)
            ip_parts = self.server_ip.split('.')
            network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
            
            # Ping sweep to populate ARP table
            ping_processes = []
            for i in range(1, 255):
                ip = f"{network_base}.{i}"
                try:
                    # Use ping with short timeout
                    proc = subprocess.Popen(
                        ['ping', '-c', '1', '-W', '1', ip],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    ping_processes.append(proc)
                except Exception:
                    continue
            
            # Wait for ping processes to complete (with timeout)
            for proc in ping_processes:
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            
            # Check ARP table
            return self._check_arp_table(mac_address)
            
        except Exception as e:
            logger.error(f"Error with ping sweep: {str(e)}")
            return None
    
    def _check_arp_table(self, mac_address: str) -> Optional[str]:
        """Check system ARP table for MAC address"""
        try:
            # Try different ARP table commands
            arp_commands = [
                ['arp', '-a'],
                ['ip', 'neigh', 'show'],
                ['cat', '/proc/net/arp']
            ]
            
            for cmd in arp_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # Search for MAC address in output
                        for line in result.stdout.split('\n'):
                            if mac_address.lower() in line.lower():
                                # Extract IP address using regex
                                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    logger.info(f"Found router at IP {ip} via ARP table")
                                    return ip
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking ARP table: {str(e)}")
        
        return None
    
    def test_connectivity(self, ip_address: str) -> bool:
        """Test if an IP address is reachable"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', ip_address],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error testing connectivity to {ip_address}: {str(e)}")
            return False
