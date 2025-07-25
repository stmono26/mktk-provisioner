"""
Status Manager Module
Handles real-time status tracking for provisioning sessions
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StatusManager:
    def __init__(self):
        self.statuses = {}  # In-memory storage for session statuses
    
    def update_status(self, session_id: str, message: str, status_type: str = "info") -> None:
        """
        Update status for a provisioning session
        
        Args:
            session_id: Unique session identifier
            message: Status message
            status_type: Type of status ('info', 'success', 'error', 'warning')
        """
        timestamp = time.time()
        
        if session_id not in self.statuses:
            self.statuses[session_id] = {
                'session_id': session_id,
                'created_at': timestamp,
                'updates': []
            }
        
        status_update = {
            'timestamp': timestamp,
            'message': message,
            'type': status_type,
            'formatted_time': time.strftime('%H:%M:%S', time.localtime(timestamp))
        }
        
        self.statuses[session_id]['updates'].append(status_update)
        self.statuses[session_id]['last_update'] = timestamp
        self.statuses[session_id]['current_status'] = message
        self.statuses[session_id]['current_type'] = status_type
        
        logger.info(f"Status update for {session_id}: [{status_type.upper()}] {message}")
    
    def get_status(self, session_id: str) -> Optional[Dict]:
        """
        Get current status for a provisioning session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Status dictionary or None if session not found
        """
        if session_id in self.statuses:
            status = self.statuses[session_id].copy()
            
            # Add summary information
            status['total_updates'] = len(status['updates'])
            
            if status['updates']:
                status['duration'] = status['last_update'] - status['created_at']
                status['is_complete'] = status['current_type'] in ['success', 'error']
            else:
                status['duration'] = 0
                status['is_complete'] = False
            
            return status
        
        return None
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """
        Get all session statuses
        
        Returns:
            Dictionary of all session statuses
        """
        all_statuses = {}
        for session_id in self.statuses:
            all_statuses[session_id] = self.get_status(session_id)
        
        return all_statuses
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old session statuses
        
        Args:
            max_age_hours: Maximum age of sessions to keep (in hours)
            
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        sessions_to_remove = []
        
        for session_id, status in self.statuses.items():
            if current_time - status['created_at'] > max_age_seconds:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.statuses[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
        
        return len(sessions_to_remove)
    
    def get_session_progress(self, session_id: str) -> Dict:
        """
        Get progress information for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Progress information dictionary
        """
        status = self.get_status(session_id)
        
        if not status:
            return {'progress': 0, 'stage': 'unknown', 'is_complete': False}
        
        updates = status['updates']
        current_type = status.get('current_type', 'info')
        
        # Define expected stages
        expected_stages = [
            'started',
            'scanning',
            'found',
            'connecting',
            'sent',
            'generating',
            'waiting',
            'completed'
        ]
        
        # Determine current stage based on messages
        current_stage = 'unknown'
        progress = 0
        
        for update in updates:
            message = update['message'].lower()
            
            if 'scanning' in message:
                current_stage = 'scanning'
                progress = 20
            elif 'found' in message:
                current_stage = 'found'
                progress = 30
            elif 'connecting' in message:
                current_stage = 'connecting'
                progress = 40
            elif 'sent' in message or 'base configuration' in message:
                current_stage = 'sent'
                progress = 60
            elif 'generating' in message:
                current_stage = 'generating'
                progress = 70
            elif 'waiting' in message:
                current_stage = 'waiting'
                progress = 80
            elif 'completed' in message or current_type == 'success':
                current_stage = 'completed'
                progress = 100
            elif current_type == 'error':
                current_stage = 'error'
                # Keep previous progress for errors
        
        return {
            'progress': progress,
            'stage': current_stage,
            'is_complete': current_type in ['success', 'error'],
            'is_error': current_type == 'error'
        }
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.statuses:
            del self.statuses[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        
        return False
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """
        Get all currently active (non-completed) sessions
        
        Returns:
            Dictionary of active session statuses
        """
        active_sessions = {}
        
        for session_id, status in self.statuses.items():
            if not status.get('is_complete', False):
                active_sessions[session_id] = self.get_status(session_id)
        
        return active_sessions
    
    def get_completed_sessions(self) -> Dict[str, Dict]:
        """
        Get all completed sessions
        
        Returns:
            Dictionary of completed session statuses
        """
        completed_sessions = {}
        
        for session_id, status in self.statuses.items():
            current_status = self.get_status(session_id)
            if current_status and current_status.get('is_complete', False):
                completed_sessions[session_id] = current_status
        
        return completed_sessions
    
    def get_session_timeline(self, session_id: str) -> Optional[list]:
        """
        Get detailed timeline for a specific session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of timeline events or None if session not found
        """
        status = self.get_status(session_id)
        
        if not status:
            return None
        
        timeline = []
        
        for update in status['updates']:
            timeline_event = {
                'timestamp': update['timestamp'],
                'formatted_time': update['formatted_time'],
                'message': update['message'],
                'type': update['type'],
                'relative_time': update['timestamp'] - status['created_at']
            }
            timeline.append(timeline_event)
        
        return timeline
