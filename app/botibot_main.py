import tkinter as tk
import threading
import time
import sys
import os
from data_reader import DataReader
from mongodb_reader import MongoDBReader
from screens import FacialRecognitionScreen, MainScreen
from components import ColorScheme
from config import get_config

class BotiBotApp:
    """Main BotiBot application with component-based architecture."""
    
    def __init__(self):
        # Load configuration
        self.config = get_config()
        
        # Initialize window
        self.root = tk.Tk()
        self.setup_window()
        
        # Color scheme
        self.colors = ColorScheme()
        
        # Window dragging variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_hidden = False
        
        # Data reader for sensor integration
        sensor_path = self.config.get('data.sensor_data_path', "/home/bsit/botibot.py/botibot/mqtt_data.json")
        self.data_reader = DataReader(sensor_path)
        
        # MongoDB reader for database integration
        connection_string = "mongodb+srv://ondababy:ondababy@ipt-project.yfofz.mongodb.net/botibot?retryWrites=true&w=majority&appName=IPT-Project"
        self.mongodb_reader = MongoDBReader(connection_string)
        
        # Current screen and user info
        self.current_screen = None
        self.authenticated_user = None
        
        # Setup window behavior
        self.setup_window_behavior()
        
        # Start with facial recognition
        self.show_facial_recognition()
        
        # Start data monitoring
        self.start_data_monitoring()
        
    def setup_window(self):
        """Setup window based on configuration."""
        window_config = self.config.get_window_config()
        
        # Basic window properties
        self.root.title(window_config.get('title', 'BOTIBOT - Smart Medication Assistant'))
        
        width = window_config.get('width', 800)
        height = window_config.get('height', 480)
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg='#FFFFFF')
        
        # Kiosk mode vs windowed mode
        if window_config.get('kiosk_mode', False):
            self.root.overrideredirect(True)  # Remove window decorations
            print("🔒 Running in kiosk mode (fixed window)")
        else:
            self.root.overrideredirect(False)  # Keep window decorations
            self.root.resizable(window_config.get('resizable', True), 
                               window_config.get('resizable', True))
            print("🪟 Running in windowed mode (draggable)")
            
        # Window properties
        if window_config.get('always_on_top', False):
            self.root.attributes('-topmost', True)
            
        if window_config.get('fullscreen', False):
            self.root.attributes('-fullscreen', True)
            
    def setup_window_behavior(self):
        """Setup window behavior including dragging and shortcuts."""
        window_config = self.config.get_window_config()
        
        # Center window if configured
        if window_config.get('center_on_start', True):
            self.center_window()
            
        # Dragging is now handled by the header component in kiosk mode
            
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Restore window position if configured
        if window_config.get('remember_position', True):
            self.restore_window_position()
            

        
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        shortcuts = self.config.get_keyboard_shortcuts()
        
        # Note: This is a simplified version. For full shortcut support,
        # you'd want to use a proper key binding library
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Control-q>', lambda e: self.close_application())
        self.root.bind('<Control-h>', lambda e: self.hide_window())
        self.root.bind('<Control-Shift-H>', lambda e: self.show_window())
        self.root.bind('<Control-k>', lambda e: self.toggle_kiosk_mode())
        self.root.bind('<Escape>', lambda e: self.emergency_escape())
        
        # Make sure the window can receive key events
        self.root.focus_set()
        
    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def save_window_position(self):
        """Save current window position."""
        try:
            geometry = self.root.geometry()
            self.config.set('window.last_geometry', geometry)
            self.config.save_config()
        except Exception as e:
            print(f"Could not save window position: {e}")
            
    def restore_window_position(self):
        """Restore saved window position."""
        try:
            last_geometry = self.config.get('window.last_geometry')
            if last_geometry:
                self.root.geometry(last_geometry)
        except Exception as e:
            print(f"Could not restore window position: {e}")
            
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)
        mode = "fullscreen" if not is_fullscreen else "windowed"
        print(f"🖥️ Switched to {mode} mode")
        
    def hide_window(self):
        """Hide the window."""
        if not self.is_hidden:
            self.root.withdraw()
            self.is_hidden = True
            print("👁️ Window hidden (Ctrl+Shift+H to show)")
            
    def show_window(self):
        """Show the window."""
        if self.is_hidden:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_hidden = False
            print("👁️ Window shown")
            
    def toggle_kiosk_mode(self):
        """Toggle kiosk mode and restart window."""
        current_mode = self.config.toggle_kiosk_mode()
        mode_text = "kiosk" if current_mode else "windowed"
        print(f"🔄 Switched to {mode_text} mode. Restart application to apply changes.")
        
    def emergency_escape(self):
        """Emergency escape - always show window and exit kiosk mode."""
        self.show_window()
        if self.config.get('window.kiosk_mode', False):
            self.config.set('window.kiosk_mode', False)
            self.config.save_config()
        self.root.attributes('-fullscreen', False)
        print("🚨 Emergency escape activated - window unlocked")
        
    def show_facial_recognition(self):
        """Show the facial recognition screen."""
        if self.current_screen:
            self.cleanup_current_screen()
            
        self.current_screen = FacialRecognitionScreen(self.root, colors=self.colors)
        self.current_screen.add_callback('authentication_complete', self.on_authentication_complete)
        self.current_screen.add_callback('close', self.close_application)
        
    def on_authentication_complete(self, user_info=None):
        """Handle successful authentication."""
        self.authenticated_user = user_info
        
        if user_info:
            print(f"✅ User authenticated: {user_info['firstName']} {user_info['lastName']}")
            print(f"   User ID: {user_info['id']}")
            print(f"   Email: {user_info['email']}")
            print(f"   Recognition accuracy: {user_info['accuracy']:.1f}%")
        else:
            print("✅ Authentication completed (no user data)")
        
        # Proceed to main screen
        self.show_main_screen()
        
    def show_main_screen(self):
        """Show the main dashboard screen."""
        if self.current_screen:
            self.cleanup_current_screen()
            
        self.current_screen = MainScreen(self.root, 
                                       data_reader=self.data_reader,
                                       mongodb_reader=self.mongodb_reader,
                                       colors=self.colors)
        self.current_screen.add_callback('close', self.close_application)
        self.current_screen.add_callback('dispense_medication', self.handle_dispense_medication)
        self.current_screen.add_callback('emergency_alert', self.handle_emergency_alert)
        self.current_screen.add_callback('logout', self.handle_logout)
        
    def cleanup_current_screen(self):
        """Clean up the current screen."""
        if self.current_screen and hasattr(self.current_screen, 'cleanup'):
            self.current_screen.cleanup()
        
        # Clear the root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
    def start_data_monitoring(self):
        """Start monitoring sensor data."""
        try:
            self.data_reader.start_monitoring()
            print("✓ Data monitoring started")
        except Exception as e:
            print(f"✗ Error starting data monitoring: {e}")
        
        # Start MongoDB monitoring
        try:
            if self.mongodb_reader.start_monitoring():
                print("✓ MongoDB monitoring started")
            else:
                print("✗ MongoDB monitoring failed to start")
        except Exception as e:
            print(f"✗ Error starting MongoDB monitoring: {e}")
            
    def stop_data_monitoring(self):
        """Stop monitoring sensor data."""
        try:
            self.data_reader.stop_monitoring()
            print("✓ Data monitoring stopped")
        except Exception as e:
            print(f"✗ Error stopping data monitoring: {e}")
        
        # Stop MongoDB monitoring
        try:
            self.mongodb_reader.stop_monitoring()
            print("✓ MongoDB monitoring stopped")
        except Exception as e:
            print(f"✗ Error stopping MongoDB monitoring: {e}")
            
    def handle_dispense_medication(self):
        """Handle medication dispensing action."""
        if self.authenticated_user:
            user_name = f"{self.authenticated_user['firstName']} {self.authenticated_user['lastName']}"
            print(f"💊 Dispensing medication for user: {user_name}")
            print(f"   User ID: {self.authenticated_user['id']}")
        else:
            print("❌ No authenticated user for medication dispensing")
        
        # Integration point for physical dispensing mechanism
        self.send_dispense_signal()
        
    def handle_emergency_alert(self):
        """Handle emergency alert action."""
        if self.authenticated_user:
            user_name = f"{self.authenticated_user['firstName']} {self.authenticated_user['lastName']}"
            print(f"🚨 Emergency alert for user: {user_name}")
            print(f"   User ID: {self.authenticated_user['id']}")
            print(f"   Email: {self.authenticated_user['email']}")
        else:
            print("🚨 Anonymous emergency alert")
        
        # Integration point for emergency response
        self.send_emergency_alert()
        
    def handle_logout(self):
        """Handle user logout."""
        if self.authenticated_user:
            user_name = f"{self.authenticated_user['firstName']} {self.authenticated_user['lastName']}"
            print(f"👋 User logged out: {user_name}")
        else:
            print("👋 User logged out: Unknown")
            
        self.authenticated_user = None
        self.show_facial_recognition()
        
    def send_dispense_signal(self):
        """Send signal to dispensing hardware."""
        try:
            print("Hardware: Activating dispensing mechanism...")
            
            # Example MQTT integration (uncomment and modify as needed):
            # import paho.mqtt.client as mqtt
            # client = mqtt.Client()
            # client.connect("192.168.4.1", 1883, 60)
            # client.publish("dispenser/command", "dispense")
            # client.disconnect()
            
        except Exception as e:
            print(f"✗ Error sending dispense signal: {e}")
            
    def send_emergency_alert(self):
        """Send emergency alert."""
        try:
            print("Emergency: Sending alert to caregivers...")
            
            # Integration points:
            # - Send SMS/email to emergency contacts
            # - Post to emergency monitoring system
            # - Activate audio/visual alarms
            
        except Exception as e:
            print(f"✗ Error sending emergency alert: {e}")
            
    def close_application(self):
        """Close the application gracefully."""
        print("Closing BotiBot application...")
        
        # Save window position if configured
        if self.config.get('window.remember_position', True):
            self.save_window_position()
        
        self.stop_data_monitoring()
        self.cleanup_current_screen()
        
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """Run the application."""
        try:
            print("🚀 Starting BotiBot application...")
            self.root.mainloop()
        except KeyboardInterrupt:
            print("Application interrupted by user")
            self.close_application()
        except Exception as e:
            print(f"✗ Application error: {e}")
            self.close_application()

def main():
    """Main entry point."""
    app = BotiBotApp()
    app.run()

if __name__ == "__main__":
    main()