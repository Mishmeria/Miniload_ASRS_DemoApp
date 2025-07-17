import socket
import requests
import sys

def test_socket_connection(host, port):
    """Test if we can connect to the host:port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"✅ Socket connection to {host}:{port} successful")
            return True
        else:
            print(f"❌ Cannot connect to {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Error testing socket connection: {e}")
        return False
    finally:
        sock.close()  # type: ignore

def test_http_connection(url):
    """Test if we can make an HTTP request to the URL"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ HTTP connection to {url} successful (Status: {response.status_code})")
            return True
        else:
            print(f"⚠️ HTTP connection to {url} returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP connection to {url} failed: {e}")
        return False

if __name__ == "__main__":
    # Default values
    host = "191.20.208.7"
    port = 8080
    
    # Check if custom host/port provided
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    print(f"Testing connection to {host}:{port}...")
    
    # Test socket connection
    socket_ok = test_socket_connection(host, port)
    
    # Test HTTP connection if socket is OK
    if socket_ok:
        url = f"http://{host}:{port}"
        test_http_connection(url)
    
    print("\nTroubleshooting tips:")
    print("1. Make sure the web server is running")
    print("2. Check firewall settings to ensure port 8080 is open")
    print("3. Verify you're on the same network or have network access to the server")
    print("4. Try accessing the web app directly in a browser: http://191.20.208.7:8080")