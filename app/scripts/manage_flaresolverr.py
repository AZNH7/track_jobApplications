#!/usr/bin/env python3
"""
FlareSolverr Management Script
Monitors, maintains, and restarts FlareSolverr to prevent resource failures.
"""

import requests
import json
import time
import subprocess
import sys
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/flaresolverr_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlareSolverrManager:
    """Manages FlareSolverr service to prevent failures and resource exhaustion."""
    
    def __init__(self, flaresolverr_url: str = None):
        # Get configuration
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        flaresolverr_config = config_manager.get_setting('flaresolverr', {})
        
        self.flaresolverr_url = flaresolverr_url or flaresolverr_config.get('url', 'http://localhost:8191/v1')
        self.container_name = "job-tracker-flaresolverr"
        self.stats = {
            'restarts': 0,
            'last_restart': None,
            'health_checks': 0,
            'failed_checks': 0,
            'sessions_cleaned': 0
        }
        
    def check_health(self) -> Tuple[bool, Dict]:
        """Check FlareSolverr health and return status with details."""
        try:
            response = requests.get(f"{self.flaresolverr_url.replace('/v1', '/health')}", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def get_sessions(self) -> List[str]:
        """Get list of active sessions."""
        try:
            response = requests.post(
                self.flaresolverr_url,
                json={"cmd": "sessions.list"},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    return result.get("sessions", [])
            return []
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            return []
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a specific session."""
        try:
            response = requests.post(
                self.flaresolverr_url,
                json={
                    "cmd": "sessions.destroy",
                    "session": session_id
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error destroying session {session_id}: {e}")
            return False
    
    def clean_old_sessions(self, max_age_minutes: int = 30) -> int:
        """Clean sessions older than specified age."""
        sessions = self.get_sessions()
        cleaned = 0
        
        for session_id in sessions:
            # For now, we'll clean all sessions as a safety measure
            # In a more sophisticated version, you'd track session creation times
            if self.destroy_session(session_id):
                cleaned += 1
                logger.info(f"Cleaned session: {session_id}")
        
        self.stats['sessions_cleaned'] += cleaned
        return cleaned
    
    def restart_container(self) -> bool:
        """Restart the FlareSolverr container."""
        try:
            logger.warning("Restarting FlareSolverr container...")
            
            # Stop the container
            subprocess.run([
                "docker", "stop", self.container_name
            ], check=True, timeout=30)
            
            # Wait a moment
            time.sleep(5)
            
            # Start the container
            subprocess.run([
                "docker", "start", self.container_name
            ], check=True, timeout=30)
            
            # Wait for it to be ready
            logger.info("Waiting for FlareSolverr to be ready...")
            for i in range(60):  # Wait up to 60 seconds
                time.sleep(1)
                healthy, _ = self.check_health()
                if healthy:
                    logger.info("FlareSolverr is ready!")
                    self.stats['restarts'] += 1
                    self.stats['last_restart'] = datetime.now()
                    return True
            
            logger.error("FlareSolverr failed to start properly")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout while restarting FlareSolverr")
            return False
        except Exception as e:
            logger.error(f"Error restarting FlareSolverr: {e}")
            return False
    
    def get_container_stats(self) -> Dict:
        """Get Docker container statistics."""
        try:
            result = subprocess.run([
                "docker", "stats", self.container_name, "--no-stream", "--format", "json"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                stats = json.loads(result.stdout.strip())
                return {
                    'cpu_percent': stats.get('CPUPerc', '0%').rstrip('%'),
                    'memory_usage': stats.get('MemUsage', '0B / 0B'),
                    'memory_percent': stats.get('MemPerc', '0%').rstrip('%'),
                    'network_io': stats.get('NetIO', '0B / 0B'),
                    'block_io': stats.get('BlockIO', '0B / 0B')
                }
        except Exception as e:
            logger.error(f"Error getting container stats: {e}")
        
        return {}
    
    def should_restart(self) -> bool:
        """Determine if FlareSolverr should be restarted based on various criteria."""
        # Check if it's been restarted recently (within last 5 minutes)
        if (self.stats['last_restart'] and 
            datetime.now() - self.stats['last_restart'] < timedelta(minutes=5)):
            return False
        
        # Check health
        healthy, details = self.check_health()
        if not healthy:
            logger.warning(f"FlareSolverr unhealthy: {details}")
            return True
        
        # Check container stats
        stats = self.get_container_stats()
        if stats:
            try:
                cpu_percent = float(stats.get('cpu_percent', 0))
                memory_percent = float(stats.get('memory_percent', 0))
                
                # Restart if CPU or memory usage is too high
                if cpu_percent > 80 or memory_percent > 85:
                    logger.warning(f"High resource usage - CPU: {cpu_percent}%, Memory: {memory_percent}%")
                    return True
            except (ValueError, TypeError):
                pass
        
        # Check session count
        sessions = self.get_sessions()
        if len(sessions) > 10:  # Too many sessions
            logger.warning(f"Too many sessions: {len(sessions)}")
            return True
        
        return False
    
    def monitor_and_maintain(self, check_interval: int = 30):
        """Main monitoring loop."""
        logger.info("Starting FlareSolverr monitoring...")
        
        while True:
            try:
                self.stats['health_checks'] += 1
                
                # Check if restart is needed
                if self.should_restart():
                    if self.restart_container():
                        logger.info("FlareSolverr restarted successfully")
                    else:
                        logger.error("Failed to restart FlareSolverr")
                        self.stats['failed_checks'] += 1
                else:
                    # Regular maintenance
                    sessions = self.get_sessions()
                    if len(sessions) > 5:
                        cleaned = self.clean_old_sessions()
                        if cleaned > 0:
                            logger.info(f"Cleaned {cleaned} old sessions")
                
                # Log stats periodically
                if self.stats['health_checks'] % 20 == 0:  # Every 10 minutes
                    self.log_stats()
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.stats['failed_checks'] += 1
                time.sleep(check_interval)
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_container_stats()
        sessions = self.get_sessions()
        
        logger.info(f"Stats - Restarts: {self.stats['restarts']}, "
                   f"Health checks: {self.stats['health_checks']}, "
                   f"Failed: {self.stats['failed_checks']}, "
                   f"Sessions: {len(sessions)}, "
                   f"CPU: {stats.get('cpu_percent', 'N/A')}%, "
                   f"Memory: {stats.get('memory_percent', 'N/A')}%")
    
    def emergency_cleanup(self):
        """Emergency cleanup - restart and clean everything."""
        logger.warning("Performing emergency cleanup...")
        
        # Clean all sessions
        sessions = self.get_sessions()
        for session_id in sessions:
            self.destroy_session(session_id)
        
        # Restart container
        self.restart_container()
        
        logger.info("Emergency cleanup completed")

def main():
    """Main function."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        manager = FlareSolverrManager()
        
        if command == "monitor":
            check_interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            manager.monitor_and_maintain(check_interval)
        elif command == "restart":
            manager.restart_container()
        elif command == "cleanup":
            manager.emergency_cleanup()
        elif command == "status":
            healthy, details = manager.check_health()
            sessions = manager.get_sessions()
            stats = manager.get_container_stats()
            
            print(f"Health: {'✅' if healthy else '❌'}")
            print(f"Active Sessions: {len(sessions)}")
            print(f"Container Stats: {stats}")
            if not healthy:
                print(f"Error: {details}")
        elif command == "clean-sessions":
            cleaned = manager.clean_old_sessions()
            print(f"Cleaned {cleaned} sessions")
        else:
            print("Usage: python manage_flaresolverr.py [monitor|restart|cleanup|status|clean-sessions]")
    else:
        print("Usage: python manage_flaresolverr.py [monitor|restart|cleanup|status|clean-sessions]")

if __name__ == "__main__":
    main() 