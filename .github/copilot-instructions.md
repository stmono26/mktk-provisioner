<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Mikrotik RouterBoard Provisioner

This is a Flask web application for automated Mikrotik RouterBoard provisioning. The application:

- Provides a web interface for entering router configuration parameters
- Automatically discovers routers on the network using MAC address resolution
- Uses SSH to send initial configuration commands to RouterOS devices
- Serves RouterOS configuration files (.rsc) for both base and personalized setups
- Provides real-time status updates during the provisioning process

## Key Components

- **Network Discovery**: Uses arp-scan to resolve MAC addresses to IP addresses
- **SSH Automation**: Uses paramiko for secure SSH connections to RouterOS devices
- **Configuration Generation**: Creates RouterOS scripts with proper syntax
- **Real-time Updates**: Uses Server-Sent Events for live status updates
- **Modular Design**: Separate modules for network, SSH, and configuration operations

## Development Guidelines

- Follow RouterOS script syntax for .rsc files
- Handle network and SSH errors gracefully
- Use proper logging throughout the application
- Keep the code modular and extensible for future parameters
- Ensure compatibility with Python 3.11+ on Debian 12/Raspberry Pi
