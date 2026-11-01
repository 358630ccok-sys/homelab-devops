import subprocess

def get_uptime():
    result = subprocess.run(['uptime'], capture_output=True, text=True)
    return result.stdout.strip()

def get_current_time():
    result = subprocess.run(['date'], capture_output=True, text=True)
    return result.stdout.strip()

if __name__ == '__main__':
    print("Server Uptime:")
    print(get_uptime())
    print("\nCurrent Time:")
    print(get_current_time())
