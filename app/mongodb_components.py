import tkinter as tk
from components import BaseComponent, ColorScheme
from typing import Dict, Any

class MongoDBSensorCard(BaseComponent):
    """Enhanced sensor card for MongoDB data."""
    
    def __init__(self, parent, sensor_type: str, colors=None):
        super().__init__(parent, colors)
        self.sensor_type = sensor_type
        self.current_data = {}
        self.create_card()
    
    def create_card(self):
        """Create the sensor card."""
        # Card container
        self.frame = tk.Frame(self.parent, bg=self.colors.border, relief='flat', bd=1)
        
        # Card content
        content = tk.Frame(self.frame, bg=self.colors.bg_card)
        content.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Inner content with padding
        self.inner_content = tk.Frame(content, bg=self.colors.bg_card)
        self.inner_content.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Icon frame
        self.icon_frame = tk.Frame(self.inner_content, bg=self.colors.accent_primary, 
                                  width=50, height=50)
        self.icon_frame.pack(pady=(0, 20))
        self.icon_frame.pack_propagate(False)
        
        # Icon label
        self.icon_label = tk.Label(self.icon_frame, text=self._get_icon(), 
                                  font=('Segoe UI', 20),
                                  bg=self.colors.accent_primary, fg='white')
        self.icon_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Value frame
        value_frame = tk.Frame(self.inner_content, bg=self.colors.bg_card)
        value_frame.pack()
        
        # Value label
        self.value_label = tk.Label(value_frame, text="--", 
                                   font=('Segoe UI', 36, 'bold'),
                                   bg=self.colors.bg_card, 
                                   fg=self.colors.text_primary)
        self.value_label.pack(side='left')
        
        # Unit label
        self.unit_label = tk.Label(value_frame, text="", 
                                  font=('Segoe UI', 18),
                                  bg=self.colors.bg_card, 
                                  fg=self.colors.text_secondary)
        self.unit_label.pack(side='left', padx=(5, 0))
        
        # Label
        self.label_text = tk.Label(self.inner_content, text=self._get_label(), 
                                  font=('Segoe UI', 10, 'bold'),
                                  bg=self.colors.bg_card, 
                                  fg=self.colors.text_muted)
        self.label_text.pack(pady=(10, 20))
        
        # Status badge
        self.status_frame = tk.Frame(self.inner_content, bg=self.colors.accent_primary)
        self.status_frame.pack(fill='x')
        
        self.status_label = tk.Label(self.status_frame, text="--", 
                                    font=('Segoe UI', 9, 'bold'),
                                    bg=self.colors.accent_primary, fg='white', pady=8)
        self.status_label.pack()
    
    def _get_icon(self) -> str:
        """Get icon for sensor type."""
        icons = {
            'temperature': '🌡️',
            'heart_rate': '❤️',
            'alcohol': '🧪'
        }
        return icons.get(self.sensor_type, '📊')
    
    def _get_label(self) -> str:
        """Get label for sensor type."""
        labels = {
            'temperature': 'TEMPERATURE',
            'heart_rate': 'HEART RATE',
            'alcohol': 'ALCOHOL LEVEL'
        }
        return labels.get(self.sensor_type, 'SENSOR')
    
    def update_data(self, data: Dict[str, Any]):
        """Update card with new data."""
        if self.sensor_type in data:
            sensor_data = data[self.sensor_type]
            
            # Update value and unit
            value = sensor_data.get('value', '--')
            unit = sensor_data.get('unit', '')
            status = sensor_data.get('status', '--')
            color = sensor_data.get('color', self.colors.accent_primary)
            
            self.value_label.config(text=str(value))
            self.unit_label.config(text=unit)
            self.status_label.config(text=status.upper())
            
            # Update colors
            self.icon_frame.config(bg=color)
            self.icon_label.config(bg=color)
            self.status_frame.config(bg=color)
            self.status_label.config(bg=color)
            
            self.current_data = sensor_data

class MongoDBDataDisplay(BaseComponent):
    """Display component for MongoDB sensor data."""
    
    def __init__(self, parent, mongodb_reader, colors=None):
        super().__init__(parent, colors)
        self.mongodb_reader = mongodb_reader
        self.sensor_cards = {}
        self.create_display()
        
        # Add callback for data updates
        self.mongodb_reader.add_callback(self.update_display)
    
    def create_display(self):
        """Create the data display."""
        self.frame = tk.Frame(self.parent, bg=self.colors.bg_primary)
        self.frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(self.frame, 
                        text="Live Sensor Data from MongoDB",
                        font=('Segoe UI', 20, 'bold'),
                        bg=self.colors.bg_primary,
                        fg=self.colors.accent_primary)
        title.pack(pady=(0, 20))
        
        # Cards container
        cards_container = tk.Frame(self.frame, bg=self.colors.bg_primary)
        cards_container.pack(fill='both', expand=True)
        
        # Configure grid
        cards_container.grid_columnconfigure(0, weight=1)
        cards_container.grid_columnconfigure(1, weight=1)
        cards_container.grid_columnconfigure(2, weight=1)
        
        # Create sensor cards
        self.sensor_cards['temperature'] = MongoDBSensorCard(
            cards_container, 'temperature', self.colors)
        self.sensor_cards['temperature'].frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        self.sensor_cards['heart_rate'] = MongoDBSensorCard(
            cards_container, 'heart_rate', self.colors)
        self.sensor_cards['heart_rate'].frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        self.sensor_cards['alcohol'] = MongoDBSensorCard(
            cards_container, 'alcohol', self.colors)
        self.sensor_cards['alcohol'].frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        
        # Status label
        self.status_label = tk.Label(self.frame,
                                   text="Connecting to MongoDB...",
                                   font=('Segoe UI', 12),
                                   bg=self.colors.bg_primary,
                                   fg=self.colors.text_secondary)
        self.status_label.pack(pady=(20, 0))
    
    def update_display(self, data: Dict[str, Any]):
        """Update display with new data."""
        # Update all sensor cards
        for sensor_type, card in self.sensor_cards.items():
            card.update_data(data)
        
        # Update status
        self.status_label.config(text="✓ Data updated successfully", 
                               fg=self.colors.accent_success)
        
        # Clear status after 3 seconds
        self.parent.after(3000, lambda: self.status_label.config(
            text="Monitoring live data...", fg=self.colors.text_secondary))
