"""
Configuration Generator Module
Generates RouterOS configuration files (.rsc) for base and personalized setups
"""

import logging
import os
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigGenerator:
    def __init__(self):
        self.config_storage = {}  # In-memory storage for personalized configs
        self.config_dir = "configs"
        os.makedirs(self.config_dir, exist_ok=True)
    
    def generate_base_config(self, server_ip: str) -> str:
        """
        Generate base RouterOS configuration that will be fetched first
        
        Args:
            server_ip: IP address of the provisioning server
            
        Returns:
            RouterOS script content as string
        """
        config = f"""# Mikrotik RouterBoard Base Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Server IP: {server_ip}

# Set system identity temporarily
/system identity set name="RouterBoard-Provisioning"

# Configure basic system settings
/system clock set time-zone-name=Europe/Rome

# Enable SSH service (ensure it's available)
/ip service enable ssh
/ip service set ssh port=22

# VLAN Configuration
/interface vlan
add name=vlan835 vlan-id=835 interface=ether1

# PPPoE Configuration
/interface pppoe-client 
add name=pppoe-out1 interface=vlan835 service-name=internet disabled=yes

# Bridge Configuration
/interface bridge
add name=bridge disabled=no auto-mac=yes protocol-mode=rstp

# Add ether2-ether5 to bridge (keeping ether1 for WAN)
/interface bridge port
add bridge=bridge interface=ether2
add bridge=bridge interface=ether3
add bridge=bridge interface=ether4
add bridge=bridge interface=ether5

# Interface Lists
/interface list add name=WAN
/interface list add name=LAN

# Interface List Members
/interface list member add list=LAN interface=bridge
/interface list member add list=WAN interface=ether1

# IP Address Configuration
/ip address
add address=192.168.188.1/24 interface=bridge comment="LAN Network"

# IP Pool Configuration
/ip pool
add name=dhcp-pool ranges=192.168.188.20-192.168.188.30

# DHCP Server Configuration
/ip dhcp-server
add name=dhcp-server interface=bridge address-pool=dhcp-pool disabled=no

/ip dhcp-server network
add address=192.168.188.0/24 gateway=192.168.188.1 dns-server=192.168.188.1,8.8.8.8

# NAT Rules
/ip firewall nat 
add chain=srcnat out-interface-list=WAN ipsec-policy=out,none action=masquerade
add chain=dstnat protocol=tcp dst-port=48291 in-interface=pppoe-out1 action=dst-nat to-addresses=192.168.188.1 to-ports=48291 comment="WinBox"

# Default Firewall Rules
/ip firewall filter
add chain=input action=accept connection-state=established,related,untracked comment="defconf: accept established,related,untracked"
add chain=input protocol=tcp dst-port=48291 action=accept comment="WinBox"
add chain=input protocol=tcp dst-port=22 comment="Allow SSH"
add chain=input action=drop connection-state=invalid comment="defconf: drop invalid"
add chain=input action=accept protocol=icmp comment="defconf: accept ICMP"
add chain=input action=accept dst-address=127.0.0.1 comment="defconf: accept to local loopback (for CAPsMAN)"
add chain=input action=drop in-interface-list=!LAN comment="defconf: drop all not coming from LAN"
add chain=forward action=accept ipsec-policy=in,ipsec comment="defconf: accept in ipsec policy"
add chain=forward action=accept ipsec-policy=out,ipsec comment="defconf: accept out ipsec policy"
add chain=forward action=fasttrack-connection connection-state=established,related comment="defconf: fasttrack"
add chain=forward action=accept connection-state=established,related,untracked comment="defconf: accept established,related, untracked"
add chain=forward action=drop connection-state=invalid comment="defconf: drop invalid"
add chain=forward action=drop connection-state=new connection-nat-state=!dstnat in-interface-list=WAN comment="defconf: drop all from WAN not DSTNATed"

# Configure DNS
/ip dns set servers=8.8.8.8,8.8.4.4 allow-remote-requests=yes

# Create script to fetch personalized configuration
/system script add name="fetch-personalized-config" source={{
    :local macAddr [/interface ethernet get ether1 mac-address];
    :local serverIP "{server_ip}";
    :local configURL ("http://" . $serverIP . ":5000/config/" . $macAddr . ".rsc");
    
    :log info ("Fetching personalized config from: " . $configURL);
    
    :do {{
        /tool fetch url=$configURL;
        :delay 2s;
        /import file=($macAddr . ".rsc");
        :log info "Personalized configuration imported successfully";
    }} on-error={{
        :log error "Failed to fetch or import personalized configuration";
    }}
}}

# Schedule personalized config fetch (run after 30 seconds)
/system scheduler add name="fetch-personalized" start-time=startup interval=0 on-event="/system script run fetch-personalized-config"

# Create backup script for configuration
/system script add name="backup-config" source={{
    :local timestamp [/system clock get date];
    :local backupName ("backup-" . $timestamp);
    /system backup save name=$backupName;
    :log info ("Configuration backup saved as: " . $backupName);
}}

:log info "Base configuration applied successfully";
:log info "Personalized configuration will be fetched automatically";
"""
        
        logger.info("Generated base RouterOS configuration")
        return config
    
    def generate_personalized_config(self, mac_address: str, session_data: Dict) -> str:
        """
        Generate personalized RouterOS configuration for specific device
        
        Args:
            mac_address: Router's MAC address
            session_data: Provisioning session data with parameters
            
        Returns:
            RouterOS script content as string
        """
        lan_ip = session_data.get('lan_ip', '192.168.188.1/24')
        pppoe_username = session_data.get('pppoe_username', '')
        pppoe_password = session_data.get('pppoe_password', '')
        additional_params = session_data.get('additional_params', {})
        
        # Parse LAN IP and subnet
        if '/' in lan_ip:
            ip_address, subnet = lan_ip.split('/')
            network = self._calculate_network(ip_address, subnet)
        else:
            ip_address = lan_ip
            subnet = '24'
            network = self._calculate_network(ip_address, subnet)
        
        config = f"""# Mikrotik RouterBoard Personalized Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# MAC Address: {mac_address}
# LAN IP: {lan_ip}

# Set final system identity
/system identity set name="RouterBoard-{mac_address.replace(':', '')}"

# Configure PPPoE client with credentials
/interface pppoe-client set [find name=pppoe-out1] user="{pppoe_username}" password="{pppoe_password}" disabled=no

# Update LAN IP address if different from default
/ip address set [find interface=bridge] address={lan_ip}

# Update DHCP pool and server for new network
/ip pool set [find name=dhcp-pool] ranges={network[:-1]}{int(network.split('.')[-1]) + 20}-{network[:-1]}{int(network.split('.')[-1]) + 250}

/ip dhcp-server network set [find] address={network}/{subnet} gateway={ip_address} dns-server={ip_address},8.8.8.8,8.8.4.4

# Configure DNS
/ip dns set servers=8.8.8.8,8.8.4.4 allow-remote-requests=yes

# Update NAT rule for WinBox if different IP
/ip firewall nat set [find comment="WinBox"] to-addresses={ip_address}

# Configure NTP client
/system ntp client set enabled=yes primary-ntp=pool.ntp.org secondary-ntp=time.google.com

# Set timezone
/system clock set time-zone-name=Europe/Rome

# Enable bandwidth monitoring
/tool bandwidth-server set enabled=yes

# Configure SNMP (if requested)"""

        # Add additional parameters if provided
        if additional_params:
            config += "\n\n# Additional Configuration Parameters"
            
            # WiFi configuration
            if 'wifi_ssid' in additional_params and 'wifi_password' in additional_params:
                config += f"""
# WiFi Configuration
/interface wireless security-profiles
add name=wifi-security mode=wpa2 authentication-types=wpa2-psk wpa2-pre-shared-key="{additional_params['wifi_password']}"

/interface wireless
set [find default-name=wlan1] mode=ap-bridge ssid="{additional_params['wifi_ssid']}" security-profile=wifi-security disabled=no
"""
            
            # VLAN configuration
            if 'vlan_ids' in additional_params:
                vlan_ids = additional_params['vlan_ids'].split(',')
                for vlan_id in vlan_ids:
                    vlan_id = vlan_id.strip()
                    if vlan_id.isdigit():
                        config += f"""
/interface vlan add name=vlan-{vlan_id} vlan-id={vlan_id} interface=bridge
"""
            
            # QoS configuration
            if 'bandwidth_limit' in additional_params:
                config += f"""
# Bandwidth limitation
/queue simple add name="total-bandwidth" target=bridge max-limit={additional_params['bandwidth_limit']}
"""
            
            # Port forwarding rules
            if 'port_forwards' in additional_params:
                forwards = additional_params['port_forwards'].split(',')
                for forward in forwards:
                    forward = forward.strip()
                    if ':' in forward:
                        external_port, internal = forward.split(':')
                        if '.' in internal:  # Contains IP
                            internal_ip, internal_port = internal.rsplit('.', 1)
                            if internal_port.isdigit():
                                config += f"""
/ip firewall nat add chain=dstnat action=dst-nat protocol=tcp dst-port={external_port} to-addresses={internal_ip} to-ports={internal_port}
"""

        # Final configuration steps
        config += f"""

# Remove the personalized config fetch scheduler
/system scheduler remove [find name="fetch-personalized"]

# Create final backup
/system script run backup-config

# Log completion
:log info "Personalized configuration applied successfully for {mac_address}";
:log info "Router provisioning completed";

# Optional: Send notification to server (if webhook URL provided)
# /tool fetch url="http://SERVER_IP:5000/webhook/provision-complete" http-method=post http-data="mac={mac_address}&status=complete"
"""
        
        # Store configuration in memory
        self.config_storage[mac_address] = config
        
        # Also save to file for persistence
        config_file = os.path.join(self.config_dir, f"{mac_address}.rsc")
        try:
            with open(config_file, 'w') as f:
                f.write(config)
            logger.info(f"Saved personalized config to {config_file}")
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}")
        
        logger.info(f"Generated personalized configuration for MAC: {mac_address}")
        return config
    
    def get_personalized_config(self, mac_address: str) -> Optional[str]:
        """
        Retrieve personalized configuration for a MAC address
        
        Args:
            mac_address: Router's MAC address
            
        Returns:
            Configuration content or None if not found
        """
        # Check in-memory storage first
        if mac_address in self.config_storage:
            return self.config_storage[mac_address]
        
        # Check file storage
        config_file = os.path.join(self.config_dir, f"{mac_address}.rsc")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = f.read()
                # Cache in memory
                self.config_storage[mac_address] = config
                return config
            except Exception as e:
                logger.error(f"Error reading config file {config_file}: {str(e)}")
        
        logger.warning(f"No personalized config found for MAC: {mac_address}")
        return None
    
    def _calculate_network(self, ip_address: str, subnet: str) -> str:
        """
        Calculate network address from IP and subnet
        
        Args:
            ip_address: IP address (e.g., '192.168.1.1')
            subnet: Subnet mask as CIDR (e.g., '24')
            
        Returns:
            Network address (e.g., '192.168.1.0')
        """
        try:
            ip_parts = [int(x) for x in ip_address.split('.')]
            subnet_bits = int(subnet)
            
            # Calculate subnet mask
            mask = (0xffffffff >> (32 - subnet_bits)) << (32 - subnet_bits)
            mask_parts = [
                (mask >> 24) & 0xff,
                (mask >> 16) & 0xff,
                (mask >> 8) & 0xff,
                mask & 0xff
            ]
            
            # Calculate network address
            network_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
            
            return '.'.join(map(str, network_parts))
            
        except Exception as e:
            logger.error(f"Error calculating network address: {str(e)}")
            # Fallback to simple calculation
            ip_parts = ip_address.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0"
    
    def list_stored_configs(self) -> Dict[str, Dict]:
        """
        List all stored configurations with metadata
        
        Returns:
            Dictionary with MAC addresses as keys and metadata as values
        """
        configs = {}
        
        # Check memory storage
        for mac in self.config_storage:
            configs[mac] = {
                'source': 'memory',
                'generated_at': 'unknown'
            }
        
        # Check file storage
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.rsc'):
                    mac = filename[:-4]  # Remove .rsc extension
                    file_path = os.path.join(self.config_dir, filename)
                    
                    try:
                        stat = os.stat(file_path)
                        configs[mac] = {
                            'source': 'file',
                            'file_path': file_path,
                            'size': stat.st_size,
                            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
                    except Exception as e:
                        logger.error(f"Error reading file metadata for {filename}: {str(e)}")
        
        return configs
    
    def delete_config(self, mac_address: str) -> bool:
        """
        Delete stored configuration for a MAC address
        
        Args:
            mac_address: Router's MAC address
            
        Returns:
            True if deleted successfully, False otherwise
        """
        success = True
        
        # Remove from memory
        if mac_address in self.config_storage:
            del self.config_storage[mac_address]
            logger.info(f"Removed config from memory for MAC: {mac_address}")
        
        # Remove file
        config_file = os.path.join(self.config_dir, f"{mac_address}.rsc")
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
                logger.info(f"Removed config file: {config_file}")
            except Exception as e:
                logger.error(f"Error removing config file {config_file}: {str(e)}")
                success = False
        
        return success
