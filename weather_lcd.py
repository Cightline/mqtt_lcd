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

from lcdbackpack import LcdBackpack

class Handler():
    def __init__(self):
        self.config_path = os.path.expanduser('~/.config/mqtt/lcd.json')
        self.config      = self.load_config()
        self.msg_queue   = []
        self.buffer      = ['','']
        self.rain_hour         = -1
        self.thunderstorm_hour = -1
        self.current_alerts    = []
        self.storm_distance    = -1

        self.temp      = 'n/a'
        self.condition = 'n/a'
        self.wind      = 'n/a'




        self.lcd = LcdBackpack(self.config['dev'], self.config['baud'])
        self.lcd.connect()
        #self.lcd.clear()
        #self.reset_backlight()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.config['log_path'])
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        fh.setFormatter(formatter)

        self.logger.addHandler(fh) 


        self.logger.debug('starting loop')

        self.display_msg('running')

        while True:
            self.logger.debug('iterating self.display_loop()')

            try: 
                #raise Exception('test')
                self.get_weather()
                self.get_alerts()
                self.get_hourly()

                self.display_info()
                

            except Exception as e:
                self.logger.debug('EXCEPTION: %s' % (e))
                self.display_msg('unknown', 'error')

            time.sleep(120)
       
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



    def display_msg(self, line_one='', line_two='', alert=False):

        self.lcd.connect()
        self.lcd.set_autoscroll(False)
        self.lcd.set_brightness(255)

        # format it a little
        line_one = str(line_one)[:16]
        line_two = str(line_two)[:16]

        #msg[0] = ('{{0: <{}}}'.format(16).format(title))

       
        # don't redisplay the same message
        if self.buffer[0] == line_one and self.buffer[1] == line_two:
            self.logger.debug('message alerady displayed, returning')
            return 

        self.buffer[0] = line_one
        self.buffer[1] = line_two
        
        if alert:
            self.lcd.set_backlight_rgb(255,0,0)

        else:
            self.lcd.set_backlight_rgb(255,255,0)

        self.lcd.clear()
        self.lcd.set_cursor_position(1,1)
        self.lcd.write(self.buffer[0])
        self.lcd.set_cursor_position(1,2)
        self.lcd.write(self.buffer[1])

        self.lcd.disconnect()



if __name__ == '__main__':
    handler = Handler()

