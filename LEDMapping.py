import time
import requests
from io import BytesIO
from PIL import Image

CAMERA_URL = "http://192.168.0.6:3000/snapshot"


def capture_with_led_on(pixel_index, pixels):
    """Turn on one LED, grab a snapshot, turn it off, return the image."""

    # Clear all LEDs
    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(0.1)

    # Light just this one LED (white for max visibility)
    pixels[pixel_index] = (255, 255, 255)
    pixels.show()

    # Give the camera a moment to capture the light
    time.sleep(0.3)

    # Fetch the snapshot
    response = requests.get(CAMERA_URL)
    image = Image.open(BytesIO(response.content))

    # Turn it back off
    pixels[pixel_index] = (0, 0, 0)
    pixels.show()

    return image
