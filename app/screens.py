import tkinter as tk
from typing import Callable, Optional
from components import BaseComponent, ColorScheme, ModernHeader, SensorCard, EnhancedSensorCard, MedicationCard, ActionButton
from mongodb_components import MongoDBDataDisplay
from print_data_processor import SensorDataProcessor
from face_recognition_client import FaceRecognitionClient
import threading
from datetime import datetime

class FacialRecognitionScreen(BaseComponent):
    """Facial recognition authentication screen."""
    
    def __init__(self, parent, colors=None):
        super().__init__(parent, colors)
        self.camera_frame = None
        self.camera_icon = None
        self.status_label = None
        self.face_rec_btn = None
        self.face_client = FaceRecognitionClient()
        self.current_user = None
        self.pulse_active = True  # Flag to control animation
        self.pulse_job = None  # Store animation job reference
        self.create_screen()
        
    def create_screen(self):
        # Main container
        self.frame = tk.Frame(self.parent, bg=self.colors.bg_primary)
        self.frame.pack(fill='both', expand=True)
        
        # Modern header (enable dragging in kiosk mode)
        from config import get_config
        config = get_config()
        enable_drag = config.get('window.kiosk_mode', False)
        
        header = ModernHeader(self.frame, show_user=False, colors=self.colors, enable_dragging=enable_drag)
        header.add_callback('close', lambda: self.trigger_callback('close'))
        
        # Content area
        content_frame = tk.Frame(self.frame, bg=self.colors.bg_primary)
        content_frame.pack(fill='both', expand=True)
        
        # Center container
        center_container = tk.Frame(content_frame, bg=self.colors.bg_primary)
        center_container.place(relx=0.5, rely=0.5, anchor='center')
        
        # Circular frame for camera icon
        self.camera_frame = tk.Frame(center_container, bg=self.colors.bg_secondary, 
                                    width=180, height=180)
        self.camera_frame.pack(pady=(0, 30))
        self.camera_frame.pack_propagate(False)
        
        # Camera icon
        self.camera_icon = tk.Label(self.camera_frame, text="🔒", 
                                   font=('Segoe UI', 60), 
                                   bg=self.colors.bg_secondary,
                                   fg=self.colors.accent_primary)
        self.camera_icon.place(relx=0.5, rely=0.5, anchor='center')
        
        # Title
        title_label = tk.Label(center_container, 
                              text="Secure Access Required",
                              font=('Segoe UI', 24, 'bold'), 
                              bg=self.colors.bg_primary, 
                              fg=self.colors.text_primary)
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = tk.Label(center_container, 
                                 text="Please look at the camera to verify your identity",
                                 font=('Segoe UI', 12), 
                                 bg=self.colors.bg_primary, 
                                 fg=self.colors.text_secondary)
        subtitle_label.pack(pady=(0, 40))
        
        # Status label
        self.status_label = tk.Label(center_container, 
                                    text="",
                                    font=('Segoe UI', 12), 
                                    bg=self.colors.bg_primary)
        
        # Button
        button_container = tk.Frame(center_container, bg=self.colors.bg_primary)
        button_container.pack()
        
        self.face_rec_btn = tk.Button(button_container, 
                                     text="SCAN FACE",
                                     font=('Segoe UI', 13, 'bold'), 
                                     bg=self.colors.accent_primary,
                                     fg='white',
                                     relief='flat',
                                     bd=0,
                                     cursor='hand2',
                                     padx=50,
                                     pady=18,
                                     command=self.start_recognition)
        self.face_rec_btn.pack()
        
        self.add_button_effects(self.face_rec_btn)
        self.animate_pulse()
        
        # Test server connection on startup
        self.test_server_connection()
        
    def test_server_connection(self):
        """Test server connection in background."""
        def test():
            if self.face_client.test_connection():
                self.update_status("🟢 Server connected - Ready to scan", self.colors.accent_success)
            else:
                self.update_status("🔴 Server offline - Check connection", self.colors.accent_danger)
        
        threading.Thread(target=test, daemon=True).start()
        
    def update_status(self, text, color):
        """Update status label safely from any thread."""
        def update():
            self.status_label.config(text=text, fg=color)
            self.status_label.pack(pady=(20, 0))
        
        self.parent.after(0, update)
        
    def animate_pulse(self):
        """Create pulsing effect for camera frame."""
        def pulse():
            if not self.pulse_active or not self.camera_frame:
                return  # Stop animation if screen is destroyed or inactive
                
            try:
                # Check if camera_frame widget still exists
                if self.camera_frame.winfo_exists():
                    colors = [self.colors.bg_secondary, '#E8EEF7', '#D9E2F2', '#E8EEF7', self.colors.bg_secondary]
                    for i, color in enumerate(colors):
                        if self.pulse_active and self.camera_frame and self.camera_frame.winfo_exists():
                            self.parent.after(i * 100, lambda c=color: self.safe_update_camera_frame(c))
                    
                    # Schedule next pulse
                    if self.pulse_active:
                        self.pulse_job = self.parent.after(500, pulse)
            except tk.TclError:
                # Widget has been destroyed, stop animation
                self.pulse_active = False
                
        pulse()
    
    def safe_update_camera_frame(self, color):
        """Safely update camera frame color, checking if widget still exists."""
        try:
            if self.pulse_active and self.camera_frame and self.camera_frame.winfo_exists():
                self.camera_frame.config(bg=color)
        except tk.TclError:
            # Widget has been destroyed, stop animation
            self.pulse_active = False

    def start_recognition(self):
        """Start the facial recognition process."""
        self.face_rec_btn.config(state='disabled', 
                                text="SCANNING...",
                                bg=self.colors.text_muted)
        
        self.camera_icon.config(text="📸", fg=self.colors.accent_warning)
        self.update_status("📷 Capturing image...", self.colors.accent_warning)
        
        # Run recognition in background thread
        threading.Thread(target=self.perform_recognition, daemon=True).start()
        
    def perform_recognition(self):
        """Perform face recognition in background thread."""
        try:
            # Capture image with smart face detection
            self.update_status("📷 Starting smart face detection...", self.colors.accent_warning)
            image_base64 = self.face_client.capture_image_from_camera()
            
            if not image_base64:
                self.recognition_failed("No face detected within 20 seconds")
                return
            
            # Send to server for recognition
            self.update_status("🔄 Analyzing captured face...", self.colors.accent_warning)
            result = self.face_client.recognize_face(image_base64)
            
            if result['success']:
                data = result['data']
                if data.get('success', False):  # Check for success in the nested data
                    # Face recognized - extract user from recognized_user field
                    user = data.get('recognized_user', {})
                    confidence_data = data.get('confidence_data', {})
                    confidence = confidence_data.get('confidence', 0)
                    accuracy = confidence_data.get('accuracy', 0)
                    
                    self.current_user = {
                        'id': user.get('id'),
                        'firstName': user.get('firstName', ''),
                        'lastName': user.get('lastName', ''),
                        'email': user.get('email', ''),
                        'confidence': confidence,
                        'accuracy': accuracy,
                        'access_token': data.get('access_token', '')
                    }
                    
                    self.recognition_success()
                else:
                    # Unknown face
                    confidence_data = data.get('confidence_data', {})
                    confidence = confidence_data.get('confidence', 0)
                    self.recognition_unknown(confidence)
            else:
                # Error from server
                error_msg = result.get('message', 'Unknown error')
                self.recognition_failed(f"Server error: {error_msg}")
                
        except Exception as e:
            self.recognition_failed(f"Recognition error: {str(e)}")
    
    def recognition_success(self):
        """Handle successful face recognition."""
        def update_ui():
            user = self.current_user
            name = f"{user['firstName']} {user['lastName']}".strip()
            accuracy = user['accuracy']
            
            self.camera_icon.config(text="✓", fg=self.colors.accent_success)
            self.update_status(f"✅ Welcome, {name}! (Accuracy: {accuracy:.1f}%)", 
                             self.colors.accent_success)
            self.face_rec_btn.config(text="ACCESS GRANTED", 
                                   bg=self.colors.accent_success)
            
            # Trigger callback with user info
            self.parent.after(2000, lambda: self.trigger_callback('authentication_complete', self.current_user))
        
        self.parent.after(0, update_ui)
    
    def recognition_unknown(self, confidence):
        """Handle unknown face detection."""
        def update_ui():
            self.camera_icon.config(text="❓", fg=self.colors.accent_warning)
            self.update_status(f"⚠️ Unknown face detected (Confidence: {confidence:.1f}%)", 
                             self.colors.accent_warning)
            self.face_rec_btn.config(text="UNKNOWN USER", 
                                   bg=self.colors.accent_warning,
                                   state='normal')
            
            # Re-enable button after 3 seconds
            self.parent.after(3000, self.reset_button)
        
        self.parent.after(0, update_ui)
    
    def recognition_failed(self, error_message):
        """Handle recognition failure."""
        def update_ui():
            self.camera_icon.config(text="❌", fg=self.colors.accent_danger)
            self.update_status(f"❌ {error_message}", self.colors.accent_danger)
            self.face_rec_btn.config(text="TRY AGAIN", 
                                   bg=self.colors.accent_danger,
                                   state='normal')
            
            # Re-enable button after 3 seconds
            self.parent.after(3000, self.reset_button)
        
        self.parent.after(0, update_ui)
    
    def reset_button(self):
        """Reset button to initial state."""
        self.face_rec_btn.config(
            text="SCAN FACE",
            bg=self.colors.accent_primary,
            state='normal'
        )
        self.camera_icon.config(text="🔒", fg=self.colors.accent_primary)
    
    def cleanup(self):
        """Clean up resources."""
        # Stop the pulse animation
        self.pulse_active = False
        if self.pulse_job:
            try:
                self.parent.after_cancel(self.pulse_job)
            except:
                pass
            self.pulse_job = None
            
        # Clean up face recognition client
        if hasattr(self, 'face_client') and self.face_client:
            self.face_client.cleanup()
        
        # Clear widget references
        self.camera_frame = None
        self.camera_icon = None
        self.status_label = None
        self.face_rec_btn = None

class MainScreen(BaseComponent):
    """Main dashboard screen with sensor data and medication info."""
    
    def __init__(self, parent, data_reader=None, mongodb_reader=None, colors=None, current_user=None):
        super().__init__(parent, colors)
        self.data_reader = data_reader
        self.mongodb_reader = mongodb_reader
        self.current_user = current_user  # Store the authenticated user
        self.header = None
        self.sensor_cards = {}
        self.medication_card = None
        self.mongodb_display = None
        self.last_mqtt_data = None  # Track last data to detect changes
        self.print_processor = SensorDataProcessor()  # Initialize thermal printer
        self.create_screen()
        
        # Start data monitoring if data_reader is provided
        if self.data_reader:
            self.data_reader.add_callback(self.update_sensor_data)
        
        # Start automatic data refresh
        self.start_auto_refresh()
        
    def capture_sensor_data(self, sensor_type):
        """Capture the first/current data from the specified sensor."""
        print(f"🎯 Capturing {sensor_type} data...")
        
        try:
            # Get current MQTT data using robust parsing
            mqtt_data = self._get_latest_mqtt_data()
            
            if not mqtt_data:
                print(f"❌ No sensor data available for capture")
                self.show_capture_feedback(sensor_type, None, '', False)
                return
            
            # Extract the relevant sensor value
            captured_value = None
            sensor_info = {}
            
            if sensor_type == 'heart_rate':
                captured_value = mqtt_data.get('health', {}).get('bpm')
                sensor_info = {
                    'type': 'heart_rate',
                    'value': captured_value,
                    'unit': 'bpm',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user': self.current_user.get('email', 'Unknown') if self.current_user else 'Unknown'
                }
                
            elif sensor_type == 'temperature':
                captured_value = mqtt_data.get('tempgun', {}).get('temp_object')
                sensor_info = {
                    'type': 'temperature',
                    'value': captured_value,
                    'unit': '°C',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user': self.current_user.get('email', 'Unknown') if self.current_user else 'Unknown'
                }
                
            elif sensor_type == 'alcohol':
                # Try multiple sources for alcohol data
                captured_value = mqtt_data.get('alcohol', {}).get('level')
                if captured_value is None:
                    captured_value = mqtt_data.get('sensors', {}).get('alcohol')
                if captured_value is None:
                    captured_value = mqtt_data.get('alcohol_level')
                    
                sensor_info = {
                    'type': 'alcohol',
                    'value': captured_value,
                    'unit': '%',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user': self.current_user.get('email', 'Unknown') if self.current_user else 'Unknown'
                }
            
            # Display capture result
            if captured_value is not None:
                self.show_capture_feedback(sensor_type, captured_value, sensor_info['unit'], True)
                
                # Save to database if MongoDB reader is available
                if self.mongodb_reader:
                    self.save_captured_data_to_db(sensor_info)
                    
                # Print to thermal printer if available
                self.print_captured_data(sensor_info)
                
            else:
                self.show_capture_feedback(sensor_type, None, '', False)
                
        except Exception as e:
            print(f"❌ Error capturing {sensor_type} data: {e}")
            self.show_capture_feedback(sensor_type, None, '', False)
    
    def _get_latest_mqtt_data(self):
        """Get the latest MQTT data using robust JSON parsing."""
        try:
            import json
            import os
            
            mqtt_file_path = '/home/bsit/botibot.py/botibot/mqtt_data.json'
            
            if not os.path.exists(mqtt_file_path):
                print(f"❌ MQTT data file not found: {mqtt_file_path}")
                return None
            
            # Read the file content and handle multiple JSON objects
            with open(mqtt_file_path, 'r') as f:
                file_content = f.read().strip()
            
            if not file_content:
                print(f"⚠️ MQTT data file is empty")
                return None
            
            # Parse multiple JSON objects separated by newlines
            json_lines = []
            current_json = ""
            brace_count = 0
            
            for line in file_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                current_json += line
                
                # Count braces to detect complete JSON objects
                for char in line:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                
                # If braces are balanced, we have a complete JSON object
                if brace_count == 0 and current_json:
                    try:
                        # Validate JSON and add to list
                        json.loads(current_json)
                        json_lines.append(current_json)
                        current_json = ""
                    except json.JSONDecodeError:
                        # Reset if invalid JSON
                        current_json = ""
                        brace_count = 0
            
            if json_lines:
                # Use the last valid JSON object (most recent data)
                latest_json = json_lines[-1]
                return json.loads(latest_json)
            else:
                print(f"⚠️ No valid JSON objects found in data file")
                return None
                
        except Exception as e:
            print(f"❌ Error reading MQTT data: {e}")
            return None
    
    def show_capture_feedback(self, sensor_type, value, unit, success):
        """Show visual feedback for data capture."""
        # Create feedback popup
        feedback_frame = tk.Toplevel(self.parent)
        feedback_frame.title("Data Captured")
        feedback_frame.geometry("400x200")
        feedback_frame.configure(bg=self.colors.bg_primary)
        feedback_frame.transient(self.parent)
        feedback_frame.grab_set()
        
        # Center the popup
        feedback_frame.update_idletasks()
        x = (feedback_frame.winfo_screenwidth() // 2) - (400 // 2)
        y = (feedback_frame.winfo_screenheight() // 2) - (200 // 2)
        feedback_frame.geometry(f"400x200+{x}+{y}")
        
        # Content
        content_frame = tk.Frame(feedback_frame, bg=self.colors.bg_primary)
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        if success:
            # Success icon
            icon_label = tk.Label(content_frame, text="✅", font=('Segoe UI', 48),
                                 bg=self.colors.bg_primary, fg=self.colors.accent_success)
            icon_label.pack(pady=(0, 10))
            
            # Success message
            message = f"{sensor_type.replace('_', ' ').title()} Captured!"
            message_label = tk.Label(content_frame, text=message,
                                   font=('Segoe UI', 16, 'bold'),
                                   bg=self.colors.bg_primary, fg=self.colors.text_primary)
            message_label.pack(pady=5)
            
            # Value display
            value_text = f"Value: {value} {unit}"
            value_label = tk.Label(content_frame, text=value_text,
                                 font=('Segoe UI', 14),
                                 bg=self.colors.bg_primary, fg=self.colors.text_secondary)
            value_label.pack(pady=5)
            
            # User info
            if self.current_user:
                user_name = f"{self.current_user.get('firstName', '')} {self.current_user.get('lastName', '')}".strip()
                if not user_name:
                    user_name = self.current_user.get('email', 'Unknown User')
                user_text = f"User: {user_name}"
                user_label = tk.Label(content_frame, text=user_text,
                                     font=('Segoe UI', 12),
                                     bg=self.colors.bg_primary, fg=self.colors.text_muted)
                user_label.pack(pady=2)
            
        else:
            # Error icon
            icon_label = tk.Label(content_frame, text="❌", font=('Segoe UI', 48),
                                 bg=self.colors.bg_primary, fg=self.colors.accent_danger)
            icon_label.pack(pady=(0, 10))
            
            # Error message
            message = f"Failed to capture {sensor_type.replace('_', ' ')} data"
            message_label = tk.Label(content_frame, text=message,
                                   font=('Segoe UI', 16, 'bold'),
                                   bg=self.colors.bg_primary, fg=self.colors.accent_danger)
            message_label.pack(pady=5)
            
            # Info message
            info_label = tk.Label(content_frame, text="Please check sensor connection",
                                font=('Segoe UI', 12),
                                bg=self.colors.bg_primary, fg=self.colors.text_secondary)
            info_label.pack(pady=5)
        
        # Close button
        close_btn = tk.Button(content_frame, text="OK",
                             font=('Segoe UI', 12, 'bold'),
                             bg=self.colors.accent_primary, fg='white',
                             relief='flat', bd=0, cursor='hand2',
                             command=feedback_frame.destroy)
        close_btn.pack(pady=15)
        
        # Auto-close after 3 seconds
        feedback_frame.after(3000, feedback_frame.destroy)
    
    def save_captured_data_to_db(self, sensor_info):
        """Save captured sensor data to MongoDB database."""
        try:
            if self.mongodb_reader:
                # Use the MongoDB reader's connection to save data
                # This would require extending the MongoDB reader with a save method
                print(f"💾 Saving {sensor_info['type']} data to database: {sensor_info}")
                # TODO: Implement database saving logic
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
    
    def print_captured_data(self, sensor_info):
        """Print captured data to thermal printer."""
        try:
            if self.print_processor:
                timestamp = sensor_info['timestamp']
                sensor_type = sensor_info['type'].replace('_', ' ').title()
                value = sensor_info['value']
                unit = sensor_info['unit']
                user = sensor_info['user']
                
                print_text = f"""
BOTIBOT - Sensor Capture
========================
Sensor: {sensor_type}
Value: {value} {unit}
User: {user}
Time: {timestamp}
========================
"""
                
                success = self.print_processor.print_custom_text(print_text)
                if success:
                    print(f"🖨️ Printed {sensor_type} data successfully")
                else:
                    print(f"❌ Failed to print {sensor_type} data")
                    
        except Exception as e:
            print(f"❌ Error printing data: {e}")

    def set_current_user(self, user_data):
        """Set the current authenticated user and update display."""
        self.current_user = user_data
        if self.header:
            self.header.set_user_info(user_data)
        print(f"✅ User set in MainScreen: {user_data.get('firstName', '')} {user_data.get('lastName', '')}")
        
        # Also update the user info bar if it exists
        if hasattr(self, 'welcome_label'):
            user_name = f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
            if not user_name:
                user_name = user_data.get('email', 'User')
            self.welcome_label.config(text=f"👋 Welcome, {user_name}!")

    def start_auto_refresh(self):
        """Start automatic data refresh every 2 seconds."""
        self.refresh_mqtt_data()
        # MongoDB data refreshes independently every 3 seconds
        self.parent.after(2000, self.start_auto_refresh)
    
    def refresh_mqtt_data(self):
        """Reload MQTT data and update display if changed."""
        try:
            # Use absolute path where sensors_json.py writes the data
            import json
            import os
            
            mqtt_file_path = '/home/bsit/botibot.py/botibot/mqtt_data.json'
            
            if os.path.exists(mqtt_file_path):
                # Read the file content and handle multiple JSON objects
                with open(mqtt_file_path, 'r') as f:
                    file_content = f.read().strip()
                
                if not file_content:
                    print(f"⚠️ MQTT data file is empty: {mqtt_file_path}")
                    return
                
                # Split by lines that contain complete JSON objects
                # The file contains multiple JSON objects separated by newlines
                json_lines = []
                current_json = ""
                brace_count = 0
                
                for line in file_content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    current_json += line
                    
                    # Count braces to detect complete JSON objects
                    for char in line:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                    
                    # If braces are balanced, we have a complete JSON object
                    if brace_count == 0 and current_json:
                        try:
                            # Validate JSON and add to list
                            json.loads(current_json)
                            json_lines.append(current_json)
                            current_json = ""
                        except json.JSONDecodeError:
                            # Reset if invalid JSON
                            current_json = ""
                            brace_count = 0
                
                if json_lines:
                    # Use the last valid JSON object (most recent data)
                    latest_json = json_lines[-1]
                    current_mqtt_data = json.loads(latest_json)
                    
                    print(f"✓ Loaded latest MQTT data from: {mqtt_file_path}")
                    print(f"Found {len(json_lines)} JSON objects, using latest")
                    print(f"Temperature: {current_mqtt_data.get('tempgun', {}).get('temp_object', 'N/A')}°C")
                    print(f"Heart Rate: {current_mqtt_data.get('health', {}).get('bpm', 'N/A')} bpm")
                    print(f"Alcohol: {current_mqtt_data.get('alcohol', {}).get('level', 'N/A')}%")
                    
                    # Check if data has changed
                    if current_mqtt_data != self.last_mqtt_data:
                        print(f"🔄 Data changed! Updating display...")
                        self.last_mqtt_data = current_mqtt_data
                        # Update sensor display with new data
                        self.update_sensor_data(current_mqtt_data)
                    else:
                        print("📋 Data unchanged")
                else:
                    print(f"⚠️ No valid JSON objects found in: {mqtt_file_path}")
            else:
                print(f"❌ MQTT data file not found at: {mqtt_file_path}")
                print("   Make sure sensors_json.py is running and writing to this location")
                    
        except Exception as e:
            print(f"❌ Error refreshing MQTT data: {e}")
            import traceback
            traceback.print_exc()
            
    def create_screen(self):
        # Clear parent
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        # Create header (enable dragging in kiosk mode)
        from config import get_config
        config = get_config()
        enable_drag = config.get('window.kiosk_mode', False)
        
        self.header = ModernHeader(self.parent, show_user=True, user_data=self.current_user, colors=self.colors, enable_dragging=enable_drag)
        self.header.add_callback('close', lambda: self.trigger_callback('close'))
        
        # Create user info bar if user is authenticated
        if self.current_user:
            self.create_user_info_bar()
        
        # Main content
        self.create_main_content()
        
        # Add MongoDB section if available
        if self.mongodb_reader:
            self.create_mongodb_section()
        
        self.create_bottom_bar()
        
        # Initial data load
        if self.data_reader:
            self.update_sensor_data(self.data_reader.get_sensor_data())
            
    def set_current_user(self, user_data):
        """Set the current authenticated user and update display."""
        self.current_user = user_data
        if self.header:
            self.header.set_user_info(user_data)
        print(f"✅ User set in MainScreen: {user_data.get('firstName', '')} {user_data.get('lastName', '')}")
        
        # Also update the user info bar if it exists
        if hasattr(self, 'welcome_label'):
            user_name = f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
            if not user_name:
                user_name = user_data.get('email', 'User')
            self.welcome_label.config(text=f"👋 Welcome, {user_name}!")

    def create_user_info_bar(self):
        """Create a professional user information bar below the header."""
        user_bar = tk.Frame(self.parent, bg=self.colors.accent_primary, height=60)
        user_bar.pack(fill='x', pady=(0, 10))
        user_bar.pack_propagate(False)
        
        # User info container with professional layout
        user_container = tk.Frame(user_bar, bg=self.colors.accent_primary)
        user_container.pack(expand=True, fill='both', padx=25, pady=12)
        
        # Left section - User identity
        left_section = tk.Frame(user_container, bg=self.colors.accent_primary)
        left_section.pack(side='left', fill='y')
        
        # Prominent user name display
        user_name = f"{self.current_user.get('firstName', '')} {self.current_user.get('lastName', '')}".strip()
        if not user_name:
            user_name = self.current_user.get('email', 'User')
        
        # User icon and name
        user_identity_frame = tk.Frame(left_section, bg=self.colors.accent_primary)
        user_identity_frame.pack(side='left')
        
        # Professional user icon
        user_icon = tk.Label(user_identity_frame, text="👤", font=('Segoe UI', 20),
                            bg=self.colors.accent_primary, fg='white')
        user_icon.pack(side='left', padx=(0, 12))
        
        # User name and title
        user_info_text = tk.Frame(user_identity_frame, bg=self.colors.accent_primary)
        user_info_text.pack(side='left')
        
        self.welcome_label = tk.Label(user_info_text,
                                     text=f"Welcome, {user_name}",
                                     font=('Segoe UI', 16, 'bold'),
                                     bg=self.colors.accent_primary,
                                     fg='white')
        self.welcome_label.pack(anchor='w')
        
        # User role/status
        role_label = tk.Label(user_info_text,
                             text="Authenticated Patient",
                             font=('Segoe UI', 11),
                             bg=self.colors.accent_primary,
                             fg='white')
        role_label.pack(anchor='w')
        
        # Center section - Authentication details
        center_section = tk.Frame(user_container, bg=self.colors.accent_primary)
        center_section.pack(side='left', fill='y', padx=(40, 0))
        
        # Authentication method with icon
        auth_frame = tk.Frame(center_section, bg=self.colors.accent_primary)
        auth_frame.pack(anchor='w')
        
        auth_icon = tk.Label(auth_frame, text="🔐", font=('Segoe UI', 14),
                            bg=self.colors.accent_primary, fg='white')
        auth_icon.pack(side='left', padx=(0, 8))
        
        auth_method = tk.Label(auth_frame,
                              text="Face Recognition Login",
                              font=('Segoe UI', 11, 'bold'),
                              bg=self.colors.accent_primary,
                              fg='white')
        auth_method.pack(side='left')
        
        # Recognition accuracy if available
        if self.current_user.get('accuracy'):
            accuracy_frame = tk.Frame(center_section, bg=self.colors.accent_primary)
            accuracy_frame.pack(anchor='w', pady=(2, 0))
            
            accuracy_icon = tk.Label(accuracy_frame, text="🎯", font=('Segoe UI', 12),
                                    bg=self.colors.accent_primary, fg='white')
            accuracy_icon.pack(side='left', padx=(0, 8))
            
            accuracy_label = tk.Label(accuracy_frame,
                                     text=f"Recognition: {self.current_user['accuracy']:.1f}%",
                                     font=('Segoe UI', 10),
                                     bg=self.colors.accent_primary,
                                     fg='white')
            accuracy_label.pack(side='left')
        
        # Right section - Session info
        right_section = tk.Frame(user_container, bg=self.colors.accent_primary)
        right_section.pack(side='right', fill='y')
        
        # Session time
        session_frame = tk.Frame(right_section, bg=self.colors.accent_primary)
        session_frame.pack(anchor='e')
        
        time_icon = tk.Label(session_frame, text="🕐", font=('Segoe UI', 14),
                            bg=self.colors.accent_primary, fg='white')
        time_icon.pack(side='left', padx=(0, 8))
        
        session_time = tk.Label(session_frame,
                               text=f"Session: {datetime.now().strftime('%H:%M')}",
                               font=('Segoe UI', 11),
                               bg=self.colors.accent_primary,
                               fg='white')
        session_time.pack(side='left')
        
        # User email if available
        if self.current_user.get('email'):
            email_frame = tk.Frame(right_section, bg=self.colors.accent_primary)
            email_frame.pack(anchor='e', pady=(2, 0))
            
            email_icon = tk.Label(email_frame, text="📧", font=('Segoe UI', 12),
                                 bg=self.colors.accent_primary, fg='white')
            email_icon.pack(side='left', padx=(0, 8))
            
            email_label = tk.Label(email_frame,
                                  text=self.current_user['email'],
                                  font=('Segoe UI', 10),
                                  bg=self.colors.accent_primary,
                                  fg='white')
            email_label.pack(side='left')

    def create_main_content(self):
        """Create the main content area with enhanced sensor cards."""
        main_frame = tk.Frame(self.parent, bg=self.colors.bg_primary)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Grid layout for cards
        cards_frame = tk.Frame(main_frame, bg=self.colors.bg_primary)
        cards_frame.pack(fill='both', expand=True)
        
        # Configure grid - now 4 columns to include alcohol sensor
        cards_frame.grid_columnconfigure(0, weight=1, uniform="cards")
        cards_frame.grid_columnconfigure(1, weight=1, uniform="cards")
        cards_frame.grid_columnconfigure(2, weight=1, uniform="cards")
        cards_frame.grid_columnconfigure(3, weight=2, uniform="cards")
        cards_frame.grid_rowconfigure(0, weight=1)
        
        # Get initial data
        mqtt_data = self.data_reader.get_sensor_data() if self.data_reader else self._get_default_mqtt_data()
        formatted_data = self._format_mqtt_data(mqtt_data)
        
        # Heart rate card with capture button
        heart_rate_data = formatted_data['heart_rate']
        self.sensor_cards['heart_rate'] = EnhancedSensorCard(
            cards_frame,
            icon="❤️",
            value=heart_rate_data['value'],
            unit="bpm",
            label="Heart Rate",
            status=heart_rate_data['status'],
            color=heart_rate_data['color'],
            colors=self.colors,
            capture_callback=lambda: self.capture_sensor_data('heart_rate')
        )
        self.sensor_cards['heart_rate'].frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        # Temperature card with capture button
        temp_data = formatted_data['temperature']
        self.sensor_cards['temperature'] = EnhancedSensorCard(
            cards_frame,
            icon="🌡️",
            value=temp_data['value'],
            unit="°C",
            label="Temperature",
            status=temp_data['status'],
            color=temp_data['color'],
            colors=self.colors,
            capture_callback=lambda: self.capture_sensor_data('temperature')
        )
        self.sensor_cards['temperature'].frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        # Alcohol sensor card with capture button
        alcohol_data = formatted_data['alcohol']
        self.sensor_cards['alcohol'] = EnhancedSensorCard(
            cards_frame,
            icon="🧪",
            value=alcohol_data['value'],
            unit="%",
            label="Alcohol Level",
            status=alcohol_data['status'],
            color=alcohol_data['color'],
            colors=self.colors,
            capture_callback=lambda: self.capture_sensor_data('alcohol')
        )
        self.sensor_cards['alcohol'].frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        
        # Medication card
        self.medication_card = MedicationCard(cards_frame, colors=self.colors)
        self.medication_card.frame.grid(row=0, column=3, padx=10, pady=10, sticky='nsew')
        
        # Add MongoDB database section below the sensor cards
        self.create_mongodb_database_section(main_frame)
        
    def create_mongodb_section(self):
        """Create MongoDB data display section."""
        # MongoDB data container
        mongodb_container = tk.Frame(self.parent, bg=self.colors.bg_primary)
        mongodb_container.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Section title
        section_title = tk.Label(mongodb_container,
                               text="Database Sensor Data",
                               font=('Segoe UI', 16, 'bold'),
                               bg=self.colors.bg_primary,
                               fg=self.colors.accent_primary)
        section_title.pack(pady=(0, 10))
        
        # MongoDB display
        self.mongodb_display = MongoDBDataDisplay(
            mongodb_container, self.mongodb_reader, self.colors)
        
    def create_bottom_bar(self):
        """Create the bottom action bar."""
        bottom_frame = tk.Frame(self.parent, bg=self.colors.bg_primary)
        bottom_frame.pack(fill='x', side='bottom')
        
        # Border
        border = tk.Frame(bottom_frame, height=1, bg=self.colors.border)
        border.pack(fill='x')
        
        # Bottom bar
        bottom_bar = tk.Frame(bottom_frame, bg=self.colors.bg_secondary, height=100)
        bottom_bar.pack(fill='x')
        bottom_bar.pack_propagate(False)
        
        # Button container
        button_container = tk.Frame(bottom_bar, bg=self.colors.bg_secondary)
        button_container.pack(expand=True, pady=20)
        
        # Dispense button
        dispense_btn = ActionButton(
            button_container,
            text="DISPENSE NOW",
            icon="💊",
            bg_color=self.colors.accent_success,
            command=self.dispense_medication,
            colors=self.colors
        )
        dispense_btn.pack(side='left', padx=10)
        
        # Emergency button
        emergency_btn = ActionButton(
            button_container,
            text="EMERGENCY",
            icon="🚨",
            bg_color=self.colors.accent_danger,
            command=self.emergency_alert,
            colors=self.colors
        )
        emergency_btn.pack(side='left', padx=10)
        
        # Print Report button
        print_btn = ActionButton(
            button_container,
            text="PRINT REPORT",
            icon="🖨️",
            bg_color=self.colors.accent_primary,
            command=self.print_sensor_report,
            colors=self.colors
        )
        print_btn.pack(side='left', padx=10)
        
        # Print Quick Status button
        quick_print_btn = ActionButton(
            button_container,
            text="QUICK PRINT",
            icon="📄",
            bg_color=self.colors.accent_secondary,
            command=self.print_quick_status,
            colors=self.colors
        )
        quick_print_btn.pack(side='left', padx=10)
        
        # Logout button
        logout_btn = ActionButton(
            button_container,
            text="LOGOUT",
            icon="👋",
            bg_color=self.colors.text_muted,
            command=lambda: self.trigger_callback('logout'),
            colors=self.colors
        )
        logout_btn.pack(side='right', padx=10)
        
    def update_sensor_data(self, mqtt_data):
        """Update sensor cards with new MQTT data."""
        formatted_data = self._format_mqtt_data(mqtt_data)
        
        # Update heart rate
        if 'heart_rate' in self.sensor_cards:
            hr_data = formatted_data['heart_rate']
            self.sensor_cards['heart_rate'].update_data(
                value=hr_data['value'],
                status=hr_data['status'],
                color=hr_data['color']
            )
            
        # Update temperature
        if 'temperature' in self.sensor_cards:
            temp_data = formatted_data['temperature']
            self.sensor_cards['temperature'].update_data(
                value=temp_data['value'],
                status=temp_data['status'],
                color=temp_data['color']
            )
            
        # Update alcohol sensor
        if 'alcohol' in self.sensor_cards:
            alcohol_data = formatted_data['alcohol']
            self.sensor_cards['alcohol'].update_data(
                value=alcohol_data['value'],
                status=alcohol_data['status'],
                color=alcohol_data['color']
            )
            
        # Update header status
        if self.header:
            status = formatted_data.get('system_status', 'Waiting for data')
            is_online = "Online" in status
            self.header.update_status(status, is_online)
            self.header.update_datetime()
    
    def _get_default_mqtt_data(self):
        """Get default MQTT data structure when no data reader is available."""
        return {
            "weight": {
                "value": None,
                "status": None
            },
            "sensors": {
                "gyro": None,
                "accel": None,
                "temp": None,
                "distance": None
            },
            "health": {
                "bpm": None
            },
            "tempgun": {
                "temp_object": None
            }
        }
    
    def _format_mqtt_data(self, mqtt_data):
        """Format MQTT data for display in UI cards."""
        # Extract heart rate from health.bpm
        bpm = mqtt_data.get('health', {}).get('bpm')
        if bpm is not None:
            hr_value = str(int(bpm)) if isinstance(bpm, (int, float)) else str(bpm)
            if isinstance(bpm, (int, float)):
                if 60 <= bpm <= 100:
                    hr_status = "Normal"
                    hr_color = self.colors.accent_success
                elif bpm < 60:
                    hr_status = "Low"
                    hr_color = self.colors.accent_warning
                else:
                    hr_status = "High"
                    hr_color = self.colors.accent_danger
            else:
                hr_status = "Unknown"
                hr_color = self.colors.text_muted
        else:
            hr_value = "--"
            hr_status = "No Data"
            hr_color = self.colors.text_muted
        
        # Extract temperature from tempgun.temp_object
        temp_celsius = mqtt_data.get('tempgun', {}).get('temp_object')
        if temp_celsius is not None and isinstance(temp_celsius, (int, float)):
            # Use temperature in Celsius directly
            temp_value = f"{temp_celsius:.1f}"
            
            # Normal body temperature range in Celsius: 36.1-37.5
            if 36.1 <= temp_celsius <= 37.5:
                temp_status = "Normal"
                temp_color = self.colors.accent_success
            elif temp_celsius < 36.1:
                temp_status = "Low"
                temp_color = self.colors.accent_warning
            else:
                temp_status = "Fever"
                temp_color = self.colors.accent_danger
        else:
            temp_value = "--"
            temp_status = "No Data"
            temp_color = self.colors.text_muted
        
        # Extract alcohol level from alcohol sensor data
        alcohol_level = mqtt_data.get('alcohol', {}).get('level')
        if alcohol_level is None:
            # Try alternative data structures for alcohol sensor
            alcohol_level = mqtt_data.get('sensors', {}).get('alcohol')
            if alcohol_level is None:
                alcohol_level = mqtt_data.get('alcohol_level')
        
        if alcohol_level is not None and isinstance(alcohol_level, (int, float)):
            alcohol_value = f"{alcohol_level:.1f}"
            
            # Alcohol level thresholds (percentage)
            if alcohol_level == 0:
                alcohol_status = "Clean"
                alcohol_color = self.colors.accent_success
            elif alcohol_level <= 0.08:  # Legal limit in many places
                alcohol_status = "Low"
                alcohol_color = self.colors.accent_warning
            else:
                alcohol_status = "High"
                alcohol_color = self.colors.accent_danger
        else:
            alcohol_value = "--"
            alcohol_status = "No Data"
            alcohol_color = self.colors.text_muted
        
        # Determine system status
        sensors_available = sum(1 for val in [bpm, temp_celsius, alcohol_level] if val is not None)
        if sensors_available == 3:
            system_status = "All Sensors Online"
        elif sensors_available >= 1:
            system_status = f"{sensors_available}/3 Sensors Active"
        else:
            system_status = "Waiting for data"
        
        return {
            'heart_rate': {
                'value': hr_value,
                'status': hr_status,
                'color': hr_color
            },
            'temperature': {
                'value': temp_value,
                'status': temp_status,
                'color': temp_color
            },
            'alcohol': {
                'value': alcohol_value,
                'status': alcohol_status,
                'color': alcohol_color
            },
            'system_status': system_status
        }
            
    def _get_default_data(self):
        """Get default data when no data reader is available."""
        return self._format_mqtt_data(self._get_default_mqtt_data())
        
    def dispense_medication(self):
        """Handle medication dispensing."""
        print("💊 Dispensing medication...")
        self.trigger_callback('dispense_medication')
        
        # Visual feedback
        original_bg = self.parent['bg']
        self.parent.configure(bg=self.colors.accent_success)
        self.parent.after(200, lambda: self.parent.configure(bg=original_bg))
        
    def emergency_alert(self):
        """Handle emergency alert."""
        print("🚨 EMERGENCY ALERT ACTIVATED!")
        self.trigger_callback('emergency_alert')
        
        # Flash effect
        for i in range(3):
            self.parent.after(i * 200, 
                          lambda: self.parent.configure(bg=self.colors.accent_danger))
            self.parent.after(i * 200 + 100, 
                          lambda: self.parent.configure(bg=self.colors.bg_primary))
    
    def print_sensor_report(self):
        """Print a complete sensor report to thermal printer."""
        print("🖨️ Printing sensor report...")
        try:
            success = self.print_processor.print_sensor_report()
            if success:
                print("✓ Sensor report printed successfully!")
                self.show_print_feedback("Sensor report printed!", self.colors.accent_success)
            else:
                print("✗ Failed to print sensor report!")
                self.show_print_feedback("Print failed - check printer!", self.colors.accent_danger)
        except Exception as e:
            print(f"❌ Print error: {e}")
            self.show_print_feedback("Print error occurred!", self.colors.accent_danger)
    
    def print_quick_status(self):
        """Print a quick status summary to thermal printer."""
        print("📄 Printing quick status...")
        try:
            success = self.print_processor.print_quick_status()
            if success:
                print("✓ Quick status printed successfully!")
                self.show_print_feedback("Quick status printed!", self.colors.accent_success)
            else:
                print("✗ Failed to print quick status!")
                self.show_print_feedback("Print failed - check printer!", self.colors.accent_danger)
        except Exception as e:
            print(f"❌ Print error: {e}")
            self.show_print_feedback("Print error occurred!", self.colors.accent_danger)
    
    def show_print_feedback(self, message, color):
        """Show visual feedback for print operations."""
        # Create temporary feedback label
        if hasattr(self, 'header') and self.header:
            feedback_label = tk.Label(self.parent, 
                                    text=message,
                                    font=('Segoe UI', 12, 'bold'),
                                    bg=color,
                                    fg='white',
                                    pady=10)
            feedback_label.pack(side='top', fill='x')
            
            # Remove feedback after 3 seconds
            self.parent.after(3000, lambda: feedback_label.destroy())
                          
    def cleanup(self):
        """Clean up resources."""
        if self.data_reader:
            self.data_reader.remove_callback(self.update_sensor_data)
        
        if self.mongodb_reader:
            # MongoDB cleanup is handled in the main app
            pass
    
    def create_mongodb_database_section(self, parent_frame):
        """Create MongoDB database data display section below sensor cards."""
        if not self.mongodb_reader:
            return
            
        # Separator line
        separator = tk.Frame(parent_frame, height=2, bg=self.colors.border)
        separator.pack(fill='x', pady=(20, 10))
        
        # Database section title
        db_title_frame = tk.Frame(parent_frame, bg=self.colors.bg_primary)
        db_title_frame.pack(fill='x', pady=(0, 15))
        
        db_title = tk.Label(db_title_frame,
                           text="📊 Database Records",
                           font=('Segoe UI', 16, 'bold'),
                           bg=self.colors.bg_primary,
                           fg=self.colors.accent_primary)
        db_title.pack(side='left')
        
        # Database status indicator
        self.db_status_label = tk.Label(db_title_frame,
                                       text="● Connecting...",
                                       font=('Segoe UI', 10),
                                       bg=self.colors.bg_primary,
                                       fg=self.colors.text_secondary)
        self.db_status_label.pack(side='right')
        
        # MongoDB data cards frame
        db_cards_frame = tk.Frame(parent_frame, bg=self.colors.bg_primary)
        db_cards_frame.pack(fill='x', pady=(0, 20))
        
        # Configure grid for 3 MongoDB cards
        db_cards_frame.grid_columnconfigure(0, weight=1, uniform="db_cards")
        db_cards_frame.grid_columnconfigure(1, weight=1, uniform="db_cards")
        db_cards_frame.grid_columnconfigure(2, weight=1, uniform="db_cards")
        db_cards_frame.grid_rowconfigure(0, weight=1)
        
        # MongoDB Heart Rate Card
        self.mongodb_cards = {}
        self.mongodb_cards['heart_rate'] = SensorCard(
            db_cards_frame,
            icon="❤️",
            value="--",
            unit="bpm",
            label="DB Heart Rate",
            status="Loading...",
            color=self.colors.text_muted,
            colors=self.colors
        )
        self.mongodb_cards['heart_rate'].frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        # MongoDB Temperature Card
        self.mongodb_cards['temperature'] = SensorCard(
            db_cards_frame,
            icon="🌡️",
            value="--",
            unit="°C",
            label="DB Temperature",
            status="Loading...",
            color=self.colors.text_muted,
            colors=self.colors
        )
        self.mongodb_cards['temperature'].frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        # MongoDB Alcohol Card
        self.mongodb_cards['alcohol'] = SensorCard(
            db_cards_frame,
            icon="🍷",
            value="--",
            unit="%",
            label="DB Alcohol",
            status="Loading...",
            color=self.colors.text_muted,
            colors=self.colors
        )
        self.mongodb_cards['alcohol'].frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        
        # Start MongoDB data refresh
        self.refresh_mongodb_data()
        
    def refresh_mongodb_data(self):
        """Refresh MongoDB database data display."""
        if not self.mongodb_reader:
            return
            
        try:
            # Get latest data from MongoDB
            mongodb_data = self.mongodb_reader.get_latest_data()
            
            if mongodb_data:
                # Update status indicator
                self.db_status_label.config(text="● Connected", fg=self.colors.accent_success)
                
                # Update MongoDB heart rate card
                if 'heart_rate' in mongodb_data and hasattr(self, 'mongodb_cards'):
                    hr_data = mongodb_data['heart_rate']
                    self.mongodb_cards['heart_rate'].update_data(
                        value=str(hr_data.get('value', '--')),
                        status=hr_data.get('status', 'Unknown'),
                        color=hr_data.get('color', self.colors.text_muted)
                    )
                
                # Update MongoDB temperature card
                if 'temperature' in mongodb_data and hasattr(self, 'mongodb_cards'):
                    temp_data = mongodb_data['temperature']
                    self.mongodb_cards['temperature'].update_data(
                        value=str(temp_data.get('value', '--')),
                        status=temp_data.get('status', 'Unknown'),
                        color=temp_data.get('color', self.colors.text_muted)
                    )
                
                # Update MongoDB alcohol card
                if 'alcohol' in mongodb_data and hasattr(self, 'mongodb_cards'):
                    alcohol_data = mongodb_data['alcohol']
                    self.mongodb_cards['alcohol'].update_data(
                        value=str(alcohol_data.get('value', '--')),
                        status=alcohol_data.get('status', 'Unknown'),
                        color=alcohol_data.get('color', self.colors.text_muted)
                    )
                
                print(f"🔄 Updated MongoDB display: HR={mongodb_data.get('heart_rate', {}).get('value', 'N/A')}, Temp={mongodb_data.get('temperature', {}).get('value', 'N/A')}, Alcohol={mongodb_data.get('alcohol', {}).get('value', 'N/A')}")
            else:
                # Update status indicator
                self.db_status_label.config(text="● No Data", fg=self.colors.accent_warning)
                
        except Exception as e:
            print(f"❌ Error refreshing MongoDB data: {e}")
            if hasattr(self, 'db_status_label'):
                self.db_status_label.config(text="● Error", fg=self.colors.accent_danger)
        
        # Schedule next refresh in 3 seconds
        self.parent.after(3000, self.refresh_mongodb_data)