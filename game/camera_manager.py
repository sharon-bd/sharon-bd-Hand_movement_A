# Camera management for handling multiple camera inputs

import cv2

class CameraManager:
    def __init__(self):
        self.cameras = []
        self.active_camera_index = 0
        self.available_cameras = self._find_available_cameras()
    
    def _find_available_cameras(self, max_cameras=2):
        """
        Find available cameras on the system.
        
        Args:
            max_cameras (int): Maximum number of cameras to check
            
        Returns:
            list: List of available camera indices
        """
        available = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
    
    def initialize_cameras(self):
        """
        Initialize the available cameras.
        
        Returns:
            bool: True if at least one camera was initialized, False otherwise
        """
        self.cameras = []
        success = False
        
        for cam_index in self.available_cameras:
            cap = cv2.VideoCapture(cam_index)
            if cap.isOpened():
                self.cameras.append(cap)
                success = True
            else:
                print(f"Failed to open camera {cam_index}")
        
        if success:
            self.active_camera_index = 0  # Default to first camera
        
        return success
    
    def switch_camera(self):
        """
        Switch to the next available camera.
        
        Returns:
            int: Index of the new active camera
        """
        if len(self.cameras) > 1:
            self.active_camera_index = (self.active_camera_index + 1) % len(self.cameras)
        return self.active_camera_index
    
    def set_active_camera(self, index):
        """
        Set a specific camera as active.
        
        Args:
            index (int): Index of the camera to activate
            
        Returns:
            bool: True if successful, False otherwise
        """
        if 0 <= index < len(self.cameras):
            self.active_camera_index = index
            return True
        return False
    
    def get_frame(self):
        """
        Get a frame from the active camera.
        
        Returns:
            tuple: (success, frame) - success is a boolean, frame is the image
        """
        if not self.cameras:
            return False, None
        
        return self.cameras[self.active_camera_index].read()
    
    def release_all(self):
        """Release all camera resources."""
        for cap in self.cameras:
            cap.release()
        self.cameras = []
    
    def get_active_camera_index(self):
        """
        Get the index of the currently active camera.
        
        Returns:
            int: Index of the active camera
        """
        return self.active_camera_index
    
    def get_available_camera_count(self):
        """
        Get the number of available cameras.
        
        Returns:
            int: Number of available cameras
        """
        return len(self.available_cameras)
    
    def get_camera_info(self):
        """
        Get information about all available cameras.
        
        Returns:
            list: List of camera information dictionaries
        """
        camera_info = []
        for i, cam_index in enumerate(self.available_cameras):
            info = {
                "index": cam_index,
                "name": f"Camera {cam_index}",
                "active": i == self.active_camera_index
            }
            camera_info.append(info)
        return camera_info
