import pymongo
from pymongo import MongoClient
from typing import Dict, List, Optional
import threading
import time

class MongoDBReader:
    """MongoDB data reader for BotiBot sensor data."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.collection = None
        self.running = False
        self.callbacks = []
        self.monitor_thread = None
        self.last_data = None
        
    def connect(self) -> bool:
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client["botibot"]
            self.collection = self.db["data"]
            
            # Test connection
            self.client.admin.command('ping')
            print("✓ Connected to MongoDB Atlas")
            return True
            
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            return False
    
    def get_latest_data(self) -> Optional[Dict]:
        """Get the most recent sensor data."""
        try:
            if not self.collection:
                return None
                
            # Get the latest document
            latest = self.collection.find_one(sort=[("_id", -1)])
            
            if latest:
                # Convert to BotiBot format
                formatted_data = {
                    'temperature': {
                        'value': latest.get('temperature', 0),
                        'unit': '°C',
                        'status': self._get_temp_status(latest.get('temperature', 0)),
                        'color': self._get_temp_color(latest.get('temperature', 0))
                    },
                    'heart_rate': {
                        'value': latest.get('pulse_rate', 0),
                        'unit': 'bpm',
                        'status': self._get_heart_rate_status(latest.get('pulse_rate', 0)),
                        'color': self._get_heart_rate_color(latest.get('pulse_rate', 0))
                    },
                    'alcohol': {
                        'value': latest.get('alcohol_percentage', 0),
                        'unit': '%',
                        'status': self._get_alcohol_status(latest.get('alcohol_percentage', 0)),
                        'color': self._get_alcohol_color(latest.get('alcohol_percentage', 0))
                    }
                }
                return formatted_data
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def get_recent_data(self, limit: int = 10) -> List[Dict]:
        """Get recent sensor data entries."""
        try:
            if not self.collection:
                return []
                
            cursor = self.collection.find().sort([("_id", -1)]).limit(limit)
            return list(cursor)
            
        except Exception as e:
            print(f"Error fetching recent data: {e}")
            return []
    
    def _get_temp_status(self, temp: float) -> str:
        """Get temperature status."""
        if temp < 36.0:
            return "Low"
        elif temp > 37.5:
            return "High"
        else:
            return "Normal"
    
    def _get_temp_color(self, temp: float) -> str:
        """Get temperature color."""
        if temp < 36.0 or temp > 37.5:
            return "#F9A826"  # Warning
        else:
            return "#2E7D32"  # Success
    
    def _get_heart_rate_status(self, hr: int) -> str:
        """Get heart rate status."""
        if hr < 60:
            return "Low"
        elif hr > 100:
            return "High"
        else:
            return "Normal"
    
    def _get_heart_rate_color(self, hr: int) -> str:
        """Get heart rate color."""
        if hr < 60 or hr > 100:
            return "#F9A826"  # Warning
        else:
            return "#2E7D32"  # Success
    
    def _get_alcohol_status(self, alcohol: float) -> str:
        """Get alcohol status."""
        if alcohol > 0.08:
            return "High"
        elif alcohol > 0.05:
            return "Moderate"
        elif alcohol > 0.0:
            return "Low"
        else:
            return "None"
    
    def _get_alcohol_color(self, alcohol: float) -> str:
        """Get alcohol color."""
        if alcohol > 0.08:
            return "#C62828"  # Danger
        elif alcohol > 0.05:
            return "#F9A826"  # Warning
        elif alcohol > 0.0:
            return "#3E5C76"  # Secondary
        else:
            return "#2E7D32"  # Success
    
    def add_callback(self, callback):
        """Add callback for data updates."""
        self.callbacks.append(callback)
    
    def start_monitoring(self):
        """Start monitoring for data changes."""
        if not self.connect():
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        if self.client:
            self.client.close()
    
    def _monitor_loop(self):
        """Monitor for data changes."""
        while self.running:
            try:
                current_data = self.get_latest_data()
                
                if current_data and current_data != self.last_data:
                    self.last_data = current_data
                    
                    # Trigger callbacks
                    for callback in self.callbacks:
                        try:
                            callback(current_data)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(5)  # Wait longer on error
