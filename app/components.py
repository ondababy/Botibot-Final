import tkinter as tk
from tkinter import ttk, font
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from icon_manager import get_icon_manager, create_icon_label

class ColorScheme:
    """Centralized color scheme for consistent styling."""
    bg_primary = '#FFFFFF'
    bg_secondary = '#F5F7FA'
    bg_card = '#FFFFFF'
    accent_primary = '#0A2463'
    accent_secondary = '#3E5C76'
    accent_success = '#2E7D32'
    accent_danger = '#C62828'
    accent_warning = '#F9A826'
    text_primary = '#2A2D34'
    text_secondary = '#626973'
    text_muted = '#8D96A5'
    border = '#E0E5EC'

class BaseComponent:
    """Base class for all GUI components."""
    
    def __init__(self, parent, colors=None):
        self.parent = parent
        self.colors = colors or ColorScheme()
        self.frame = None
        self.callbacks = {}
        
    def add_callback(self, event_name: str, callback: Callable):
        """Add a callback for a specific event."""
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []
        self.callbacks[event_name].append(callback)
        
    def trigger_callback(self, event_name: str, *args, **kwargs):
        """Trigger all callbacks for a specific event."""
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Error in callback {event_name}: {e}")
                    
    def add_button_effects(self, button):
        """Add modern hover effects to buttons."""
        def on_enter(e):
            button.configure(relief='raised', bd=1)
        
        def on_leave(e):
            button.configure(relief='flat', bd=0)
        
        def on_press(e):
            button.configure(relief='sunken')
        
        def on_release(e):
            button.configure(relief='raised')
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        button.bind('<ButtonPress-1>', on_press)
        button.bind('<ButtonRelease-1>', on_release)

class ModernHeader(BaseComponent):
    """Modern header component with user info and status."""
    
    def __init__(self, parent, show_user=False, user_data=None, colors=None, enable_dragging=False):
        super().__init__(parent, colors)
        self.show_user = show_user
        self.user_data = user_data or {}
        self.status_label = None
        self.datetime_label = None
        self.user_name_label = None
        self.enable_dragging = enable_dragging
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.create_header()
        
    def create_header(self):
        self.frame = tk.Frame(self.parent, bg=self.colors.bg_secondary, height=80)
        self.frame.pack(fill='x')
        self.frame.pack_propagate(False)
        
        # Subtle border at bottom
        border = tk.Frame(self.frame, height=1, bg=self.colors.border)
        border.pack(side='bottom', fill='x')
        
        # Inner header content
        inner_header = tk.Frame(self.frame, bg=self.colors.bg_secondary)
        inner_header.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Left section
        left_section = tk.Frame(inner_header, bg=self.colors.bg_secondary)
        left_section.pack(side='left', fill='y')
        
        # Logo and title
        title_label = tk.Label(left_section, text="BOTIBOT", 
                              font=('Segoe UI Semibold', 20), 
                              bg=self.colors.bg_secondary, 
                              fg=self.colors.accent_primary)
        title_label.pack(anchor='w')
        
        # Subtitle
        subtitle = tk.Label(left_section, text="Smart Medication Assistant", 
                           font=('Segoe UI', 10), 
                           bg=self.colors.bg_secondary, 
                           fg=self.colors.text_muted)
        subtitle.pack(anchor='w', pady=(5, 0))
        
        # Right section
        right_section = tk.Frame(inner_header, bg=self.colors.bg_secondary)
        right_section.pack(side='right', fill='y')
        
        # User info (if authenticated)
        if self.show_user and self.user_data:
            self.create_user_info_section(right_section)
        
        # Status indicator
        status_frame = tk.Frame(right_section, bg=self.colors.bg_secondary)
        status_frame.pack(anchor='ne', pady=(0, 5))
        
        self.status_dot = tk.Label(status_frame, text="●", font=('Segoe UI', 10), 
                                  bg=self.colors.bg_secondary, 
                                  fg=self.colors.accent_success)
        self.status_dot.pack(side='left', padx=(0, 5))
        
        self.status_label = tk.Label(status_frame, text="System Online", 
                                    font=('Segoe UI', 10), 
                                    bg=self.colors.bg_secondary, 
                                    fg=self.colors.text_secondary)
        self.status_label.pack(side='left')
        
        # DateTime
        self.datetime_label = tk.Label(right_section, 
                                     text=datetime.now().strftime("%B %d, %Y • %I:%M %p"),
                                     font=('Segoe UI', 9), 
                                     bg=self.colors.bg_secondary, 
                                     fg=self.colors.text_muted)
        self.datetime_label.pack(anchor='se')
        
        # Close button
        close_btn = tk.Label(right_section, text="✕", 
                            font=('Segoe UI', 18), 
                            bg=self.colors.bg_secondary, 
                            fg=self.colors.text_muted,
                            cursor='hand2')
        close_btn.pack(side='right', padx=(20, 0))
        close_btn.bind('<Button-1>', lambda e: self.trigger_callback('close'))
        close_btn.bind('<Enter>', lambda e: close_btn.config(fg=self.colors.accent_danger))
        close_btn.bind('<Leave>', lambda e: close_btn.config(fg=self.colors.text_muted))
        
        # Enable dragging if requested (for kiosk mode)
        if self.enable_dragging:
            self.setup_dragging()

    def create_user_info_section(self, parent):
        """Create the user info section with dynamic user data."""
        user_frame = tk.Frame(parent, bg=self.colors.bg_primary, 
                             relief='flat', bd=1)
        user_frame.pack(side='left', padx=(0, 20), pady=5)
        
        user_inner = tk.Frame(user_frame, bg=self.colors.bg_primary)
        user_inner.pack(padx=15, pady=8)
        
        user_icon = tk.Label(user_inner, text="👤", font=('Segoe UI', 14), 
                            bg=self.colors.bg_primary, fg=self.colors.accent_primary)
        user_icon.pack(side='left', padx=(0, 8))
        
        # Format user name from user data
        user_name = self.get_display_name()
        self.user_name_label = tk.Label(user_inner, text=user_name, 
                                       font=('Segoe UI', 11, 'bold'), 
                                       bg=self.colors.bg_primary, 
                                       fg=self.colors.text_primary)
        self.user_name_label.pack(side='left')

    def get_display_name(self):
        """Get formatted display name from user data."""
        if not self.user_data:
            return "Guest User"
        
        first_name = self.user_data.get('firstName', '')
        last_name = self.user_data.get('lastName', '')
        email = self.user_data.get('email', '')
        
        # Try to build full name
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        elif email:
            return email.split('@')[0]  # Use part before @ as display name
        else:
            return "Authenticated User"

    def set_user_info(self, user_data):
        """Update user information dynamically."""
        self.user_data = user_data
        if self.user_name_label and user_data:
            display_name = self.get_display_name()
            self.user_name_label.config(text=display_name)
            print(f"🔄 Header updated with user: {display_name}")

    def update_status(self, status_text: str, is_online: bool = True):
        """Update the system status."""
        if self.status_label:
            self.status_label.config(text=status_text)
            self.status_dot.config(fg=self.colors.accent_success if is_online else self.colors.accent_danger)
            
    def update_datetime(self):
        """Update the datetime display."""
        if self.datetime_label:
            self.datetime_label.config(text=datetime.now().strftime("%B %d, %Y • %I:%M %p"))
            
    def setup_dragging(self):
        """Setup window dragging from the header."""
        def start_drag(event):
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            
        def on_drag(event):
            # Get the main window (traverse up the widget hierarchy)
            root = self.frame
            while root.master:
                root = root.master
                
            # Calculate new position
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            
            # Get current position and add the delta
            current_x = root.winfo_x()
            current_y = root.winfo_y()
            
            new_x = current_x + x
            new_y = current_y + y
            
            # Set new position
            root.geometry(f"+{new_x}+{new_y}")
            
            # Update drag start position for next movement
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            
        # Bind dragging to the header frame (not individual labels)
        self.frame.bind('<Button-1>', start_drag)
        self.frame.bind('<B1-Motion>', on_drag)
        
        # Also bind to the inner header for better grab area
        for child in self.frame.winfo_children():
            if isinstance(child, tk.Frame):
                child.bind('<Button-1>', start_drag)
                child.bind('<B1-Motion>', on_drag)
                
        # Change cursor to indicate draggable area
        self.frame.config(cursor="fleur")

class SensorCard(BaseComponent):
    """Reusable sensor card component."""
    
    def __init__(self, parent, icon, value, unit, label, status, color, colors=None):
        super().__init__(parent, colors)
        self.icon = icon
        self.value = value
        self.unit = unit
        self.label = label
        self.status = status
        self.color = color
        self.value_label = None
        self.status_label = None
        self.icon_label = None
        self.icon_manager = get_icon_manager()
        self.create_card()
        
    def create_card(self):
        # Card container with subtle shadow
        self.frame = tk.Frame(self.parent, bg=self.colors.border, relief='flat', bd=1)
        
        # Card content
        content = tk.Frame(self.frame, bg=self.colors.bg_card)
        content.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Inner padding
        inner_content = tk.Frame(content, bg=self.colors.bg_card)
        inner_content.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Icon with colored background
        icon_frame = tk.Frame(inner_content, bg=self.color, width=50, height=50)
        icon_frame.pack(pady=(0, 20))
        icon_frame.pack_propagate(False)
        
        # Use icon manager to create icon label
        self.icon_label = self.icon_manager.create_icon_label(
            icon_frame, 
            self.icon, 
            size=24,  # Smaller size for card icons
            bg=self.color
        )
        
        # If no image was loaded, fall back to text
        if not hasattr(self.icon_label, 'image') or not self.icon_label.image:
            self.icon_label.config(text=self.icon, font=('Segoe UI', 20))
            
        self.icon_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Value and unit
        value_frame = tk.Frame(inner_content, bg=self.colors.bg_card)
        value_frame.pack()
        
        self.value_label = tk.Label(value_frame, text=str(self.value), 
                                   font=('Segoe UI', 36, 'bold'),
                                   bg=self.colors.bg_card, 
                                   fg=self.colors.text_primary)
        self.value_label.pack(side='left')
        
        unit_label = tk.Label(value_frame, text=self.unit, 
                             font=('Segoe UI', 18),
                             bg=self.colors.bg_card, 
                             fg=self.colors.text_secondary)
        unit_label.pack(side='left', padx=(5, 0))
        
        # Label
        label_text = tk.Label(inner_content, text=self.label.upper(), 
                             font=('Segoe UI', 10, 'bold'),
                             bg=self.colors.bg_card, 
                             fg=self.colors.text_muted)
        label_text.pack(pady=(10, 20))
        
        # Status badge
        status_frame = tk.Frame(inner_content, bg=self.color)
        status_frame.pack(fill='x')
        
        self.status_label = tk.Label(status_frame, text=self.status.upper(), 
                                    font=('Segoe UI', 9, 'bold'),
                                    bg=self.color, fg='white', pady=8)
        self.status_label.pack()
        
    def update_data(self, value, status=None, color=None):
        """Update the card's data."""
        self.value = value
        if self.value_label:
            self.value_label.config(text=str(value))
            
        if status is not None:
            self.status = status
            if self.status_label:
                self.status_label.config(text=status.upper())
                
        if color is not None:
            self.color = color
            # Update color elements
            for widget in self.frame.winfo_children():
                self._update_widget_colors(widget, color)
                
    def _update_widget_colors(self, widget, color):
        """Recursively update widget colors."""
        try:
            if widget.winfo_class() == 'Frame' and widget['bg'] == self.color:
                widget.config(bg=color)
            elif widget.winfo_class() == 'Label' and widget['bg'] == self.color:
                widget.config(bg=color)
            
            for child in widget.winfo_children():
                self._update_widget_colors(child, color)
        except tk.TclError:
            pass

class MedicationCard(BaseComponent):
    """Card component for displaying medication information."""
    
    def __init__(self, parent, medication_name="Aspirin", dosage="100mg • 1 tablet", 
                 time_until="2 hours", schedule_time="2:00 PM", pills_remaining=14, colors=None):
        super().__init__(parent, colors)
        self.medication_name = medication_name
        self.dosage = dosage
        self.time_until = time_until
        self.schedule_time = schedule_time
        self.pills_remaining = pills_remaining
        self.icon_manager = get_icon_manager()
        self.create_card()
        
    def create_card(self):
        # Card container
        self.frame = tk.Frame(self.parent, bg=self.colors.border, relief='flat', bd=1)
        
        # Card content
        content = tk.Frame(self.frame, bg=self.colors.bg_card)
        content.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Inner padding
        inner_content = tk.Frame(content, bg=self.colors.bg_card)
        inner_content.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Header
        header_frame = tk.Frame(inner_content, bg=self.colors.bg_card)
        header_frame.pack(fill='x', pady=(0, 20))
        
        # Use icon manager for pill icon
        pill_icon = self.icon_manager.create_icon_label(
            header_frame, 
            'pill', 
            size=24,
            bg=self.colors.bg_card
        )
        
        # If no image was loaded, fall back to emoji
        if not hasattr(pill_icon, 'image') or not pill_icon.image:
            pill_icon.config(text="💊", font=('Segoe UI', 24), fg=self.colors.accent_primary)
            
        pill_icon.pack(side='left', padx=(0, 15))
        
        header_text = tk.Frame(header_frame, bg=self.colors.bg_card)
        header_text.pack(side='left', fill='x', expand=True)
        
        next_med = tk.Label(header_text, text="NEXT MEDICATION", 
                           font=('Segoe UI', 10, 'bold'),
                           bg=self.colors.bg_card, 
                           fg=self.colors.accent_secondary)
        next_med.pack(anchor='w')
        
        self.time_until_label = tk.Label(header_text, text=f"in {self.time_until}", 
                                        font=('Segoe UI', 9),
                                        bg=self.colors.bg_card, 
                                        fg=self.colors.accent_warning)
        self.time_until_label.pack(anchor='w')
        
        # Medication info
        med_frame = tk.Frame(inner_content, bg=self.colors.bg_secondary, 
                            relief='flat', bd=1)
        med_frame.pack(fill='x', pady=(0, 15))
        
        med_inner = tk.Frame(med_frame, bg=self.colors.bg_secondary)
        med_inner.pack(padx=20, pady=20)
        
        self.med_name_label = tk.Label(med_inner, text=self.medication_name, 
                                      font=('Segoe UI', 22, 'bold'),
                                      bg=self.colors.bg_secondary, 
                                      fg=self.colors.accent_primary)
        self.med_name_label.pack()
        
        self.dosage_label = tk.Label(med_inner, text=self.dosage, 
                                    font=('Segoe UI', 13),
                                    bg=self.colors.bg_secondary, 
                                    fg=self.colors.text_secondary)
        self.dosage_label.pack(pady=(5, 0))
        
        # Time display
        time_frame = tk.Frame(inner_content, bg=self.colors.accent_primary, 
                             relief='flat', bd=1)
        time_frame.pack(fill='x', pady=(0, 15))
        
        self.time_label = tk.Label(time_frame, text=f"⏰  {self.schedule_time}", 
                                  font=('Segoe UI', 15, 'bold'),
                                  bg=self.colors.accent_primary, 
                                  fg='white',
                                  pady=14)
        self.time_label.pack()
        
        # Pills remaining
        pills_frame = tk.Frame(inner_content, bg=self.colors.bg_card)
        pills_frame.pack(fill='x')
        
        pills_icon = tk.Label(pills_frame, text="📦", 
                             font=('Segoe UI', 12),
                             bg=self.colors.bg_card, 
                             fg=self.colors.accent_secondary)
        pills_icon.pack(side='left', padx=(0, 8))
        
        self.pills_label = tk.Label(pills_frame, text=f"{self.pills_remaining} pills remaining", 
                                   font=('Segoe UI', 10),
                                   bg=self.colors.bg_card, 
                                   fg=self.colors.text_secondary)
        self.pills_label.pack(side='left')
        
    def update_medication(self, name=None, dosage=None, time_until=None, 
                         schedule_time=None, pills_remaining=None):
        """Update medication information."""
        if name is not None:
            self.medication_name = name
            self.med_name_label.config(text=name)
            
        if dosage is not None:
            self.dosage = dosage
            self.dosage_label.config(text=dosage)
            
        if time_until is not None:
            self.time_until = time_until
            self.time_until_label.config(text=f"in {time_until}")
            
        if schedule_time is not None:
            self.schedule_time = schedule_time
            self.time_label.config(text=f"⏰  {schedule_time}")
            
        if pills_remaining is not None:
            self.pills_remaining = pills_remaining
            self.pills_label.config(text=f"{pills_remaining} pills remaining")

class ActionButton(BaseComponent):
    """Modern action button component."""
    
    def __init__(self, parent, text, icon, bg_color, command=None, colors=None):
        super().__init__(parent, colors)
        self.text = text
        self.icon = icon
        self.bg_color = bg_color
        self.command = command
        self.button = None
        self.create_button()
        
    def create_button(self):
        self.button = tk.Button(self.parent, 
                               text=f"{self.icon}  {self.text}",
                               font=('Segoe UI', 14, 'bold'), 
                               bg=self.bg_color,
                               fg='white',
                               relief='flat',
                               bd=0,
                               cursor='hand2',
                               padx=40,
                               pady=20,
                               command=self._on_click)
        
        self.add_button_effects(self.button)
        
    def _on_click(self):
        """Handle button click."""
        if self.command:
            self.command()
        self.trigger_callback('click')
        
    def pack(self, **kwargs):
        """Pack the button."""
        self.button.pack(**kwargs)
        
    def grid(self, **kwargs):
        """Grid the button."""
        self.button.grid(**kwargs)
        
    def set_enabled(self, enabled: bool):
        """Enable or disable the button."""
        state = 'normal' if enabled else 'disabled'
        self.button.config(state=state)

class EnhancedSensorCard(SensorCard):
    """Enhanced sensor card with capture button and improved styling."""
    
    def __init__(self, parent, icon, value, unit, label, status, color, colors=None, capture_callback=None):
        self.capture_callback = capture_callback
        super().__init__(parent, icon, value, unit, label, status, color, colors)
        
    def create_card(self):
        # Card container with enhanced shadow effect
        self.frame = tk.Frame(self.parent, bg='#D0D0D0', relief='flat', bd=1)
        
        # Card content with gradient-like effect
        content = tk.Frame(self.frame, bg=self.colors.bg_card)
        content.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Inner padding with professional spacing
        inner_content = tk.Frame(content, bg=self.colors.bg_card)
        inner_content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header with icon and title
        header_frame = tk.Frame(inner_content, bg=self.colors.bg_card)
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Icon with modern circular background
        icon_container = tk.Frame(header_frame, bg=self.colors.bg_card)
        icon_container.pack(side='left')
        
        self.icon_frame = tk.Frame(icon_container, bg=self.color, width=45, height=45)
        self.icon_frame.pack()
        self.icon_frame.pack_propagate(False)
        
        # Use icon manager for better icon handling
        self.icon_label = self.icon_manager.create_icon_label(
            self.icon_frame,
            self.icon,
            size=20,
            bg=self.color
        )
        
        # Fallback to text if no image
        if not hasattr(self.icon_label, 'image') or not self.icon_label.image:
            self.icon_label.config(text=self.icon, font=('Segoe UI', 18), fg='white')
            
        self.icon_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Sensor label next to icon
        sensor_label = tk.Label(header_frame, text=self.label.upper(),
                               font=('Segoe UI', 10, 'bold'),
                               bg=self.colors.bg_card,
                               fg=self.colors.text_muted)
        sensor_label.pack(side='left', padx=(15, 0), anchor='w')
        
        # Main value display with enhanced typography
        value_container = tk.Frame(inner_content, bg=self.colors.bg_card)
        value_container.pack(pady=(0, 10))
        
        self.value_label = tk.Label(value_container, text=str(self.value),
                                   font=('Segoe UI', 42, 'bold'),
                                   bg=self.colors.bg_card,
                                   fg=self.colors.text_primary)
        self.value_label.pack(side='left')
        
        unit_label = tk.Label(value_container, text=self.unit,
                             font=('Segoe UI', 16),
                             bg=self.colors.bg_card,
                             fg=self.colors.text_secondary)
        unit_label.pack(side='left', padx=(8, 0), anchor='s', pady=(0, 8))
        
        # Status badge with modern styling
        self.status_frame = tk.Frame(inner_content, bg=self.color, height=35)
        self.status_frame.pack(fill='x', pady=(0, 15))
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame, text=self.status.upper(),
                                    font=('Segoe UI', 9, 'bold'),
                                    bg=self.color, fg='white')
        self.status_label.pack(expand=True)
        
        # Capture button with modern styling
        if self.capture_callback:
            self.capture_btn = tk.Button(inner_content,
                                        text="📸 CAPTURE",
                                        font=('Segoe UI', 10, 'bold'),
                                        bg=self.colors.accent_secondary,
                                        fg='white',
                                        relief='flat',
                                        bd=0,
                                        cursor='hand2',
                                        pady=8,
                                        command=self.capture_callback)
            self.capture_btn.pack(fill='x')
            
            # Add button hover effects
            self.add_button_effects(self.capture_btn)
    
    def update_data(self, value, status=None, color=None):
        """Update the enhanced card's data with animations."""
        # Animate value change
        if self.value != value and self.value_label:
            # Brief highlight effect
            original_fg = self.value_label['fg']
            self.value_label.config(fg=self.colors.accent_primary)
            self.value_label.after(200, lambda: self.value_label.config(fg=original_fg))
        
        # Call parent update method
        super().update_data(value, status, color)