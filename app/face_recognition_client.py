import requests

import json
from typing import Optional, Dict, Any
import io
from PIL import Image
import time
import threading
import cv2
import base64

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("⚠️ PiCamera2 not available, using fallback method")

class FaceRecognitionClient:
    """Client for communicating with the face recognition server."""
    
    def __init__(self, server_url: str = "http://192.168.1.40:5000"):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10  # Set default timeout
        self.camera = None
        self.preview_active = False  # Add missing attribute
        self.preview_thread = None   # Add missing attribute
        
        # List of possible server URLs to try if main one fails
        self.backup_servers = [
            "http://localhost:5000",
            "http://127.0.0.1:5000", 
            "http://192.168.1.41:5000",
            "http://192.168.1.42:5000"
        ]
        
    def capture_image_from_camera(self) -> Optional[str]:
        """Capture image from PiCamera2 and convert to base64 with face detection and smart countdown."""
        try:
            if not PICAMERA2_AVAILABLE:
                print("❌ Error: PiCamera2 library not available")
                return None
                
            print("📹 Starting camera preview with face detection...")
            
            # Initialize face detection
            face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            
            # Initialize PiCamera2
            self.camera = Picamera2()
            
            # Configure camera for preview
            config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "XRGB8888"}
            )
            self.camera.configure(config)
            
            # Start the camera
            self.camera.start()
            time.sleep(1)  # Let camera warm up
            
            # Smart countdown parameters
            max_wait_time = 20  # Maximum wait time in seconds
            face_detection_delay = 2  # Wait 2 seconds after face detected before capture
            start_time = time.time()
            window_name = "Face Recognition - Smart Detection"
            
            face_detected = False
            face_detection_start = None
            captured_frame = None
            
            print(f"📸 Smart face detection active - up to {max_wait_time}s wait time...")
            
            while time.time() - start_time < max_wait_time:
                frame = self.camera.capture_array()
                frame_bgr = frame  # XRGB8888 format is already compatible with OpenCV BGR
                
                # Detect faces in the frame
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                current_time = time.time()
                elapsed_time = current_time - start_time
                remaining_time = max_wait_time - elapsed_time
                
                # Check if face is detected
                if len(faces) > 0:
                    if not face_detected:
                        # Face just detected
                        face_detected = True
                        face_detection_start = current_time
                        print("✅ Face detected! Preparing to capture...")
                    
                    # Draw rectangle around faces
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(frame_bgr, "Face Detected", (x, y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Check if face has been stable for the delay period
                    if face_detection_start and (current_time - face_detection_start >= face_detection_delay):
                        print("📸 Face stable - capturing now!")
                        captured_frame = frame_bgr.copy()
                        break
                    
                    # Show countdown for face capture
                    face_countdown = face_detection_delay - (current_time - face_detection_start)
                    cv2.putText(frame_bgr, f"Capturing in {face_countdown:.1f}s", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame_bgr, "Face detected - Hold steady!", (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    # No face detected
                    if face_detected:
                        print("⚠️ Face lost - restarting detection...")
                    face_detected = False
                    face_detection_start = None
                    
                    # Show instructions and remaining time
                    cv2.putText(frame_bgr, f"No face detected - {remaining_time:.1f}s left", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame_bgr, "Position your face in the center", (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame_bgr, "Look directly at the camera", (10, 110), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Add timeout warning when getting close to limit
                if remaining_time <= 5 and not face_detected:
                    cv2.putText(frame_bgr, "⚠️ TIMEOUT WARNING ⚠️", (150, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                
                cv2.imshow(window_name, frame_bgr)
                
                # Allow early exit with 'q' or 'Esc'
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or Esc key
                    print("❌ Capture cancelled by user")
                    cv2.destroyWindow(window_name)
                    self.camera.stop()
                    self.camera.close()
                    self.camera = None
                    return None
            
            cv2.destroyWindow(window_name)
            
            # Check if we captured due to face detection or timeout
            if captured_frame is not None:
                print("✅ Face captured successfully!")
                # Flash effect to indicate successful capture
                for _ in range(3):
                    # Green flash for successful detection
                    flash_frame = captured_frame.copy()
                    flash_frame[:, :, 1] = 255  # Green channel
                    cv2.putText(flash_frame, "FACE CAPTURED!", (150, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
                    cv2.imshow(window_name, flash_frame)
                    cv2.waitKey(200)
                    cv2.destroyWindow(window_name)
            else:
                print("⏰ Timeout - no stable face detected")
                # Show timeout message
                timeout_frame = frame_bgr.copy()
                timeout_frame[:, :, 2] = 255  # Red channel
                cv2.putText(timeout_frame, "TIMEOUT - NO FACE DETECTED", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
                cv2.imshow(window_name, timeout_frame)
                cv2.waitKey(2000)  # Show for 2 seconds
                cv2.destroyWindow(window_name)
                
                # Clean up and return None for timeout
                self.camera.stop()
                self.camera.close()
                self.camera = None
                return None
            
            # Capture the final image
            print("📸 Processing captured image...")
            pil_image = self.camera.capture_image()
            
            # Stop and clean up camera
            self.camera.stop()
            self.camera.close()
            self.camera = None
            
            # Convert PIL image to JPEG bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=85)
            img_data = img_byte_arr.getvalue()
            
            # Convert to base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            print(f"✓ Image processed successfully ({len(img_data)} bytes)")
            return img_base64
            
        except Exception as e:
            print(f"❌ Error capturing image: {e}")
            # Clean up camera on error
            if self.camera:
                try:
                    self.camera.stop()
                    self.camera.close()
                    self.camera = None
                except:
                    pass
            # Clean up any open windows
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return None
    
    def capture_with_preview(self, preview_duration: int = 5) -> Optional[str]:
        """Show camera preview for a few seconds, then capture image"""
        try:
            if not PICAMERA2_AVAILABLE:
                print("❌ Error: PiCamera2 library not available")
                return None
                
            print(f"📹 Starting {preview_duration}s camera preview before capture...")
            
            # Initialize PiCamera2
            self.camera = Picamera2()
            
            # Configure camera
            config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "XRGB8888"}
            )
            self.camera.configure(config)
            
            # Start the camera
            self.camera.start()
            time.sleep(1)  # Let camera warm up
            
            # Show preview for specified duration
            start_time = time.time()
            window_name = "Face Recognition Preview"
            
            while time.time() - start_time < preview_duration:
                frame = self.camera.capture_array()
                frame_bgr = frame  # XRGB8888 format is already compatible with OpenCV BGR
                
                # Add countdown overlay
                remaining = int(preview_duration - (time.time() - start_time))
                cv2.putText(frame_bgr, f"Capturing in {remaining}s...", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame_bgr, "Position your face in the frame", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow(window_name, frame_bgr)
                
                # Allow early exit with 'q'
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
            
            cv2.destroyWindow(window_name)
            
            # Capture the final image
            print("📸 Capturing image...")
            pil_image = self.camera.capture_image()
            
            # Clean up camera
            self.camera.stop()
            self.camera.close()
            self.camera = None
            
            # Convert to base64
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=85)
            img_data = img_byte_arr.getvalue()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            print(f"✓ Image captured successfully ({len(img_data)} bytes)")
            return img_base64
            
        except Exception as e:
            print(f"❌ Error during preview and capture: {e}")
            if self.camera:
                try:
                    self.camera.stop()
                    self.camera.close()
                    self.camera = None
                except:
                    pass
            return None
    
    def recognize_face(self, image_base64: str) -> Dict[str, Any]:
        """Send image to server for face recognition."""
        
        # Test connection first and switch servers if needed
        if not self.test_connection():
            return {
                'success': False,
                'error': 'no_server_available',
                'message': 'No face recognition server is reachable'
            }
        
        # List of possible endpoints to try
        endpoints = [
            "/api/auth/face-login",
            "/api/face/recognize", 
            "/api/face/login",
            "/api/auth/recognize",
            "/api/recognize",
            "/login"
        ]
        
        payload = {
            "image": image_base64
        }
        
        for endpoint in endpoints:
            try:
                url = f"{self.server_url}{endpoint}"
                print(f"🔄 Trying endpoint: {url}")
                
                response = self.session.post(
                    url, 
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"📡 Server response: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    print(f"✅ Recognition successful with endpoint: {endpoint}")
                    print(f"✅ Response: {response_data}")
                    return {
                        'success': True,
                        'data': response_data
                    }
                elif response.status_code == 404:
                    print(f"⚠️ Endpoint {endpoint} not found, trying next...")
                    continue
                else:
                    error_text = response.text
                    print(f"❌ Server error {response.status_code} at {endpoint}: {error_text}")
                    # Don't continue on auth errors, they suggest the endpoint exists but needs auth
                    if response.status_code == 401:
                        return {
                            'success': False,
                            'error': f"Authentication required at {endpoint}",
                            'message': error_text,
                            'status_code': response.status_code
                        }
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"⏰ Request timed out for {endpoint} (10s timeout)")
                continue
            except requests.exceptions.ConnectionError:
                print(f"🔗 Connection error for {endpoint}")
                continue
            except Exception as e:
                print(f"❌ Error with {endpoint}: {e}")
                continue
        
        # If we get here, all endpoints failed
        return {
            'success': False,
            'error': 'all_endpoints_failed',
            'message': 'All face recognition endpoints failed or returned errors'
        }
    
    def test_connection(self) -> bool:
        """Test if the server is reachable."""
        print(f"🔍 Testing connection to: {self.server_url}")
        
        # Try main server first
        if self._test_single_server(self.server_url):
            return True
        
        # Try backup servers
        print("⚠️ Main server unreachable, trying backup servers...")
        for backup_url in self.backup_servers:
            print(f"🔄 Trying backup: {backup_url}")
            if self._test_single_server(backup_url):
                print(f"✅ Switching to backup server: {backup_url}")
                self.server_url = backup_url
                return True
        
        print("❌ All servers unreachable")
        return False
    
    def _test_single_server(self, url: str) -> bool:
        """Test connection to a single server URL."""
        try:
            response = self.session.get(f"{url}/", timeout=3)
            is_connected = response.status_code in [200, 404]  # 404 is also OK, means server is running
            if is_connected:
                print(f"🔗 Server {url}: ✅ Connected")
            return is_connected
        except requests.exceptions.Timeout:
            print(f"🔗 Server {url}: ⏰ Timeout")
            return False
        except requests.exceptions.ConnectionError:
            print(f"🔗 Server {url}: 🔌 Connection refused")
            return False
        except Exception as e:
            print(f"🔗 Server {url}: ❌ Error - {e}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_camera_preview()
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                self.camera = None
            except:
                pass
    
    def start_camera_preview(self, window_name: str = "Face Recognition Camera"):
        """Start camera preview in a separate window"""
        try:
            if not PICAMERA2_AVAILABLE:
                print("❌ Error: PiCamera2 library not available for preview")
                return False
                
            if self.preview_active:
                print("⚠️ Camera preview is already active")
                return True
                
            # Initialize PiCamera2 for preview
            self.camera = Picamera2()
            
            # Configure camera for preview (smaller resolution for better performance)
            config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "XRGB8888"}
            )
            self.camera.configure(config)
            
            # Start the camera
            self.camera.start()
            time.sleep(1)  # Let camera warm up
            
            self.preview_active = True
            self.preview_thread = threading.Thread(
                target=self._preview_loop, 
                args=(window_name,), 
                daemon=True
            )
            self.preview_thread.start()
            
            print(f"✓ Camera preview started in window: {window_name}")
            print("📸 Press 'SPACE' to capture for recognition, 'q' to quit preview")
            return True
            
        except Exception as e:
            print(f"❌ Error starting camera preview: {e}")
            self.preview_active = False
            return False
    
    def _preview_loop(self, window_name: str):
        """Internal method for the camera preview loop"""
        try:
            while self.preview_active and self.camera:
                # Capture frame
                frame = self.camera.capture_array()
                
                # XRGB8888 format is already compatible with OpenCV BGR
                frame_bgr = frame
                
                # Add overlay text
                cv2.putText(frame_bgr, "Face Recognition Camera", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame_bgr, "Press SPACE to scan face, 'q' to quit", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Display the frame
                cv2.imshow(window_name, frame_bgr)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop_camera_preview()
                    break
                elif key == ord(' '):  # Space key
                    print("📸 Scanning face...")
                    self._capture_and_recognize()
                    
        except Exception as e:
            print(f"❌ Error in preview loop: {e}")
        finally:
            cv2.destroyAllWindows()
    
    def stop_camera_preview(self):
        """Stop camera preview"""
        try:
            self.preview_active = False
            
            if hasattr(self, 'preview_thread') and self.preview_thread and self.preview_thread.is_alive():
                self.preview_thread.join(timeout=2)
            
            if self.camera:
                self.camera.stop()
                self.camera.close()
                self.camera = None
            
            cv2.destroyAllWindows()
            print("✓ Camera preview stopped")
            
        except Exception as e:
            print(f"❌ Error stopping camera preview: {e}")
    
    def _capture_and_recognize(self):
        """Capture current frame and send for recognition"""
        try:
            if not self.camera:
                print("❌ Camera not available")
                return
                
            # Capture image as PIL Image
            pil_image = self.camera.capture_image()
            
            # Convert PIL image to JPEG bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=85)
            img_data = img_byte_arr.getvalue()
            
            # Convert to base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            print(f"📤 Sending image for recognition ({len(img_data)} bytes)")
            
            # Send for recognition
            result = self.recognize_face(img_base64)
            
            # Display result
            if result.get('success', False) and result.get('data', {}).get('success', False):
                user = result['data']['recognized_user']
                print(f"✅ Face recognized: {user.get('firstName', '')} {user.get('lastName', '')}")
                print(f"📧 Email: {user.get('email', '')}")
                print(f"👤 User ID: {user.get('id', '')}")
                
                if 'access_token' in result['data']:
                    print("🔐 User automatically logged in!")
                    print(f"🎫 Token: {result['data']['access_token'][:20]}...")
                    # Auto-close preview after successful recognition
                    print("🎉 Recognition successful! Closing preview in 3 seconds...")
                    time.sleep(3)
                    self.stop_camera_preview()
            else:
                print("❌ Face not recognized")
                confidence_data = result.get('data', {}).get('confidence_data', {})
                confidence = confidence_data.get('confidence', 0)
                accuracy = confidence_data.get('accuracy', 0)
                print(f"🎯 Confidence: {confidence:.2f}")
                print(f"📊 Accuracy: {accuracy:.2f}")
                print("💡 Try adjusting your position and lighting")
                
        except Exception as e:
            print(f"❌ Error during capture and recognition: {e}")
    
    def capture_and_recognize_with_preview(self) -> Dict[str, Any]:
        """Start camera preview and capture/recognize when user presses space"""
        print("🚀 Starting face recognition with camera preview...")
        
        # Start camera preview
        if self.start_camera_preview():
            print("📹 Camera preview active. Position yourself in front of the camera.")
            print("💡 Press SPACE when ready to scan your face")
            
            # Keep the main thread alive while preview is running
            try:
                while self.preview_active:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n⏹️ Interrupted by user")
                self.stop_camera_preview()
                
            return {"message": "Preview session ended"}
        else:
            return {"error": "Failed to start camera preview"}
