import network
import time
import machine
import dht
from umqtt_simple import MQTTClient
from secrets import CONFIG

# Configuration
DEMO = True
LOCATION = 'HOME'

cfg = CONFIG[LOCATION]

SSID = cfg['SSID']
PASSWORD = cfg['PASSWORD']
MQTT_BROKER = cfg['MQTT_BROKER']
MQTT_PORT = cfg['MQTT_PORT']
MQTT_PASSWORD = cfg['MQTT_PASSWORD']
SLEEP_TIME = cfg['SLEEP_TIME']

MQTT_TOPIC = 'szenzor/dht22'
MQTT_USER = 'ha'
CLIENT_ID = 'pico_client'

DISCOVERY_PREFIX = 'homeassistant'
UNIQUE_ID = "pico_dht22_001"

if DEMO:
    SLEEP_TIME = 5

# Sensor
sensor = dht.DHT22(machine.Pin(2))  # GP2

# LED
pin = machine.Pin("LED", machine.Pin.OUT)

# WiFi connection
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.active(True)
        wlan.connect(SSID, PASSWORD)
        tries = 0
        while not wlan.isconnected() and tries < 10:
            print(".", end="")
            time.sleep(1)
            tries += 1
    if wlan.isconnected():
        print("\nWiFi OK:", wlan.ifconfig())
    else:
        print("\nWiFi ERROR.")
    return wlan

# MQTT connection
def connect_mqtt():
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
        client.connect()
        print("MQTT connected")
        return client
    except Exception as e:
        print("MQTT connection error:", e)
        return None

# --- HA autodiscovery setup ---
def publish_discovery(client):
    config_topic_temp = f"{DISCOVERY_PREFIX}/sensor/{CLIENT_ID}/temperature/config"
    config_topic_hum = f"{DISCOVERY_PREFIX}/sensor/{CLIENT_ID}/humidity/config"

    payload_temp = f'''{{
        "name": "DHT22 Temperature",
        "state_topic": "{MQTT_TOPIC}",
        "unit_of_measurement": "°C",
        "value_template": "{{{{ value_json.temperature }}}}",
        "device_class": "temperature",
        "unique_id": "{UNIQUE_ID}_temp",
        "device": {{
            "identifiers": ["{UNIQUE_ID}"],
            "name": "Pico DHT22",
            "model": "Raspberry Pi Pico WH",
            "manufacturer": "Custom"
        }}
    }}'''
    
    payload_hum = f'''{{
        "name": "DHT22 Humidity",
        "state_topic": "{MQTT_TOPIC}",
        "unit_of_measurement": "%",
        "value_template": "{{{{ value_json.humidity }}}}",
        "device_class": "humidity",
        "unique_id": "{UNIQUE_ID}_humidity",
        "device": {{
            "identifiers": ["{UNIQUE_ID}"],
            "name": "Pico DHT22",
            "model": "Raspberry Pi Pico WH",
            "manufacturer": "Custom"
        }}
    }}'''

    client.publish(config_topic_hum, payload_hum.encode('utf-8'), retain=True)
    time.sleep(2)
    client.publish(config_topic_temp, payload_temp.encode('utf-8'), retain=True)
    
    
    print("HA autodiscovery configuration sent")

# --- Fő működés ---
def main():
    first_publish = True

    while True:
        wlan = connect_wifi()
        if not wlan.isconnected():
            print("No WiFi - restart after 5s")
            time.sleep(5)
            if not DEMO:
                machine.reset()
            else:
                continue

        client = connect_mqtt()
        if client is None:
            print("MQTT error - restart after 5s")
            time.sleep(5)
            if not DEMO:
                machine.reset()
            else:
                continue
            client.disconnect()
                
        if first_publish:
            publish_discovery(client)
            first_publish = False

        try:
            pin.toggle()
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
            msg = '{{"temperature": {:.1f}, "humidity": {:.1f}}}'.format(temp, hum)
            print("Measuring:", msg)
            client.publish(MQTT_TOPIC, msg)
            pin.toggle()
        except Exception as e:
            print("Sensor ERROR:", e)

        if not DEMO:
            try:
                client.disconnect()
                wlan.disconnect()
                first_publish = True
            except Exception as e:
                print("Kapcsolat bontási hiba:", e)

        if DEMO:
            client.disconnect()
            print(f"DEMO mode - waiting for {SLEEP_TIME} seconds...\n")
            time.sleep(SLEEP_TIME)
        else:
            print(f"Sleeping for {SLEEP_TIME} seconds, then restart...\n")
            time.sleep(SLEEP_TIME)
            machine.reset()

main()