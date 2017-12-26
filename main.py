#!/usr/bin/python3
import json
import os
import time
import datetime

import daemon
import paho.mqtt.client as mqtt

from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        self.config_path = os.path.expanduser('~/.config/mqtt_lcd/config.json')
        self.config      = self.load_config()
        self.msg_queue   = []
        self.client      = mqtt.Client()

        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message

        self.client.username_pw_set(username=self.config['username'], password=self.config['password'])
        self.client.tls_set()

         
        
        self.lcd = LcdBackpack('/dev/serial/by-id/usb-239a_Adafruit_Industries-if00', 115200)
        self.lcd.connect()
        self.lcd.clear()
        self.reset_backlight()
        self.lcd.set_autoscroll(False)
        self.lcd.write('waiting...')
        self.buffer = ['','']

        try:
            self.client.connect(host=self.config['host'], port=self.config['port'])
    
        except Exception as e:
            print('execption: %s' % (e))
            self.display_msg('error', 'cant connect')


        self.client.loop_start()
        self.display_loop()
        


    def load_config(self):
        with open(os.path.expanduser('~/.config/mqtt_lcd/config.json'), 'r') as cfg:
            config = json.load(cfg)

        return config


    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print('Unable to connect: code [%s]' % (rc))
            self.display_msg('error', 'cant connect')
            time.sleep(30)
            
        self.display_msg('connected', '')
        print('connected with result code: %s' % (rc))

        self.client.subscribe('pi/#')

    def on_disconnect(self, client, userdata, rc):
        print('disconnected: code [%s]' % (rc)) 
        self.display_msg('disconnected', '')


    def on_message(self, client, userdata, msg):
        print('%s %s' % (msg.topic, msg.payload))

        keys  = ['msg', 'title', 'type']
        alert = False

        try:
            m = json.loads(msg.payload)
        except Exception as e:
            print('unable to decode message')
            return 

        
        for key in keys:
            if key not in m:
                print('message missing key: %s' % (m))
                return 

        msg    = m['msg']
        type_  = m['type']
        title  = m['title']
        now    = datetime.datetime.utcnow()

        if 'alert' in m and m['alert'] == True:
            alert = True

        for x in range(len(self.msg_queue)):
            item = self.msg_queue[x]

            if item['type'] == type_:
                item['msg']      = msg
                item['datetime'] = now
                item['alert']    = alert
                item['title']    = title
                
                return 

        self.msg_queue.append({'msg':msg, 'datetime':now, 'type':type_, 'title':title, 'alert':alert})


    def reset_backlight(self):
        self.lcd.set_backlight_rgb(255, 255, 255)


    def display_msg(self, title, msg, alert=False):
    
        # don't redisplay the same message
        if self.buffer[0] == title and self.buffer[1] == msg:
            return 

        self.lcd.clear()
        self.lcd.set_cursor_position(1,1)
        self.lcd.write(title)
        self.buffer[0] = title
        self.lcd.set_cursor_position(1,2)
        self.buffer[1] = msg
        self.lcd.write(msg)


    def display_loop(self):
        #print(dir(self.lcd))
        while True:
            if not len(self.msg_queue):
                #print('No messages in queue')
                time.sleep(3)
                continue

            #print('%s message(s) in queue' % (len(self.msg_queue)))
            for x in range(len(self.msg_queue)):
                message = self.msg_queue[x]
                
                now = datetime.datetime.utcnow()


                time_diff = ((now - message['datetime']).seconds/60)

                if time_diff >= self.config['message_exp']:
                    print('removing message: %s' % (message))
                    self.msg_queue.remove(message)
                    continue

                if message['alert'] == True:
                    self.lcd.set_backlight_red()
                    self.display_msg(message['title'], message['msg'])
                    time.sleep(self.config['delay'])
                    self.reset_backlight()

                else:
                    self.display_msg(message['title'], message['msg'])
                    time.sleep(self.config['delay'])




if __name__ == '__main__':
    handler = Handler()

