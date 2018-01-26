#!/usr/bin/python3
import json
import os
import time
import datetime
import threading
import copy


import paho.mqtt.client as mqtt

from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        self.config_path = os.path.expanduser('~/.config/mqtt/lcd.json')
        self.config      = self.load_config()
        self.msg_queue   = []
        self.client      = mqtt.Client()
        self.buffer      = ['','']
        self.connected   = False
        self.scrolling   = False

        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message

        self.client.username_pw_set(username=self.config['username'], password=self.config['password'])
        self.client.tls_set()

         
        self.lcd = LcdBackpack(self.config['dev'], self.config['baud'])
        self.lcd.connect()
        self.lcd.clear()
        self.reset_backlight()
        self.lcd.set_autoscroll(False)
        self.break_loop = False
        self.display_msg('waiting to', 'connect')

        try:
            self.client.connect(host=self.config['host'], port=self.config['port'])
    
        except Exception as e:
            print('execption: %s' % (e))
            self.display_msg('error', 'cant connect')


        self.client.loop_start()
        self.display_loop()
        


    def load_config(self):
        with open(self.config_path, 'r') as cfg:
            config = json.load(cfg)

        return config


    def delay(self, seconds):
        print('delaying for %s seconds...' % (seconds))
        time.sleep(seconds)



    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print('Unable to connect: code [%s]' % (rc))
            self.display_msg('error', 'cant connect')
            self.delay(10)
            
        self.display_msg('connected', '')
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
        self.current_index = 0

        self.break_loop = True


    def reset_backlight(self):
        self.lcd.set_backlight_rgb(255, 255, 0)

    # Give the current message that is looping, and it will return True if a new message is in the queue
    # used to break out of a display_msg loop
    def check_new_msg(self, dt):
        for m in self.msg_queue:
            if m['type'] == 'immediate' and m['datetime'] > dt:
                return True


        return False

        

    def display_msg(self, title, msg, alert=False):

        title = str(title).strip()
        msg   = str(msg).strip()
    
        now = datetime.datetime.now()

        if not title:
            title = 'no title'
        
        title = title[:16]

        title = ('{{0: <{}}}'.format(16).format(title))

       
        # don't redisplay the same message
        if self.buffer[0] == title and self.buffer[1] == msg:
            return 


        #print('what', msg, title)
        #print(len(msg))
        # scroll the message if its too long
        if len(msg) > self.config['row_characters'] and self.config['scroll'] == True:
            self.lcd.clear()
            self.scrolling = True
            for x in range(len(msg)):

                if self.check_new_msg(now) == True:
                    break

                segment = msg[x:(16+x)]

                segment = ('{{0: <{}}}'.format(16).format(segment))

                # self._ser.write('{{0: <{}}}'.format(lcd_chars).format(string).encode())
                self.lcd.set_cursor_position(1,1)
                self.lcd.write(title)
                self.buffer[0] = title
                self.lcd.set_cursor_position(1,2)
                self.lcd.write(segment)
                self.buffer[1] = segment
                time.sleep(.3)

                if x < len(msg):
                    self.lcd.clear()
                
            self.scrolling = False 


        else:

            self.lcd.clear()
            self.lcd.set_cursor_position(1,1)
            self.lcd.write(str(title))
            self.buffer[0] = title
            self.lcd.set_cursor_position(1,2)
            self.buffer[1] = msg
            self.lcd.write(str(msg))


    def display_loop(self):
        # Loop and display the messages.
        # If there are no messages, it will let the user know and 
        # sleep for a few seconds. 
        self.current_index = 0

        wlq_len = len(self.msg_queue)

        while wlq_len == len(self.msg_queue):
            x = self.current_index
            if not len(self.msg_queue):
                if self.connected: self.display_msg('connected','[no messages]')

                else:
                    self.display_msg('disconnected', '')
                
                self.delay(1)
                continue
    
            # This for loop will break if it deletes an expired message. 
            # Once it breaks, the while loop sees it and restarts it. 
            # After the message is deleted, there is no time.sleep. 
            print('x', x)

            if wlq_len != len(self.msg_queue):
                break
            

            if self.scrolling == True:
                break
             
            print('current message: %s' % (self.msg_queue[x]))
            msg   = self.msg_queue[x]['msg']
            title = self.msg_queue[x]['title']
            type_ = self.msg_queue[x]['type']
            color = self.msg_queue[x]['color']
     
            
            now = datetime.datetime.utcnow()

            #if type_ == 'immediate':
            #    self.msg_queue.remove(message)
            #    self.display_msg(title, msg)
            #    time.sleep(1)
            #    break
            
               
            time_diff = ((now - self.msg_queue[x]['datetime']).seconds/60)

            if time_diff >= self.config['message_exp']:
                print('removing message: %s' % (self.msg_queue[x]))
                self.msg_queue.remove(self.msg_queue[x])
                print('message deleted, restarting loop')

                # restart at the next message in the queue
                q_len = len(self.msg_queue)

                if q_len <= 1:
                    self.current_index = 0

                else:
                    self.current_index = q_len - 1

                break

            if self.msg_queue[x]['alert'] == True:
                self.lcd.set_backlight_red()
                self.display_msg(title, msg)
                self.delay(self.config['delay'])
                self.reset_backlight()

            else:
                if self.scrolling == True:
                    continue 

                if color:
                    self.lcd.set_backlight_rgb(color[0], color[1], color[2])
            
                title = ('{{0: <{}}}'.format(16).format(title))

                self.display_msg(title,  msg)

                if len(msg) > self.config['row_characters']:
                    self.delay(2)

                else:
                    self.delay(self.config['delay'])

                self.reset_backlight()
            
            
            self.current_index += 1

            if self.current_index >= len(self.msg_queue):
                self.current_index = 0


        wql_len = len(self.msg_queue) 
        self.display_loop()

if __name__ == '__main__':
    handler = Handler()

