#!/usr/bin/python2
import json
import os
import time
import datetime
import threading
import copy
import logging
import pygame
import ptext


import paho.mqtt.client as mqtt

#from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        
        os.putenv('SDL_FBDEV', '/dev/fb1')
        os.putenv('SDL_VIDEODRIVER', 'fbcon')

        pygame.display.init()
        pygame.font.init()
        pygame.mouse.set_visible(False)

        self.size   = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN)

        self.font = pygame.font.Font(None, 30)
        self.background_color = (0, 0, 0)

        self.config_path = os.path.expanduser('/home/admin/.config/mqtt/lcd.json')
        self.config      = self.load_config()
        self.msg_queue   = []
        self.client      = mqtt.Client()
        self.buffers     = [''] * 10
        self.connected   = False
        self.scrolling   = False
        self.displaying_msg = False

        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message
        self.current_screen       = 0
        self.screens              = 1

        self.client.username_pw_set(username=self.config['username'], password=self.config['password'])
        self.client.tls_set()

        # Set up the lines for the buffer
        self.line_pos = []
        l = (pygame.display.Info().current_h/len(self.buffers)) 

        c = 0
        for b in range(len(self.buffers)):
            # + 3 is just a visual adjustment so it isn't right at the top 
            self.line_pos.append((l * c) + 3)
            c += 1

        print(self.line_pos)

        self.display_msg('waiting to', 'connect')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.config['log_path'])
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        fh.setFormatter(formatter)

        self.logger.addHandler(fh) 

        try:
            self.client.connect(host=self.config['host'], port=self.config['port'])
    
        except Exception as e:
            self.logger.error('exception: %s' % (e))
            self.display_msg('error', 'cant connect')


        self.client.loop_start()

        self.logger.debug('starting loop')

        while True:
            for event in pygame.event.get():
                print('switching display')
                self.rotate_screen()
                break
                #print('event: %s' % (event))

            self.update_display()
            time.sleep(2)
        
    def rotate_screen(self):

        if self.current_screen == self.screens:
            self.current_screen = 0

        else:
            self.current_screen += 1


    def load_config(self):
        with open(self.config_path, 'r') as cfg:
            config = json.load(cfg)

        return config


    def delay(self, seconds):
        self.logger.debug('delaying for %s seconds' % (seconds))
        print('delaying for %s seconds...' % (seconds))
        time.sleep(seconds)



    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print('Unable to connect: code [%s]' % (rc))
            self.display_msg('error', 'cant connect')
            self.logger.info("can't connect, code [%s]" % (rc))
            self.delay(10)
            
        self.display_msg('connected', '')
        self.logger.info('connected')
        print('connected with result code: %s' % (rc))

        self.client.subscribe('pi/#')
        self.connected = True

    def on_disconnect(self, client, userdata, rc):
        print('disconnected: code [%s]' % (rc)) 
        self.display_msg('disconnected', '')
        self.connected = False



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

         
        
        # See if the same type already exists
        # Also, give the option to 'update' or not

        if 'update' in m and m['update'] == True:
            for x in range(len(self.msg_queue)):
                item = self.msg_queue[x]

                if item['type'] == type_:
                    item['msg']      = msg
                    item['datetime'] = now
                    item['alert']    = alert
                    item['title']    = title
                    
                    return 

        if 'color' in m and m['color']:
            color = m['color']

        else:
            color = None
        
        self.msg_queue.append({'msg':msg, 'datetime':now, 'type':type_, 'title':title, 'alert':alert, 'color':color})
        self.logger.debug("self.msg_queue.append({'msg':%s, 'datetime':%s, 'type':%s, 'title':%s, 'alert':%s, 'color':%s})" % (msg, now, type_, title, alert, color))
        self.current_index = 0

        self.break_loop = True



    # Give the current message that is looping, and it will return True if a new message is in the queue
    # used to break out of a display_msg loop
    def check_new_msg(self, dt):
        for m in self.msg_queue:
            if m['type'] == 'immediate' and m['datetime'] > dt:
                return True


        return False

        

    def display_msg(self, title, msg, alert=False, line=0):
        
        self.buffers[0] = '%s %s' % (title, msg)
        self.update_display()

    def update_display(self):
        if self.current_screen == 0:
            self.display_status()

        elif self.current_screen == 1:
            self.display_weather_image()


    def display_weather_image(self):
                                               #W              #H
        weather_img = pygame.image.load('/home/admin/mqtt_lcd/w.png')
        weather_img = pygame.transform.scale(weather_img, (self.size[0], self.size[1]))
        self.screen.blit(weather_img, (0, 0))

        pygame.display.update()

    def display_status(self):

        #self.size   = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        
        now = datetime.datetime.now()

        for msg in self.msg_queue:
            if msg['type'] == 'weather':
                self.buffers[1] = 'weather: %s' % (msg['msg'])

            elif msg['type'] == 'bitcoin':
                self.buffers[2] = 'bitcoin: %s' % (msg['msg'])


        self.screen.fill(self.background_color)

        for x in range(len(self.buffers)):
            ptext.draw(self.buffers[x], (self.size[1] * .05, self.line_pos[x]), 
                       color='white', 
                       fontsize=30, 
                       fontname='terminus.ttf', 
                       width=400)

        #btc_chart = pygame.image.load('/home/admin/mqtt_lcd/bitcoin_chart.png')

                                                       #W              #H
        #btc_chart = pygame.transform.scale(btc_chart, (int(self.size[0] * .66), int(self.size[1] * .66)))
        #btc_chart = pygame.transform.scale(btc_chart, (self.size[0], self.size[1]))
        #weather = pygame.transform.scale(weather, (self.size[0], self.size[1]))
        #self.screen.blit(weather, (0, 0))

        pygame.display.update()


if __name__ == '__main__':
    handler = Handler()

