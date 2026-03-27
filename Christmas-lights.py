from flask import Flask, request, jsonify
import board
import neopixel
import time
import random
import threading
import requests
import json
import os
import math

app = Flask(__name__)

# Configure for 150 LEDs on GPIO 18
pixels = neopixel.NeoPixel(board.D18, 150, brightness=0.2, auto_write=False)

current_effect = None
effect_thread = None
stop_effect = False

# Path to LED coordinates
COORDINATES_FILE = #path

# Load coordinates at startup
led_coordinates = {}
if os.path.exists(COORDINATES_FILE):
    with open(COORDINATES_FILE, 'r') as f:
        loaded = json.load(f)
        led_coordinates = {int(k): v for k, v in loaded.items() if v is not None}

# Calculate bounds
if led_coordinates:
    all_x = [v['x'] for v in led_coordinates.values()]
    all_y = [v['y'] for v in led_coordinates.values()]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
else:
    min_x = max_x = min_y = max_y = center_x = center_y = 0


def stop_current_effect():
    global stop_effect, effect_thread
    stop_effect = True
    if effect_thread and effect_thread.is_alive():
        effect_thread.join()
    stop_effect = False


def turn_off_other_switches(except_switch_id):
    """Tell Homebridge to turn off all other Christmas switches"""
    switches = [
        'christmas_lights',
        'christmas_twinkle',
        'christmas_candy_cane',
        'christmas_northern_lights',
        'christmas_fire',
        'christmas_wave',
        'christmas_snowfall',
        'christmas_rotating_line',
        'christmas_red_green',
        'vegas_golden_knights'
    ]

    for switch_id in switches:
        if switch_id != except_switch_id:
            try:
                requests.get(f'http://IP/?accessoryId={switch_id}&state=false', timeout=1)
            except:
                pass


def all_off():
    pixels.fill((0, 0, 0))
    pixels.show()


def solid_white():
    pixels.fill((255, 255, 255))
    pixels.show()


def solid_red():
    pixels.fill((255, 0, 0))
    pixels.show()


def solid_green():
    pixels.fill((0, 255, 0))
    pixels.show()


# ========== COORDINATE-BASED EFFECTS ==========

def twinkle_stars():
    """Random sparkles - now prefers LEDs that are higher up (like stars in the sky)"""
    global stop_effect
    while not stop_effect:
        pixels.fill((0, 0, 0))

        # Pick 20 random LEDs, but bias towards the top (lower y values)
        for _ in range(20):
            if led_coordinates and len(led_coordinates) > 0:
                # Weight by height - LEDs at the top are more likely to twinkle
                led_list = list(led_coordinates.keys())
                weights = [(max_y - led_coordinates[i]['y']) for i in led_list]
                total_weight = sum(weights)
                if total_weight > 0:
                    weights = [w / total_weight for w in weights]

                    # Manual weighted random choice
                    r = random.random()
                    cumsum = 0
                    for idx, w in enumerate(weights):
                        cumsum += w
                        if r <= cumsum:
                            i = led_list[idx]
                            break
                else:
                    i = random.choice(led_list)
            else:
                i = random.randint(0, 149)

            brightness = random.randint(100, 255)
            pixels[i] = (brightness, brightness, brightness)

        pixels.show()
        time.sleep(0.1)


def candy_cane_chase():
    """Vertical stripes of red and white that move horizontally"""
    global stop_effect
    offset = 0
    stripe_width = (max_x - min_x) / 10 if max_x != min_x else 10  # 10 stripes across

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            x_pos = (coord['x'] - min_x + offset) % (max_x - min_x) if max_x != min_x else 0
            stripe_num = int(x_pos / stripe_width) if stripe_width > 0 else 0

            if stripe_num % 2 == 0:
                pixels[led_idx] = (255, 0, 0)  # Red
            else:
                pixels[led_idx] = (255, 255, 255)  # White

        pixels.show()
        time.sleep(0.05)
        offset += 2


def northern_lights():
    """Waves of green/blue flowing from bottom to top"""
    global stop_effect
    wave = 0

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Create wave based on y position
            y_normalized = (coord['y'] - min_y) / (max_y - min_y) if max_y != min_y else 0
            phase = (y_normalized * 150 + wave * 5) % 150

            if phase < 50:
                intensity = int((phase / 50) * 255)
                pixels[led_idx] = (0, intensity, intensity // 2)
            elif phase < 100:
                intensity = int(((100 - phase) / 50) * 255)
                pixels[led_idx] = (0, intensity, intensity // 2)
            else:
                pixels[led_idx] = (0, 0, 0)

        pixels.show()
        time.sleep(0.05)
        wave += 1


def fire_flicker():
    """Fire effect - concentrated at the bottom, flickering upward"""
    global stop_effect

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Fire is brighter at the bottom
            y_normalized = (coord['y'] - min_y) / (max_y - min_y) if max_y != min_y else 0
            intensity = 1.0 - (y_normalized * 0.7)  # Bottom is 100%, top is 30%

            r = int(random.randint(180, 255) * intensity)
            g = int(random.randint(50, 150) * intensity)
            pixels[led_idx] = (r, g, 0)

        pixels.show()
        time.sleep(0.05)


def christmas_wave():
    """Circular waves emanating from center"""
    global stop_effect
    colors = [(255, 0, 0), (0, 255, 0), (255, 215, 0)]  # Red, Green, Gold
    wave_offset = 0

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Calculate distance from center
            dx = coord['x'] - center_x
            dy = coord['y'] - center_y
            distance = math.sqrt(dx * dx + dy * dy)

            # Create circular waves
            color_index = int((distance + wave_offset) / 30) % 3
            pixels[led_idx] = colors[color_index]

        pixels.show()
        time.sleep(0.03)
        wave_offset += 2


def snowfall():
    """Snow falls from top to bottom"""
    global stop_effect

    # Create snow particles with positions
    snow_particles = []
    for _ in range(20):
        snow_particles.append({
            'x': random.uniform(min_x, max_x),
            'y': min_y  # Start at top
        })

    while not stop_effect:
        pixels.fill((0, 0, 50))  # Dark blue background

        # Move snow down
        for particle in snow_particles:
            particle['y'] += 5

            # Reset if off screen
            if particle['y'] > max_y:
                particle['y'] = min_y
                particle['x'] = random.uniform(min_x, max_x)

            # Light up nearest LED
            min_dist = float('inf')
            nearest_led = None

            for led_idx, coord in led_coordinates.items():
                dx = coord['x'] - particle['x']
                dy = coord['y'] - particle['y']
                dist = dx * dx + dy * dy

                if dist < min_dist and dist < 400:  # Within ~20 pixels
                    min_dist = dist
                    nearest_led = led_idx

            if nearest_led is not None:
                pixels[nearest_led] = (255, 255, 255)

        pixels.show()
        time.sleep(0.1)


def rotating_line():
    """All LEDs lit with rotating rainbow colors based on angle from center"""
    global stop_effect
    angle = 0

    # Manual center adjustment - tweak these values to shift the center point
    adjusted_center_x = center_x - 30  # Shift left (negative = left, positive = right)
    adjusted_center_y = center_y  # Shift up/down (negative = up, positive = down)

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Calculate angle from adjusted center to this LED
            dx = coord['x'] - adjusted_center_x
            dy = coord['y'] - adjusted_center_y
            led_angle = math.atan2(dy, dx)

            # Calculate color based on angle relative to rotating line
            # Normalize angle difference to 0-360 degrees
            angle_diff = ((led_angle - angle) * 180 / math.pi) % 360

            # Map angle to hue (0-360)
            hue = angle_diff

            # Convert HSV to RGB
            c = 255
            x = int(c * (1 - abs((hue / 60) % 2 - 1)))

            if hue < 60:
                r, g, b = c, x, 0
            elif hue < 120:
                r, g, b = x, c, 0
            elif hue < 180:
                r, g, b = 0, c, x
            elif hue < 240:
                r, g, b = 0, x, c
            elif hue < 300:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x

            pixels[led_idx] = (r, g, b)

        pixels.show()
        time.sleep(0.02)
        angle += 0.05


def rotating_red_green():
    """All LEDs lit with rotating red and green colors based on angle from center"""
    global stop_effect
    angle = 0

    # Manual center adjustment
    adjusted_center_x = center_x - 30
    adjusted_center_y = center_y + 10

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Calculate angle from adjusted center to this LED
            dx = coord['x'] - adjusted_center_x
            dy = coord['y'] - adjusted_center_y
            led_angle = math.atan2(dy, dx)

            # Calculate angle difference relative to rotating line
            angle_diff = ((led_angle - angle) * 180 / math.pi) % 360

            # Split into red and green halves
            if angle_diff < 180:
                r = 255
                g = 0
                b = 0
            else:
                r = 0
                g = 255
                b = 0

            pixels[led_idx] = (r, g, b)

        pixels.show()
        time.sleep(0.02)
        angle += 0.05


def vegas_golden_knights():
    """Vegas Golden Knights themed - rotating gold, steel grey, red, and black"""
    global stop_effect
    angle = 0

    # VGK Colors
    vgk_gold = (185, 151, 91)  # Metallic gold
    vgk_steel = (51, 63, 72)  # Steel grey
    vgk_red = (200, 16, 46)  # Red
    vgk_black = (0, 0, 0)  # Black

    colors = [vgk_gold, vgk_steel, vgk_red, vgk_black]

    # Manual center adjustment
    adjusted_center_x = center_x - 30
    adjusted_center_y = center_y

    while not stop_effect:
        for led_idx, coord in led_coordinates.items():
            # Calculate angle from adjusted center to this LED
            dx = coord['x'] - adjusted_center_x
            dy = coord['y'] - adjusted_center_y
            led_angle = math.atan2(dy, dx)

            # Calculate angle difference relative to rotating line
            angle_diff = ((led_angle - angle) * 180 / math.pi) % 360

            # Divide circle into 4 quadrants for 4 colors
            quadrant = int(angle_diff / 90)
            next_quadrant = (quadrant + 1) % 4

            # Position within quadrant (0 to 1)
            position = (angle_diff % 90) / 90

            # Blend between current and next color
            current_color = colors[quadrant]
            next_color = colors[next_quadrant]

            r = int(current_color[0] * (1 - position) + next_color[0] * position)
            g = int(current_color[1] * (1 - position) + next_color[1] * position)
            b = int(current_color[2] * (1 - position) + next_color[2] * position)

            pixels[led_idx] = (r, g, b)

        pixels.show()
        time.sleep(0.02)
        angle += 0.05


# ========== FLASK ROUTES ==========

@app.route('/webhook', methods=['POST'])
def webhook():
    global current_effect, effect_thread, stop_effect

    try:
        if request.is_json:
            data = request.json
        elif request.data:
            data = json.loads(request.data.decode('utf-8'))
        else:
            data = request.form.to_dict()

        effect = data.get('effect', 'off')

        stop_current_effect()

        switch_map = {
            'off': None,
            'white': 'christmas_lights',
            'red': 'christmas_lights',
            'green': 'christmas_lights',
            'twinkle': 'christmas_twinkle',
            'candy_cane': 'christmas_candy_cane',
            'northern_lights': 'christmas_northern_lights',
            'fire': 'christmas_fire',
            'christmas_wave': 'christmas_wave',
            'snowfall': 'christmas_snowfall',
            'rotating_line': 'christmas_rotating_line',
            'rotating_red_green': 'christmas_red_green',
            'vegas_golden_knights' : 'christmas_golden_knights'
        }

        if effect in switch_map and switch_map[effect]:
            turn_off_other_switches(switch_map[effect])

        if effect == 'off':
            all_off()
            return jsonify({'status': 'success', 'effect': 'off'})

        elif effect == 'white':
            solid_white()
            return jsonify({'status': 'success', 'effect': 'white'})

        elif effect == 'red':
            solid_red()
            return jsonify({'status': 'success', 'effect': 'red'})

        elif effect == 'green':
            solid_green()
            return jsonify({'status': 'success', 'effect': 'green'})

        elif effect == 'twinkle':
            effect_thread = threading.Thread(target=twinkle_stars, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'twinkle'})

        elif effect == 'candy_cane':
            effect_thread = threading.Thread(target=candy_cane_chase, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'candy_cane'})

        elif effect == 'northern_lights':
            effect_thread = threading.Thread(target=northern_lights, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'northern_lights'})

        elif effect == 'fire':
            effect_thread = threading.Thread(target=fire_flicker, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'fire'})

        elif effect == 'christmas_wave':
            effect_thread = threading.Thread(target=christmas_wave, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'christmas_wave'})

        elif effect == 'snowfall':
            effect_thread = threading.Thread(target=snowfall, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'snowfall'})

        elif effect == 'rotating_line':
            effect_thread = threading.Thread(target=rotating_line, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'rotating_line'})
        elif effect == 'rotating_red_green':
            effect_thread = threading.Thread(target=rotating_red_green, daemon=True)
            effect_thread.start()
            return jsonify({'status': 'success', 'effect': 'rotating_red_green'})

        else:
            return jsonify({'status': 'error', 'message': 'Unknown effect'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/map_led', methods=['POST'])
def map_led():
    """Turn on only one specific LED for mapping"""
    try:
        if request.is_json:
            data = request.json
        elif request.data:
            data = json.loads(request.data.decode('utf-8'))
        else:
            data = request.form.to_dict()

        index = int(data.get('index', 0))

        if index < 0 or index >= 150:
            return jsonify({'status': 'error', 'message': 'Index out of range (0-149)'}), 400

        pixels.fill((0, 0, 0))
        pixels[index] = (255, 255, 255)
        pixels.show()

        return jsonify({'status': 'success', 'index': index})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/save_coordinate', methods=['POST'])
def save_coordinate():
    """Save LED coordinate to mapping file"""
    try:
        if request.is_json:
            data = request.json
        elif request.data:
            data = json.loads(request.data.decode('utf-8'))
        else:
            data = request.form.to_dict()

        index = int(data.get('index'))
        x = int(data.get('x'))
        y = int(data.get('y'))

        if os.path.exists(COORDINATES_FILE):
            with open(COORDINATES_FILE, 'r') as f:
                coordinates = json.load(f)
        else:
            coordinates = {}

        coordinates[str(index)] = {'x': x, 'y': y}

        with open(COORDINATES_FILE, 'w') as f:
            json.dump(coordinates, f, indent=2)

        return jsonify({'status': 'success', 'index': index, 'x': x, 'y': y, 'total_mapped': len(coordinates)})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    """Return the complete coordinate mapping"""
    try:
        if os.path.exists(COORDINATES_FILE):
            with open(COORDINATES_FILE, 'r') as f:
                coordinates = json.load(f)
            return jsonify({'status': 'success', 'coordinates': coordinates, 'count': len(coordinates)})
        else:
            return jsonify({'status': 'success', 'coordinates': {}, 'count': 0, 'message': 'No coordinates mapped yet'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("Starting Christmas Lights Server...")
    print(f"Loaded {len(led_coordinates)} LED coordinates")
    if led_coordinates:
        print(f"Coordinate bounds: X({min_x}-{max_x}), Y({min_y}-{max_y})")
        print(f"Center point: ({center_x}, {center_y})")
    try:
        app.run(host='0.0.0.0', port=3001, debug=False)
    except Exception as e:
        print(f"Error starting Flask: {e}")
    finally:
        all_off()
