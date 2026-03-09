import configparser
import os

CONFIG_FILE = "config.ini"

def save_settings(s_port, r_port, baud, payload):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'sender_port': s_port,
        'receiver_port': r_port,
        'baud_rate': baud,
        'payload': payload
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def load_settings():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return config['DEFAULT']
    return None