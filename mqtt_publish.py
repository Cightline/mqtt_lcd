import os
import json

import paho.mqtt.client as mqtt


class Publisher():
    def __init__(self):
        
        with open(os.path.expanduser('~/.config/mqtt/lcd.json'), 'r') as cfg:
            self.config = json.load(cfg)

        self.client = mqtt.Client()

        self.client.username_pw_set(username=self.config['username'], password=self.config['password'])
        self.client.tls_set()
        self.client.on_connect = self.on_connect

        self.client.connect(self.config['host'], self.config['port'])

        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print('connect with result code: %s' % (rc))

        self.client.subscribe('pi/#')


    def publish(self, msg, title, type_, alert, color=None, update=False, qos=2):
        j_data = json.dumps({'msg':msg, 'title':title, 'type':type_, 'alert':alert, 'color':color, 'update':update})
        infot = self.client.publish('pi', j_data, qos=qos)

        infot.wait_for_publish()

        print('message published: %s' % (j_data))
