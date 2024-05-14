"""Just a file to store all the functions and classes that are no longer used in the project."""


def rfid_raw_test():
    import sys
    print("rfid_raw_test()")
    while True:
        line = sys.stdin.readline().strip()
        if line:
            print(f"RFID card UID: {line}")

def get_usb_device_name(vendor_id, product_id):
    # Run lsusb command and capture its output
    lsusb_output = subprocess.check_output(['lsusb']).decode('utf-8')
    print("lsusb_output:", lsusb_output)

    # Construct regex pattern to match the device line
    pattern = r'ID\s([a-fA-F0-9]+):([a-fA-F0-9]+)'

    # Construct regex pattern to match the device line
    pattern = rf'ID\s{vendor_id}:{product_id}\s(.+)$'

    # Search for the device line using regex
    match = re.search(pattern, lsusb_output, re.MULTILINE)

    if match:
        print("match.groups():", match.groups())
        # Extract the device name from the matched line
        device_name = match.group(1)

        # Find the corresponding device file in /dev/input
        try:
            input_device_path = subprocess.check_output(['find', '/dev/input', '-name', device_name]).decode('utf-8').strip()
            return input_device_path
        except subprocess.CalledProcessError:
            pass

    return None


def get_input_device_path_from_by_id(vendor_id, product_id):
    # Path to the input device directory
    input_device_by_id_dir = '/dev/input/by-id'

    # Get a list of all files in the input device by-id directory
    input_device_files = os.listdir(input_device_by_id_dir)

    # Construct regex pattern to match the device file name
    pattern = re.compile(r'.*?usb-{}.*?{}.*?'.format(vendor_id, product_id))

    # Iterate over each file in the input device by-id directory
    for filename in input_device_files:
        # Check if the file name matches the expected pattern
        if pattern.match(filename):
            # Read the symlink target to get the actual device path
            symlink_target = os.readlink(os.path.join(input_device_by_id_dir, filename))
            return symlink_target

    return None

def usb_get_test():
    print("usb_get_test()")
    # Example usage: Get the device name for a specific vendor and product ID
    vendor_id = 'ffff'  # Replace with your actual vendor ID
    product_id = '0035' # Replace with your actual product ID
    device_name = get_usb_device_name(vendor_id, product_id)

    if device_name:
        print(f"USB device name: {device_name}")
    else:
        print("USB device not found.")