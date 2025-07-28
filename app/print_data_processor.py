#!/usr/bin/env python3
"""
Data processor for thermal printing MQTT sensor data
Formats sensor data into readable print format
"""

import json
import os
from datetime import datetime
from thermal_printer import ThermalPrinter

class SensorDataProcessor:
    """Process and format sensor data for thermal printing"""
    
    def __init__(self, device_path="/dev/usb/lp0"):
        self.printer = ThermalPrinter(device_path)
        
    def load_mqtt_data(self):
        """Load MQTT data from JSON file"""
        try:
            mqtt_file_path = '/home/bsit/botibot.py/botibot/mqtt_data.json'
            
            if os.path.exists(mqtt_file_path):
                with open(mqtt_file_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"❌ MQTT data file not found at: {mqtt_file_path}")
                return None
                
        except Exception as e:
            print(f"❌ Error loading MQTT data: {e}")
            return None
    
    def format_sensor_data_for_print(self, mqtt_data):
        """Format MQTT sensor data into readable text for printing"""
        if not mqtt_data:
            return "No sensor data available"
        
        # Header
        report = "BOTIBOT SENSOR REPORT\n"
        report += "=" * 32 + "\n\n"
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report += f"Generated: {timestamp}\n\n"
        
        # Health Data
        report += "HEALTH MONITORING\n"
        report += "-" * 32 + "\n"
        
        # Heart Rate (fix typo: bpm not bmp)
        bpm = mqtt_data.get('health', {}).get('bpm')
        if bpm is not None and isinstance(bpm, (int, float)):
            status = self._get_heart_rate_status(bpm)
            report += f"Heart Rate: {int(bpm)} bpm\n"
            report += f"Status: {status}\n"
        else:
            report += "Heart Rate: No data\n"
        
        report += "\n"
        
        # Temperature Data
        temp_celsius = mqtt_data.get('tempgun', {}).get('temp_object')
        if temp_celsius is not None and isinstance(temp_celsius, (int, float)):
            temp_status = self._get_temperature_status(temp_celsius)
            # Convert to Fahrenheit for additional info
            temp_fahrenheit = (temp_celsius * 9/5) + 32
            report += f"Temperature: {temp_celsius:.1f}C\n"
            report += f"           ({temp_fahrenheit:.1f}F)\n"
            report += f"Status: {temp_status}\n"
        else:
            report += "Temperature: No data\n"
        
        report += "\n"
        
        # Weight Data
        weight_data = mqtt_data.get('weight', {})
        if weight_data.get('value') is not None:
            report += "WEIGHT MONITORING\n"
            report += "-" * 32 + "\n"
            report += f"Weight: {weight_data['value']}\n"
            if weight_data.get('status'):
                report += f"Status: {weight_data['status']}\n"
            report += "\n"
        
        # Sensor Data
        sensors = mqtt_data.get('sensors', {})
        if any(v is not None for v in sensors.values()):
            report += "SENSOR READINGS\n"
            report += "-" * 32 + "\n"
            
            if sensors.get('temp') is not None:
                report += f"Ambient Temp: {sensors['temp']:.1f}C\n"
            
            if sensors.get('distance') is not None:
                report += f"Distance: {sensors['distance']:.1f}cm\n"
            
            if sensors.get('gyro') is not None:
                report += f"Gyroscope: Active\n"
            
            if sensors.get('accel') is not None:
                report += f"Accelerometer: Active\n"
            
            report += "\n"
        
        # System Status
        report += "SYSTEM STATUS\n"
        report += "-" * 32 + "\n"
        
        # Determine overall status
        has_vital_data = (
            mqtt_data.get('health', {}).get('bpm') is not None or
            mqtt_data.get('tempgun', {}).get('temp_object') is not None
        )
        
        if has_vital_data:
            report += "Status: ONLINE\n"
            report += "Monitoring: ACTIVE\n"
        else:
            report += "Status: WAITING FOR DATA\n"
            report += "Monitoring: STANDBY\n"
        
        report += "\n"
        
        # Footer
        report += "=" * 32 + "\n"
        report += "BOTIBOT Medical Assistant\n"
        report += "End of Report\n"
        
        return report
    
    def format_medication_schedule(self):
        """Format medication schedule for printing"""
        report = "MEDICATION SCHEDULE\n"
        report += "=" * 32 + "\n\n"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report += f"Generated: {timestamp}\n\n"
        
        # Sample medication schedule (you can modify this based on your data)
        medications = [
            {"name": "Aspirin", "dosage": "100mg", "time": "08:00", "status": "PENDING"},
            {"name": "Aspirin", "dosage": "100mg", "time": "14:00", "status": "NEXT"},
            {"name": "Aspirin", "dosage": "100mg", "time": "20:00", "status": "SCHEDULED"},
        ]
        
        report += "TODAY'S SCHEDULE\n"
        report += "-" * 32 + "\n"
        
        for med in medications:
            report += f"Time: {med['time']}\n"
            report += f"Medication: {med['name']}\n"
            report += f"Dosage: {med['dosage']}\n"
            report += f"Status: {med['status']}\n"
            report += "-" * 16 + "\n"
        
        report += "\n"
        report += "MEDICATION INVENTORY\n"
        report += "-" * 32 + "\n"
        report += "Aspirin: 14 pills remaining\n"
        report += "Refill needed: 7 days\n\n"
        
        report += "=" * 32 + "\n"
        report += "BOTIBOT Medical Assistant\n"
        report += "End of Schedule\n"
        
        return report
    
    def _get_heart_rate_status(self, bpm):
        """Get heart rate status based on BPM"""
        if 60 <= bpm <= 100:
            return "NORMAL"
        elif bpm < 60:
            return "LOW (Bradycardia)"
        else:
            return "HIGH (Tachycardia)"
    
    def _get_temperature_status(self, temp_celsius):
        """Get temperature status based on celsius reading"""
        if 36.1 <= temp_celsius <= 37.5:
            return "NORMAL"
        elif temp_celsius < 36.1:
            return "LOW (Hypothermia)"
        else:
            return "FEVER (Hyperthermia)"
    
    def print_sensor_report(self, add_borders=True, add_timestamp=True):
        """Print a complete sensor report"""
        mqtt_data = self.load_mqtt_data()
        if not mqtt_data:
            return False
        
        report_text = self.format_sensor_data_for_print(mqtt_data)
        return self.printer.print_text(report_text, center=True, add_borders=add_borders, add_timestamp=False)
    
    def print_medication_schedule(self, add_borders=True, add_timestamp=True):
        """Print medication schedule"""
        schedule_text = self.format_medication_schedule()
        return self.printer.print_text(schedule_text, center=True, add_borders=add_borders, add_timestamp=False)
    
    def print_combined_report(self, add_borders=True):
        """Print combined sensor and medication report"""
        mqtt_data = self.load_mqtt_data()
        if not mqtt_data:
            return False
        
        # Combine both reports
        combined_report = self.format_sensor_data_for_print(mqtt_data)
        combined_report += "\n\n"
        combined_report += self.format_medication_schedule()
        
        return self.printer.print_text(combined_report, center=True, add_borders=add_borders, add_timestamp=False)
    
    def print_quick_status(self):
        """Print a quick status summary"""
        mqtt_data = self.load_mqtt_data()
        if not mqtt_data:
            return False
        
        # Quick status format
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        quick_report = f"BOTIBOT STATUS - {timestamp}\n"
        quick_report += "=" * 32 + "\n"
        
        # Heart rate
        bpm = mqtt_data.get('health', {}).get('bpm')
        if bpm is not None:
            quick_report += f"Heart Rate: {int(bpm)} bpm\n"
        
        # Temperature
        temp = mqtt_data.get('tempgun', {}).get('temp_object')
        if temp is not None:
            quick_report += f"Temperature: {temp:.1f}C\n"
        
        # Next medication
        quick_report += f"Next Med: Aspirin 2:00 PM\n"
        
        quick_report += "=" * 32 + "\n"
        
        return self.printer.print_text(quick_report, center=True, add_borders=False)

    def print_custom_text(self, text):
        """Print custom formatted text to thermal printer"""
        try:
            if self.printer.is_connected:
                self.printer.text(text)
                self.printer.cut()
                print("✅ Custom text printed successfully")
                return True
            else:
                print("❌ Printer not connected")
                return False
                
        except Exception as e:
            print(f"❌ Error printing custom text: {e}")
            return False

# Convenience function for easy integration
def print_sensor_data(device_path="/dev/usb/lp0", report_type="full"):
    """
    Convenience function to print sensor data
    
    Args:
        device_path: Printer device path
        report_type: "full", "quick", "medication", "combined"
    """
    processor = SensorDataProcessor(device_path)
    
    if report_type == "full":
        return processor.print_sensor_report()
    elif report_type == "quick":
        return processor.print_quick_status()
    elif report_type == "medication":
        return processor.print_medication_schedule()
    elif report_type == "combined":
        return processor.print_combined_report()
    else:
        print(f"Unknown report type: {report_type}")
        return False

if __name__ == "__main__":
    # Test the processor
    processor = SensorDataProcessor()
    
    print("Testing sensor data formatting...")
    mqtt_data = processor.load_mqtt_data()
    if mqtt_data:
        formatted = processor.format_sensor_data_for_print(mqtt_data)
        print("Formatted output:")
        print(formatted)
    else:
        print("No MQTT data available for testing") 