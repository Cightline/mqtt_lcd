#!/usr/bin/python2
import json
import os
import time
import datetime
import threading
import copy
import logging

from cStringIO import StringIO
from io import BytesIO

import pygame
import ptext
import requests
import paho.mqtt.client as mqtt

from PIL import Image


#from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        
        os.putenv('SDL_FBDEV', '/dev/fb1')
        os.putenv('SDL_VIDEODRIVER', 'fbcon')

        pygame.display.init()
        pygame.font.init()
        pygame.mouse.set_visible(False)

        self.size   = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN | pygame.DOUBLEBUF)

        self.font = pygame.font.Font(None, 30)
        self.background_color = (0, 0, 0)

        self.config_path  = os.path.expanduser('/home/admin/.config/mqtt/lcd.json')
        self.config       = self.load_config()
        self.msg_queue    = []
        self.client       = mqtt.Client()
        self.buffers      = [''] * self.config['buffers']
        self.cache_buffers  = [''] * self.config['buffers']
        self.connected    = False
        self.scrolling    = False
        self.font_name    = self.config['font_name']
        self.text_color   = self.config['text_color']
        self.font_size    = self.config['font_size']
        self.font_width   = self.config['font_width']
        self.u            = {'screen':-1}
        self.image_buffers   = {}
        self.error_delay     = self.config['error_delay']
        self.radar_interval  = self.config['radar_interval']
        self.lat             = self.config['lat']
        self.lon             = self.config['lon']
        self.wu_api_key      = self.config['wunderground_api_key']
        self.temp_path       = self.config['temp_path']

        self.displaying_msg = False

        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message
        self.current_screen       = 0
        self.screens              = 1
        self.last_rotate          = False 

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
                print('touch event')
                self.rotate_screen()
                break
                #print('event: %s' % (event))
    
            self.update_display()
        
    def rotate_screen(self):
        now       = datetime.datetime.utcnow()
        first_run = False

        if not self.last_rotate:
            self.last_rotate = now
            first_run = True
            time_diff = 0

        else:
            time_diff = ((now - self.last_rotate).seconds)

        
        if time_diff > 1 or first_run == True:

            if self.current_screen == self.screens:
                self.current_screen = 0

            else:
                self.current_screen += 1

            self.last_rotate = now

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

        

    def display_msg(self, title, msg, alert=False, line=0, now=False):
                                               #W              #H
        if now == True:
            self.screen.fill(self.background_color)
            ptext.draw('Unable to get IP info', (self.size[1] * .05, self.size[0]),
                    color=self.text_color,
                    fontsize=self.font_size,
                    fontname=self.font_name,
                    width=self.font_width)
            
            pygame.display.flip()
            return 


        
        self.buffers[0] = '%s %s' % (title, msg)
        self.update_display()

    def display_error(self, msg):
        print('error: ', msg)
        self.display_msg('Error:',msg, alert=False, line=0, now=True)


    def update_display(self):
        need_update = False


        if self.u['screen'] == -1 or self.u['screen'] != self.current_screen:
            need_update = True

        if self.current_screen == 0:
            self.display_status(need_update=need_update)
            #time.sleep(3)

        elif self.current_screen == 1:
            self.display_weather_image(need_update=need_update)
            #time.sleep(3)

        self.u['screen'] = self.current_screen
        
        print('screen: %s (update: %s)' % (self.current_screen, need_update))

    def display_image(self, path):
        #self.screen.fill(self.background_color)
       
        try:

            to_display = pygame.image.load(path).convert()
            to_display = pygame.transform.scale(to_display, (self.size[0], self.size[1]))

            self.screen.blit(to_display, (0, 0))
            pygame.display.flip()
            return True

        except:
            return False



    def display_weather_image(self, need_update=False):

        first_run = False
        now = datetime.datetime.utcnow()

        # If we havent stored an expiration time yet, then create the dictionary value 
        if 'weather' not in self.u:
            self.u['weather'] = now
            first_run = True

        time_diff = ((now - self.u['weather']).seconds)
        print('TIME DIFF: %s' % (time_diff))

        
                
        # Check the expiration
        if time_diff >= self.radar_interval or first_run == True:
            # Reset the timer now so we don't hammer the API if there is a unexplained error.
            self.u['weather'] = now

            # Get the radar image for our location
            radar_url = "http://api.wunderground.com/api/%s/radar/image.gif?centerlat=%s&centerlon=%s&radius=100&width=%s&height=%s&newmaps=1&format=png" \
                % (self.wu_api_key, self.lat, self.lon, self.size[0], self.size[1])
            
            try:
                ir = requests.get(radar_url)
                print(ir.url)

            except Exception as e:
                self.display_error('unable to download radar image')
                time.sleep(self.error_delay)
                return

            if ir.status_code != 200:
                self.display_error('unable to download radar image')
                time.sleep(self.error_delay)
                return 
            
            
            with open('%s/w.gif.part' % (self.temp_path), 'wb') as w:
                w.write(ir.content)
           
            '''if 'weather' not in self.image_buffers:
                self.image_buffers['weather'] = BytesIO()
                self.image_buffers['weather'].write(ir.content)

            else:
                self.image_buffers['weather'] = BytesIO()
                self.image_buffers['weather'].write(ir.content)'''

            os.rename('%s/w.gif.part' % (self.temp_path), '%s/w.gif' % (self.temp_path))

        
        if not self.display_image('%s/w.gif' % (self.temp_path)):
            self.display_error('unable to show radar image')
            time.sleep(3)
        

    def display_status(self, need_update=False):

        now = datetime.datetime.now()

        for msg in self.msg_queue:
            if msg['type'] == 'weather':
                self.buffers[1] = 'weather: %s' % (msg['msg'])

            elif msg['type'] == 'bitcoin':
                self.buffers[2] = 'bitcoin: %s' % (msg['msg'])


        self.screen.fill(self.background_color)

        for x in range(len(self.buffers)):
            ptext.draw(self.buffers[x], (self.size[1] * .05, self.line_pos[x]), 
                       color=self.text_color, 
                       fontsize=self.font_size, 
                       fontname=self.font_name, 
                       width=self.font_width)


        pygame.display.flip()


if __name__ == '__main__':
    handler = Handler()

