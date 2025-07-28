#!/usr/bin/env python3

"""
BotiBot Configuration Management

This module handles all configuration settings for the BotiBot application,
including window behavior, display settings, and sensor parameters.
"""

import json
import os
import time
from typing import Dict, Any

class BotiBotConfig:
    """Configuration manager for BotiBot application."""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "window": {
            "kiosk_mode": False,          # True = fixed/locked, False = draggable window
            "width": 800,
            "height": 480,
            "resizable": True,            # Allow window resizing
            "always_on_top": False,       # Keep window on top
            "fullscreen": False,          # Start in fullscreen
            "center_on_start": True,      # Center window on startup
            "remember_position": True,    # Save/restore window position
            "title": "BOTIBOT - Smart Medication Assistant"
        },
        "interface": {
            "show_title_bar": True,       # Show window title bar (ignored in kiosk mode)
            "enable_close_button": True,  # Show close button in header
            "enable_minimize": True,      # Allow window minimization
            "theme": "default",           # UI theme
            "font_size": "normal",        # UI font size scaling
            "touch_mode": True            # Optimize for touch interactions
        },
        "data": {
            "sensor_data_path": "/home/bsit/botibot.py/botibot/mqtt_data.json",
            "update_interval": 1.0,       # Data refresh rate (seconds)
            "auto_start_monitoring": True, # Start sensor monitoring automatically
            "fallback_to_test_data": False # Use test data if real data unavailable
        },
        "sensors": {
            "heart_rate_threshold": 100,  # BPM threshold for normal/high
            "temp_normal_min": 36.1,      # °C minimum normal temperature
            "temp_normal_max": 37.5,      # °C maximum normal temperature
            "motion_sensitivity": 0.3,    # Motion detection sensitivity
            "weight_change_threshold": 0.1 # Minimum weight change to detect
        },
        "alerts": {
            "enable_sound": True,         # Enable audio alerts
            "enable_visual": True,        # Enable visual alerts
            "flash_on_emergency": True,   # Flash screen on emergency
            "auto_alert_caregivers": False # Automatically alert caregivers
        },
        "keyboard_shortcuts": {
            "toggle_fullscreen": "F11",   # Toggle fullscreen mode
            "hide_window": "Ctrl+H",      # Hide window
            "show_window": "Ctrl+Shift+H", # Show window
            "emergency": "Ctrl+E",        # Emergency alert
            "quit": "Ctrl+Q"              # Quit application
        }
    }
    
    def __init__(self, config_file="botibot_config.json"):
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        
    def load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    # Merge saved config with defaults (preserving new default keys)
                    self._deep_merge(self.config, saved_config)
                print(f"✓ Loaded configuration from {self.config_file}")
            else:
                print(f"📄 Creating default configuration: {self.config_file}")
                self.save_config()
        except Exception as e:
            print(f"⚠ Error loading config, using defaults: {e}")
            
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✓ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"✗ Error saving config: {e}")
            
    def _deep_merge(self, base_dict, update_dict):
        """Recursively merge dictionaries."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
                
    def get(self, key_path, default=None):
        """Get configuration value using dot notation (e.g., 'window.width')."""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key_path, value):
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config_dict = self.config
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config_dict:
                config_dict[key] = {}
            config_dict = config_dict[key]
            
        # Set the final value
        config_dict[keys[-1]] = value
        
    def toggle_kiosk_mode(self):
        """Toggle kiosk mode on/off."""
        current = self.get('window.kiosk_mode', False)
        self.set('window.kiosk_mode', not current)
        self.save_config()
        return not current
        
    def is_kiosk_mode(self):
        """Check if kiosk mode is enabled."""
        return self.get('window.kiosk_mode', False)
        
    def get_window_config(self):
        """Get window-specific configuration."""
        return self.get('window', {})
        
    def get_sensor_config(self):
        """Get sensor-specific configuration."""
        return self.get('sensors', {})
        
    def get_keyboard_shortcuts(self):
        """Get keyboard shortcuts configuration."""
        return self.get('keyboard_shortcuts', {})
        
    def export_config(self, filename=None):
        """Export configuration to a file."""
        if filename is None:
            filename = f"botibot_config_backup_{int(time.time())}.json"
            
        try:
            with open(filename, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✓ Configuration exported to {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error exporting config: {e}")
            return None
            
    def import_config(self, filename):
        """Import configuration from a file."""
        try:
            with open(filename, 'r') as f:
                imported_config = json.load(f)
                self.config = imported_config
                self.save_config()
            print(f"✓ Configuration imported from {filename}")
            return True
        except Exception as e:
            print(f"✗ Error importing config: {e}")
            return False
            
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
        print("✓ Configuration reset to defaults")

# Global configuration instance
config = BotiBotConfig()

def get_config():
    """Get the global configuration instance."""
    return config 