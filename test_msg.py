import os
import json



import paho.mqtt.client as mqtt

client = mqtt.Client()


with open(os.path.expanduser('~/.config/mqtt_lcd/config.json'), 'r') as cfg:
    config = json.load(cfg)


def on_connect(client, userdata, flags, rc):
    print('connect with result code: %s' % (rc))

    client.subscribe('test/#')



def on_message(client, userdata, msg):
    pass


client.username_pw_set(username=config['username'], password=config['password'])
client.tls_set()
client.on_connect = on_connect
client.on_message = on_message

client.connect(config['host'], config['port'])

client.loop_start()

infot = client.publish('pi', json.dumps({'line_one':'fuck', 'line_two':'bitches'}), qos=2)

infot.wait_for_publish()

print('Done')
