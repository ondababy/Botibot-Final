# app.py
from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json
import threading
from datetime import datetime
import time
from config import *
from player import AudioPlayer

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Audio playback control
audio_lock = threading.Lock()
audio_playing = False

# Global variables to store sensor data
sensor_data = {
    'gyro': {'x': 0, 'y': 0, 'z': 0, 'timestamp': datetime.now().isoformat()},
    'accel': {'x': 0, 'y': 0, 'z': 0, 'timestamp': datetime.now().isoformat()},
    'temp': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'distance': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'weight_value': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'weight_status': {'status': 'unknown', 'timestamp': datetime.now().isoformat()},
    'gyro_y': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'gyro_z': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'load': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'bpm': {'value': 0, 'timestamp': datetime.now().isoformat()},
    'alcohol': {'value': 0, 'timestamp': datetime.now().isoformat()},
}

# Audio alert thresholds and tracking
AUDIO_THRESHOLDS = {
    'temp_high': 37.5,  # High fever threshold in Celsius
    'temp_low': 35.0,   # Low body temp threshold
    'bpm_high': 100,    # High BPM threshold
    'bpm_low': 60,      # Low BPM threshold
    'alcohol_detected': 0.1,  # Alcohol detection threshold
    'motion_threshold': 5.0,  # Motion detection threshold
}

# Track last audio alerts to prevent spam
last_audio_alerts = {
    'high_temp': 0,
    'low_temp': 0,
    'high_bpm': 0,
    'low_bpm': 0,
    'normal_bpm': 0,
    'alcohol': 0,
    'motion': 0,
    'mqtt_connected': 0,
    'system_startup': 0,
}

AUDIO_COOLDOWN = 30  # Seconds between repeated audio alerts

# MQTT connection status
mqtt_connected = False

# Initialize Audio Player
audio_player = AudioPlayer(verbose=True)

# MQTT Client Setup
mqtt_client = mqtt.Client()

def should_play_audio_alert(alert_type: str) -> bool:
    """Check if enough time has passed since last audio alert"""
    current_time = time.time()
    if current_time - last_audio_alerts.get(alert_type, 0) >= AUDIO_COOLDOWN:
        last_audio_alerts[alert_type] = current_time
        return True
    return False

def play_audio_threaded(func, *args):
    """Play audio in a separate thread to avoid blocking - only one audio at a time"""
    global audio_playing
    
    def audio_task():
        global audio_playing
        
        # Check if audio is already playing
        if not audio_lock.acquire(blocking=False):
            print(f"🔇 Audio skipped - another audio is playing: {func.__name__}")
            return
        
        try:
            audio_playing = True
            success = func(*args)
            if not success:
                print(f"⚠️ Audio playback failed for {func.__name__} with args {args}")
        except Exception as e:
            print(f"❌ Audio error in {func.__name__}: {e}")
        finally:
            audio_playing = False
            audio_lock.release()
    
    thread = threading.Thread(target=audio_task, daemon=True)
    thread.start()

def check_and_play_audio_alerts(sensor_type: str, value: float = None):
    """Check sensor values and play audio alerts when thresholds are exceeded"""
    try:
        if sensor_type == 'temp' and value is not None:
            if value >= AUDIO_THRESHOLDS['temp_high'] and should_play_audio_alert('high_temp'):
                play_audio_threaded(audio_player.play_health_alert, 'high_temp')
                print(f"🔊 High temperature alert: {value}°C")
            elif value <= AUDIO_THRESHOLDS['temp_low'] and should_play_audio_alert('low_temp'):
                play_audio_threaded(audio_player.play_health_alert, 'temp_measure')
                print(f"🔊 Low temperature alert: {value}°C")
        
        elif sensor_type == 'bpm' and value is not None:
            if value >= AUDIO_THRESHOLDS['bpm_high'] and should_play_audio_alert('high_bpm'):
                play_audio_threaded(audio_player.play_health_alert, 'high_bpm')
                print(f"🔊 High BPM alert: {value}")
            elif value > 0 and value <= AUDIO_THRESHOLDS['bpm_low'] and should_play_audio_alert('low_bpm'):
                play_audio_threaded(audio_player.play_health_alert, 'normal_bpm')
                print(f"🔊 Low BPM alert: {value}")
            elif value > 0 and 60 <= value < 100 and should_play_audio_alert('normal_bpm'):
                # Normal BPM detected
                play_audio_threaded(audio_player.play_health_alert, 'normal_bpm')
                print(f"🔊 Normal BPM detected: {value}")
        
        elif sensor_type == 'alcohol' and value is not None:
            if value >= AUDIO_THRESHOLDS['alcohol_detected'] and should_play_audio_alert('alcohol'):
                play_audio_threaded(audio_player.play_health_alert, 'alcohol_detected')
                print(f"🔊 Alcohol detected alert: {value}")
        
        elif sensor_type == 'motion' and value is not None:
            if abs(value) >= AUDIO_THRESHOLDS['motion_threshold'] and should_play_audio_alert('motion'):
                play_audio_threaded(audio_player.play_motion_alert)
                print(f"🔊 Motion detected alert: {value}")
                
    except Exception as e:
        print(f"Error in audio alert system: {e}")

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print(f"Successfully connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        # Play system online sound
        if should_play_audio_alert('mqtt_connected'):
            play_audio_threaded(audio_player.play_system_status, 'online')
    else:
        mqtt_connected = False
        print(f"Failed to connect to MQTT broker with result code {rc}")
        # Play error sound
        play_audio_threaded(audio_player.play_system_status, 'error')
    
    # Subscribe to all topics
    for topic in TOPICS.values():
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = msg.payload.decode()
        timestamp = datetime.now().isoformat()
        
        # Process different topics
        if topic == TOPICS['gyro']:
            data = json.loads(payload)
            sensor_data['gyro'] = {**data, 'timestamp': timestamp}
            # Check for significant motion
            if 'x' in data and 'y' in data and 'z' in data:
                motion_magnitude = (data['x']**2 + data['y']**2 + data['z']**2)**0.5
                check_and_play_audio_alerts('motion', motion_magnitude)
        elif topic == TOPICS['accel']:
            data = json.loads(payload)
            sensor_data['accel'] = {**data, 'timestamp': timestamp}
            # Check for significant acceleration/motion
            if 'x' in data and 'y' in data and 'z' in data:
                accel_magnitude = (data['x']**2 + data['y']**2 + data['z']**2)**0.5
                check_and_play_audio_alerts('motion', accel_magnitude)
        elif topic == TOPICS['temp']:
            # Handle both JSON and simple float formats
            try:
                temp_data = json.loads(payload)
                # Check if it's a dictionary with temperature data
                if isinstance(temp_data, dict):
                    if 'temp' in temp_data:
                        temp_value = float(temp_data['temp'])
                        sensor_data['temp'] = {'value': temp_value, 'timestamp': timestamp}
                        check_and_play_audio_alerts('temp', temp_value)
                    elif 'temperature' in temp_data:
                        temp_value = float(temp_data['temperature'])
                        sensor_data['temp'] = {'value': temp_value, 'timestamp': timestamp}
                        check_and_play_audio_alerts('temp', temp_value)
                    else:
                        # If it's a dict but no recognized key, try to get the first numeric value
                        for key, value in temp_data.items():
                            try:
                                temp_value = float(value)
                                sensor_data['temp'] = {'value': temp_value, 'timestamp': timestamp}
                                check_and_play_audio_alerts('temp', temp_value)
                                break
                            except (ValueError, TypeError):
                                continue
                else:
                    # If it's not a dict (could be a plain number), use it directly
                    temp_value = float(temp_data)
                    sensor_data['temp'] = {'value': temp_value, 'timestamp': timestamp}
                    check_and_play_audio_alerts('temp', temp_value)
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as plain float
                temp_value = float(payload)
                sensor_data['temp'] = {'value': temp_value, 'timestamp': timestamp}
                check_and_play_audio_alerts('temp', temp_value)
        elif topic == TOPICS['distance']:
            sensor_data['distance'] = {'value': float(payload), 'timestamp': timestamp}
        elif topic == TOPICS['weight_value']:
            sensor_data['weight_value'] = {'value': float(payload), 'timestamp': timestamp}
        elif topic == TOPICS['weight_status']:
            sensor_data['weight_status'] = {'status': payload, 'timestamp': timestamp}
        elif topic == TOPICS['gyro_y']:
            sensor_data['gyro_y'] = {'value': float(payload), 'timestamp': timestamp}
        elif topic == TOPICS['gyro_z']:
            sensor_data['gyro_z'] = {'value': float(payload), 'timestamp': timestamp}
        elif topic == TOPICS['load']:
            sensor_data['load'] = {'value': float(payload), 'timestamp': timestamp}
        elif topic == TOPICS['bpm']:
            bpm_value = float(payload)
            sensor_data['bpm'] = {'value': bpm_value, 'timestamp': timestamp}
            check_and_play_audio_alerts('bpm', bpm_value)
        elif topic == TOPICS['alcohol']:
            # Handle both JSON and simple float formats
            try:
                alcohol_data = json.loads(payload)
                if 'alcohol_level' in alcohol_data:
                    alcohol_value = float(alcohol_data['alcohol_level'])
                    sensor_data['alcohol'] = {'value': alcohol_value, 'timestamp': timestamp}
                    check_and_play_audio_alerts('alcohol', alcohol_value)
                elif 'alcohol' in alcohol_data:
                    alcohol_value = float(alcohol_data['alcohol'])
                    sensor_data['alcohol'] = {'value': alcohol_value, 'timestamp': timestamp}
                    check_and_play_audio_alerts('alcohol', alcohol_value)
                else:
                    alcohol_value = float(payload)
                    sensor_data['alcohol'] = {'value': alcohol_value, 'timestamp': timestamp}
                    check_and_play_audio_alerts('alcohol', alcohol_value)
            except json.JSONDecodeError:
                alcohol_value = float(payload)
                sensor_data['alcohol'] = {'value': alcohol_value, 'timestamp': timestamp}
                check_and_play_audio_alerts('alcohol', alcohol_value)
        
    except Exception as e:
        print(f"Error processing message from {topic}: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Flask Routes
@app.route("/")
def dashboard():
    return render_template('dashboard.html')

@app.route("/api/sensor-data")
def get_sensor_data():
    return jsonify(sensor_data)

@app.route("/api/mqtt-status")
def get_mqtt_status():
    return jsonify({
        'connected': mqtt_connected,
        'broker': MQTT_BROKER,
        'port': MQTT_PORT
    })

@app.route("/api/control/servo", methods=['POST'])
def control_servo():
    try:
        data = request.get_json()
        angle = data.get('angle', 0)
        
        # Publish servo control command
        mqtt_client.publish(TOPICS['servo'], str(angle))
        
        # Play user interaction sound
        play_audio_threaded(audio_player.play_user_interaction, 'press_button')
        
        return jsonify({'status': 'success', 'message': f'Servo set to {angle} degrees'})
    except Exception as e:
        play_audio_threaded(audio_player.play_system_status, 'error')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route("/api/control/stepper", methods=['POST'])
def control_stepper():
    try:
        data = request.get_json()
        steps = data.get('steps', 0)
        direction = data.get('direction', 'CW')
        
        command = {'steps': steps, 'direction': direction}
        mqtt_client.publish(TOPICS['stepper'], json.dumps(command))
        
        # Play user interaction sound
        play_audio_threaded(audio_player.play_user_interaction, 'press_button')
        
        return jsonify({'status': 'success', 'message': f'Stepper moved {steps} steps {direction}'})
    except Exception as e:
        play_audio_threaded(audio_player.play_system_status, 'error')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route("/api/audio/test", methods=['POST'])
def test_audio():
    """Test audio playback with specific sound"""
    try:
        data = request.get_json()
        sound_name = data.get('sound_name', 'system_online')
        
        # Play the requested sound in a separate thread
        success = False
        if sound_name in ['high_temp', 'high_bpm', 'normal_bpm', 'alcohol_detected', 'temp_measure']:
            success = audio_player.play_health_alert(sound_name)
        elif sound_name in ['online', 'error', 'setup_complete', 'sensors_active', 'scan_start']:
            success = audio_player.play_system_status(sound_name)
        elif sound_name == 'motion':
            success = audio_player.play_motion_alert()
        elif sound_name in ['identified', 'touch_screen', 'press_button', 'do_not_move']:
            success = audio_player.play_user_interaction(sound_name)
        else:
            success = audio_player.play_sound(sound_name)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': f'Audio test {"successful" if success else "failed"} for sound: {sound_name}',
            'sound_played': sound_name
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route("/api/audio/available")
def get_available_sounds():
    """Get list of available audio files"""
    try:
        available_sounds = audio_player.list_available_sounds()
        return jsonify({
            'status': 'success',
            'sounds': available_sounds,
            'sound_categories': {
                'health_alerts': ['high_temp', 'high_bpm', 'normal_bpm', 'alcohol_detected', 'temp_measure'],
                'system_status': ['online', 'error', 'setup_complete', 'sensors_active', 'scan_start'],
                'user_interaction': ['identified', 'touch_screen', 'press_button', 'do_not_move'],
                'motion': ['motion']
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route("/api/audio/status")
def get_audio_status():
    """Get current audio alert status and thresholds"""
    return jsonify({
        'thresholds': AUDIO_THRESHOLDS,
        'last_alerts': last_audio_alerts,
        'cooldown_seconds': AUDIO_COOLDOWN,
        'audio_enabled': True,
        'audio_player_status': 'ready',
        'audio_currently_playing': audio_playing
    })

def start_mqtt():
    try:
        if MQTT_USERNAME and MQTT_PASSWORD:
            mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        play_audio_threaded(audio_player.play_system_status, 'error')

if __name__ == "__main__":
    # Start MQTT client in a separate thread
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # Play startup sound
    print("🎵 Starting BotiBot Web Server...")
    if should_play_audio_alert('system_startup'):
        play_audio_threaded(audio_player.play_system_status, 'setup_complete')
    
    # Announce sensors are active
    time.sleep(2)  # Brief delay before next sound
    play_audio_threaded(audio_player.play_system_status, 'sensors_active')
    
    # Start Flask server
    app.run(debug=DEBUG, port=PORT, host=HOST)
