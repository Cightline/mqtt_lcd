#!/usr/bin/python3
import json
import os
import time
import datetime
import threading
import copy
import logging
import requests



from math import radians, cos, sin, asin, sqrt

import paho.mqtt.client as mqtt
from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        self.config_path = os.path.expanduser('~/.config/mqtt/lcd.json')
        self.config      = self.load_config()
        self.msg_queue   = []
        self.buffer      = [''] * 4
        self.current_buffer = ['', '']
        self.rain_hour         = -1
        self.thunderstorm_hour = -1
        self.current_alerts    = []
        self.storm_distance    = -1
        self.connected         = False
        self.c                 = None
        self.d                 = None

        self.temp      = 'n/a'
        self.condition = 'n/a'
        self.wind      = 'n/a'

        self.client = mqtt.Client()
        
        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message

        self.client.username_pw_set(username=self.config['username'], password=self.config['password'])
        self.client.tls_set()

        self.lcd = LcdBackpack(self.config['dev'], self.config['baud'])

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.config['log_path'])
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        fh.setFormatter(formatter)

        self.logger.addHandler(fh) 


        self.logger.debug('======== NEW INSTANCE ========')

        self.display_msg('updating...')

        while True:

            if not self.connected:
                self.client.connect(host=self.config['host'], port=self.config['port'])
            
            self.client.loop_start()

            #self.logger.debug('iterating self.display_loop()')
            
            now = datetime.datetime.utcnow()
            print(self.buffer)
            try: 
                #raise Exception('test')
                #self.display_msg('test', 'fuck', alert=False, buffer_index=[2,3])
                if self.c == None:
                    self.c = now
                    time_diff_c = 120

                else:
                    time_diff_c = ((now - self.c).seconds)

                if self.d == None:
                    self.d = now
                    time_diff_d = 0

                else:
                    time_diff_d = ((now - self.d).seconds)

                #print('time diff: %s' % (time_diff))
    
                # Grab the alerts first
                
                print('time_diff_c', time_diff_c, 'time_diff_d', time_diff_d)
                if time_diff_c >= 120:
                    #self.get_alerts()
                    self.get_weather()
                    self.get_hourly()
                    
                    self.display_info()
                    self.c = now
               
                elif time_diff_d >= 5:
                    self.display_info()
                    time.sleep(.1)

            except Exception as e:
                self.logger.debug('EXCEPTION: %s' % (e))
                self.display_msg('unknown', 'error')




    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print('Unable to connect: code [%s]' % (rc))
            self.display_msg('error', 'cant connect')
            self.logger.info("can't connect, code [%s]" % (rc))

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

        keys = ['line_one', 'line_two']

        try:
            m = json.loads(msg.payload)
        except Exception as e:
            self.logger.warn('unable to decode JSON from MQTT: %s' % (e))

        for key in keys:
            if key not in m:
                print('JSON from MQTT is malformed: %s' % (m))
                return 

        line_one = m['line_one']
        line_two = m['line_two']

        if not self.current_alerts:
            self.d = datetime.datetime.utcnow()
            self.display_msg(line_one, line_two, alert=False, buffer_index=[2,3])
       
    def get_page(self, url):
        page = requests.get(url)

        print('request URL: %s' % url)
        if page.status_code != 200:
            self.logger.info('unable to get page: [%s], status code: %s' % (url, page.status_code))

        try:
            return page.json()
        
        except Exception as e:
            self.logger.info('unable to decode JSON:  page: [%s], status code: [%s], text: [%s]' % (url, page.status_code, page.text))

        return False

        

    def get_weather(self):
        
        d = self.get_page('http://api.wunderground.com/api/%s/conditions/q/%s,%s.json' % (self.config['api_key'], 
                                                                                          self.config['lat'],
                                                                                          self.config['lon']))
        d = d['current_observation']

        if not d:
            self.display_msg('unable to get', 'weather')
            return False

        #print(d)

        self.temp      = d['temp_f']
        self.condition = d['weather']
        self.wind      = d['wind_mph']

    
    # https://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
    def haversine(self, lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        # Radius of earth in kilometers is 6371
        # Radius of earth in miles is 3959
        km = 3959* c
        return km        

    def get_hourly(self):

        d = self.get_page('http://api.wunderground.com/api/%s/hourly/q/%s,%s.json' % (self.config['api_key'], 
                                                                                      self.config['lat'],
                                                                                      self.config['lon']))

        d = d['hourly_forecast']
        if not d:
            self.display_msg('unable to get', 'hourly')

        #print(d)


        # 10 Chance of Showers
        # 11 Showers 
        # 12 Chance of Rain
        # 13 Rain
        # 14 Chance of Thunderstorm
        # 15 Thunderstorm 
    
        rain_conditions         = [10, 11, 12, 13, 14, 15]
        thunderstorm_conditions = [14, 15]



        rain_set = False
        thunderstorm_set = False

        for x in range(24):
            fctcode = int(d[x]['fctcode'])

            if fctcode in rain_conditions and rain_set == False:
                self.logger.debug('rain detected in %s hour(s)' % (x))
                self.rain_hour = x
                rain_set = True

            if fctcode in thunderstorm_conditions and thunderstorm_set == False:
                self.logger.debug('thunderstorm detected in %s hour(s)' % (x))
                self.thunderstorm_hour = x
                thunderstorm_set = True

        if not rain_set:
            self.rain_hour = -1
    
        if not thunderstorm_set:
            self.thunderstorm_set = -1

   
    def get_alerts(self):
        self.current_alerts = []
        storm_set = False

        d = self.get_page('http://api.wunderground.com/api/%s/alerts/q/%s,%s.json' % (self.config['api_key'], 
                                                                                      self.config['lat'],
                                                                                      self.config['lon']))

        d = d['alerts']
        
        for x in range(len(d)):
            alert = copy.deepcopy(d[x])
            
            print(alert['type'])
            self.current_alerts.append(alert['type'])

            for word in alert['message'].split(' '):
                if 'hail' in word.lower() and 'HAL' not in self.current_alerts:
                    self.current_alerts.append('HAL')
       
            sb = alert['StormBased']

            # {'time_epoch': 1523590740, 'Motion_deg': 241, 'Motion_spd': 40, 'position_lat': 32.98, 'position_lon': -95.2}
            if 'stormInfo' in sb.keys():
                storm_info = sb['stormInfo']

                distance = self.haversine(storm_info['position_lat'], storm_info['position_lon'], self.config['lat'], self.config['lon'])
                
                print('DISTANCE', distance)
                self.storm_distance = int(distance)
                storm_set = True



        if not storm_set:
            self.storm_distance = -1


        print(self.current_alerts)



    def load_config(self):
        with open(self.config_path, 'r') as cfg:
            config = json.load(cfg)

        return config


    def delay(self, seconds):
        self.logger.debug('delaying for %s seconds' % (seconds))
        print('delaying for %s seconds...' % (seconds))
        time.sleep(seconds)


    def display_info(self):


        # prioritize alerts
        # 4 alerts per line
        if self.current_alerts:

            if len(self.current_alerts) > 4:
                line_one = '/'.join(self.current_alerts[:4])
                line_two = '/'.join(self.current_alerts[4:])

                self.display_msg(line_one, line_two, alert=True)
                return 

            else:
                line_one = '/'.join(self.current_alerts)

                if self.storm_distance != -1:
                    self.display_msg(line_one, '%s miles out' % (self.storm_distance), alert=True)
    
                else:
                    self.display_msg(line_one, self.condition, alert=True)

                
                return



        # Just set it to temp, if rain or thunderstorm is coming, then we change the T/R values
        line_one = self.temp
    
        print('RAIN_HOUR', self.rain_hour)
        print('T HOUR', self.thunderstorm_hour)
        # rain and thunderstorm
        if self.rain_hour != -1 and self.thunderstorm_hour != -1:
            line_one = '%s R: %s T:%s' % (self.temp, self.rain_hour, self.thunderstorm_hour)

        # rain, no thunderstorm
        elif self.rain_hour != -1 and self.thunderstorm_hour == -1:
            line_one = '%s R: %s' % (self.temp, self.rain_hour)
        
        # no rain, just thunderstorm
        elif self.rain_hour == -1 and self.thunderstorm_hour != -1:
            line_one = '%s      T: %s ' % (self.temp, self.thunderstorm_hour)

        self.display_msg(line_one, self.condition)



    def display_msg(self, line_one='', line_two='', alert=False, buffer_index=[0,1]):

        self.logger.debug('doing some buffer stuff')
        # format it a little
        line_one = str(line_one)[:16]
        line_two = str(line_two)[:16]

        #msg[0] = ('{{0: <{}}}'.format(16).format(title))

       
        # don't redisplay the same message
        '''if self.buffer[buffer_index[0]] == line_one and self.buffer[buffer_index[1]] == line_two:
            self.logger.debug('message alerady displayed, returning')
            return '''


        if self.current_buffer[0] == line_one and self.current_buffer[1] == line_two:
            self.logger.debug('message already displayed, returning')
            return 

        if self.buffer[buffer_index[0]] != line_one:
            self.buffer[buffer_index[0]] = line_one


        if self.buffer[buffer_index[1]] != line_two:
            self.buffer[buffer_index[1]] = line_two
       
        self.logger.debug('connecting to LCD')
        self.lcd.connect()
        self.logger.debug('setting autoscroll to False')
        self.lcd.set_autoscroll(False)
        self.logger.debug('setting brightness to 255 ')
        self.lcd.set_brightness(255)

        if alert:
            self.logger.debug('message was an alert, setting backlight to (255,0,0)')
            self.lcd.set_backlight_rgb(255,0,0)

        else:
            self.logger.debug('message was not an alert, setting backlight to (255,255,0)')
            self.lcd.set_backlight_rgb(255,255,0)
    
        self.logger.debug('clearing LCD')
        self.lcd.clear()
        self.logger.debug('setting cursor to (1,1)')
        self.lcd.set_cursor_position(1,1)
        self.logger.debug('writting self.buffer[%s]' % (buffer_index[0]))
        self.lcd.write(self.buffer[buffer_index[0]])
        self.logger.debug('setting cursor to (1,2)')
        self.lcd.set_cursor_position(1,2)
        self.logger.debug('writting self.buffer[%s]' % (buffer_index[1]))
        self.lcd.write(self.buffer[buffer_index[1]])

        self.logger.debug('disconnecting from LCD')
        self.lcd.disconnect()

if __name__ == '__main__':
    handler = Handler()


