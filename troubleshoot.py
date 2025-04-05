import socket
import time
import sys

def test_car_connection(car_ip="192.168.4.1", car_port=100, test_commands=None):
    """Test connection and command response with the car"""
    if test_commands is None:
        test_commands = ["FORWARD", "LEFT", "RIGHT", "BACKWARD", "STOP"]
    
    print(f"Testing connection to car at {car_ip}:{car_port}")
    
    # Create socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)  # 1 second timeout
        print("Socket created successfully")
    except socket.error as e:
        print(f"Socket creation failed: {e}")
        return False
    
    # Test each command
    for cmd in test_commands:
        try:
            print(f"Sending command: {cmd}")
            sock.sendto(cmd.encode(), (car_ip, car_port))
            print(f"Command {cmd} sent successfully")
            time.sleep(1)  # Wait for car to execute command
        except Exception as e:
            print(f"Failed to send command {cmd}: {e}")
    
    sock.close()
    print("Connection test completed")
    
    return True

def check_network():
    """Check network settings for potential issues"""
    print("Checking network configuration...")
    
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Hostname: {hostname}")
        print(f"Local IP: {local_ip}")
        
        # Check if on same subnet as car (assuming car is on 192.168.4.x)
        if not local_ip.startswith("192.168.4."):
            print("WARNING: Your computer appears to be on a different subnet than the car.")
            print("The car typically uses 192.168.4.x network.")
            print("You may need to connect to the car's Wi-Fi network.")
    except Exception as e:
        print(f"Failed to check network: {e}")

if __name__ == "__main__":
    print("Car Connection Troubleshooter")
    print("-----------------------------")
    
    # Check network first
    check_network()
    
    # Get car IP from command line if provided
    car_ip = "192.168.4.1"  # Default
    if len(sys.argv) > 1:
        car_ip = sys.argv[1]
    
    # Test connection
    test_car_connection(car_ip)
    
    print("\nTroubleshooting tips:")
    print("1. Make sure you're connected to the car's Wi-Fi network")
    print("2. Verify the car is powered on and in control mode")
    print("3. Check that the car's IP and port settings match your code")
    print("4. Try restarting both the car and this application")
