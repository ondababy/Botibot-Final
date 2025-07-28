import json
import os
import threading
import time
from typing import Dict, Any, Optional, Callable

class DataReader:
    """Reads sensor data from mqtt_data.json and provides real-time updates."""
    
    def __init__(self, json_file_path: str = "/home/bsit/botibot.py/botibot/mqtt_data.json"):
        self.json_file_path = json_file_path
        self.last_data = {}
        self.callbacks = []
        self.running = False
        self.thread = None
        self.update_interval = 1.0  # Update every second
        
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback function to be called when data updates."""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove a callback function."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get the latest sensor data."""
        try:
            if os.path.exists(self.json_file_path):
                with open(self.json_file_path, 'r') as f:
                    return json.load(f)
            else:
                # Return default/empty data structure if file doesn't exist
                return {
                    "weight": {"value": None, "status": None},
                    "sensors": {"gyro": None, "accel": None, "temp": None, "distance": None},
                    "health": {"bpm": None},
                    "tempgun": {"temp_object": None}
                }
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading sensor data: {e}")
            return self.last_data
            
    def get_heart_rate(self) -> Optional[int]:
        """Get heart rate value."""
        data = self.get_sensor_data()
        return data.get("health", {}).get("bpm")
        
    def get_temperature(self) -> Optional[float]:
        """Get temperature value from temp gun."""
        data = self.get_sensor_data()
        temp_celsius = data.get("tempgun", {}).get("temp_object")
        if temp_celsius is not None:
            # Return temperature in Celsius directly
            return round(temp_celsius, 1)
        return None
        
    def get_weight_status(self) -> Dict[str, Any]:
        """Get weight sensor status."""
        data = self.get_sensor_data()
        return data.get("weight", {"value": None, "status": None})
        
    def get_motion_status(self) -> Dict[str, Any]:
        """Get motion sensor data."""
        data = self.get_sensor_data()
        sensors = data.get("sensors", {})
        return {
            "gyro": sensors.get("gyro"),
            "accel": sensors.get("accel"),
            "distance": sensors.get("distance")
        }
        
    def start_monitoring(self):
        """Start monitoring the JSON file for changes."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            
    def stop_monitoring(self):
        """Stop monitoring the JSON file."""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def _monitor_loop(self):
        """Internal loop that monitors for data changes."""
        while self.running:
            try:
                current_data = self.get_sensor_data()
                if current_data != self.last_data:
                    self.last_data = current_data.copy()
                    # Notify all callbacks of the data change
                    for callback in self.callbacks:
                        try:
                            callback(current_data)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                            
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
                
    def get_formatted_data(self) -> Dict[str, Any]:
        """Get formatted data for display in GUI."""
        data = self.get_sensor_data()
        
        # Format heart rate
        bpm = self.get_heart_rate()
        heart_rate = {
            "value": bpm if bpm is not None else "--",
            "status": "Normal" if bpm and bpm <= 100 else "High" if bpm and bpm > 100 else "Unknown",
            "color": "#2E7D32" if bpm and bpm <= 100 else "#C62828" if bpm and bpm > 100 else "#626973"
        }
        
        # Format temperature
        temp_c = self.get_temperature()
        temperature = {
            "value": f"{temp_c:.1f}" if temp_c is not None else "--",
            "status": "Normal" if temp_c and 36.1 <= temp_c <= 37.5 else "Abnormal" if temp_c else "Unknown",
            "color": "#0A2463" if temp_c and 36.1 <= temp_c <= 37.5 else "#C62828" if temp_c else "#626973"
        }
        
        # Format weight
        weight_data = self.get_weight_status()
        weight = {
            "value": weight_data.get("value", "--"),
            "status": weight_data.get("status", "Unknown")
        }
        
        # Format motion
        motion_data = self.get_motion_status()
        motion_detected = any([
            motion_data.get("gyro"),
            motion_data.get("accel"),
            motion_data.get("distance") is not None
        ])
        
        return {
            "heart_rate": heart_rate,
            "temperature": temperature,
            "weight": weight,
            "motion": {
                "detected": motion_detected,
                "distance": motion_data.get("distance"),
                "gyro": motion_data.get("gyro"),
                "accel": motion_data.get("accel")
            },
            "system_status": "Online" if any([bpm, temp_c, weight_data.get("value")]) else "Waiting for data"
        } 