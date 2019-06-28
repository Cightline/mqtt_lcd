#!/usr/bin/python
import json
import os
import time
import datetime
import threading
import copy
import logging
import requests
import traceback

from math import radians, cos, sin, asin, sqrt

import timeout_decorator

from lcdbackpack import LcdBackpack
from noaa_sdk    import noaa

# I'm not sure if its my soldering job, or the LCD itself, but I had to use this as 
# the LCD would freeze after a while. 
# https://github.com/pnpnpn/timeout-decorator

class Handler():
    def __init__(self, args):

        if args.config:
            self.config_path = os.path.expanduser(args.config)

        else:
            self.config_path = os.path.expanduser('~/.config/weather_lcd/config.json')

        self.config      = self.load_config()
        self.msg_queue   = []
        self.buffer      = [''] * 4
        self.current_alerts_short = []
        self.current_buffer = ['', '']
        self.rain_hour         = -1
        self.thunderstorm_hour = -1
        self.current_alerts    = []
        self.storm_distance    = -1
        self.connected         = False
        self.c                 = None
        self.d                 = None
        self.in_use            = False
        self.update_interval   = self.config['update_interval']
        self.normal_color      = self.config['normal_color']
        self.alert_color       = self.config['alert_color']
        self.alerts_ignore     = self.config['alerts_ignore']
        self.error_count       = 0
        self.n                 = noaa.NOAA()
        self.osm               = noaa.OSM()
        self.setup             = False

        self.temp      = 'n/a'
        self.condition = 'n/a'
        self.wind      = 'n/a'

        self.logger = logging.getLogger(__name__)

        if args.debug:
            self.logger.setLevel(logging.DEBUG)

        else:
            self.logger.setLevel(logging.INFO)


        while self.setup == False:
            try:
                self.postal_code, self.country_code = self.osm.get_postalcode_country_by_lan_lon(self.config['lat'], self.config['lon'])

                self.setup = True


            except Exception as e:
                self.logger.error('Unable to set the postal or country code (this is probably a connection issue)')
                self.logger.error('TRACEBACK:', exc_info=e.__traceback__)

    
            time.sleep(10)
            

        
        self.lcd = LcdBackpack(self.config['dev'], self.config['baud'])

        #fh = logging.FileHandler(self.config['log_path'])
        #fh.setLevel(logging.DEBUG)
       
        sh = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        #fh.setFormatter(formatter)
        sh.setFormatter(formatter)

        #self.logger.setFormatter(formatter)

        #self.logger.addHandler(fh) 
        self.logger.addHandler(sh) 


        self.logger.debug('======== NEW INSTANCE ========')

        while True:
            self.logger.debug('looping')
            
            now = datetime.datetime.utcnow()

            if self.error_count >= 3:
                exit(1)

            try: 
                if self.c == None:
                    self.c = now
                    time_diff_c = self.update_interval

                else:
                    time_diff_c = ((now - self.c).seconds)

                self.logger.debug('time_diff_c: %s' % (time_diff_c))
    
                if time_diff_c >= self.update_interval: 
                    self.get_alerts()
                    self.get_weather()
                    #self.get_hourly()
                    self.c = now
                    
                self.display_info()
               

            except Exception as e:
                self.error(e)
                self.logger.error('TRACEBACK:', exc_info=e.__traceback__)




            time.sleep(1)
    
    def error(self, msg):
        self.logger.error('EXCEPTION: %s' % (msg))
        #self.display_msg('exception')


    def get_page(self, url):
        page = requests.get(url)

        print('request URL: %s' % url)

        # Bad status_code error
        if page.status_code != 200:
            self.logger.info('unable to get page: [%s], status code: %s' % (url, page.status_code))
            self.error_count += 1

            return False

        try:
            return page.json()
        
        # Unable to decode JSON error
        except Exception as e:
            self.logger.info('unable to decode JSON:  page: [%s], status code: [%s], text: [%s]' % (url, page.status_code, page.text))
            self.error_count += 1

        return False

        

    def get_weather(self):
        
        #d = self.get_page('http://api.wunderground.com/api/%s/conditions/q/%s,%s.json' % (self.config['api_key'], 
        #                                                                                  self.config['lat'],
        #                                                                                  self.config['lon']))


        noaa_alerts = self.n.alerts(point='%s,%s' % (self.config['lat'], self.config['lon']), active=1)

        # FOR RAIN FORECAST
        #noaa_weather = self.n.points_forecast(point='%s,%s' % (self.config['lat'], self.config['lon'])


        # this literally just converts the poastal code and country code right back. 
        noaa_weather = self.n.get_observations(self.postal_code, self.country_code)

        # just get the first one I guess (noaa_weather is a generator)

        for x in noaa_weather:
            #print(x)

            # {'value': 4.400000000000034, 'unitCode': 'unit:degC', 'qualityControl': 'qc:V'}
            #print(x['temperature'])


            print(x['temperature'])
            self.temp      = int((x['temperature']['value'] * 1.8) + 32)
            self.condition = x['textDescription']

            return 



        #if not d:
        #    self.display_msg('unable to get', 'weather')
        #    return False


        
    
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

        noaa_forecast = self.n.get_forecasts(self.postal_code, self.country_code)

         

        rain_set = False
        thunderstorm_set = False

        for x in noaa_forecast:
            print(x)



                #self.logger.debug('rain detected in %s hour(s)' % (x))
                #self.rain_hour = x
                #rain_set = True

                #self.logger.debug('thunderstorm detected in %s hour(s)' % (x))
                #self.thunderstorm_hour = x
                #thunderstorm_set = True
        exit()

        if not rain_set:
            self.rain_hour = -1
    
        if not thunderstorm_set:
            self.thunderstorm_hour = -1

   
    def get_alerts(self):
        storm_set = False
        hail      = False
        alerts       = []
        short_alerts = []
        

        #d = self.get_page('http://api.wunderground.com/api/%s/alerts/q/%s,%s.json' % (self.config['api_key'], 
        #                                                                              self.config['lat'],
        #                                                                              self.config['lon']))

        noaa_alerts = self.n.alerts(point='%s,%s' % (self.config['lat'], self.config['lon']), active=1)

        
        # alert keys: dict_keys(['id', 'type', 'geometry', 'properties'])
        for x in noaa_alerts['features']:
            alert       = x['properties']['event']

            # Flood Watch -> FW
            
            #short_alert = ''.join([x[0] for x in alert.split(' ')])
            short_alert = ''.join([x[:2] for x in alert.split(' ')])

            short_alerts.append(short_alert)

            self.logger.debug('found alert: %s' % (alert))
            #self.logger.debug('alert shortened to: %s' % (short_alert))

            alerts.append(alert)


            #sb = alert['StormBased']

            """ {'time_epoch': 1523590740, 'Motion_deg': 241, 'Motion_spd': 40, 'position_lat': 32.98, 'position_lon': -95.2}
            if 'stormInfo' in sb.keys():
                storm_info = sb['stormInfo']

                #distance = self.haversine(storm_info['position_lat'], storm_info['position_lon'], self.config['lat'], self.config['lon'])
                
                #print('DISTANCE', distance)
                self.storm_distance = int(distance)
                storm_set = True"""



        if not storm_set:
            self.storm_distance = -1


        self.current_alerts_short = short_alerts
        self.current_alerts       = alerts

    def load_config(self):
        with open(self.config_path, 'r') as cfg:
            config = json.load(cfg)

        return config


    def delay(self, seconds):
        self.logger.debug('delaying for %s seconds' % (seconds))
        #print('delaying for %s seconds...' % (seconds))
        time.sleep(seconds)


    def display_info(self):

        alert        = False
        max_space    = 16

        # prioritize alerts
        # 4 alerts per line
        if self.current_alerts:
            alert = True
            
            #short_alert = ''.join([x[0] for x in alert.split(' ')])
           
            # Make it into a string with no spaces, then see if we have 
            # enough room left (13 characters of space + 1 character per alert for a slash)

                
            for alert in self.current_alerts:
                
                for word in alert.split(' '):
                    self.display_msg('%s %s' % (self.temp, word), self.condition.lower(), alert=alert)
                    time.sleep(4)

        else:
            self.display_msg(self.temp, self.condition.lower(), alert=alert)


        """# Just set it to temp, if rain or thunderstorm is coming, then we change the T/R values
        line_one = self.temp
    
        #print('RAIN_HOUR', self.rain_hour)
        #print('T HOUR', self.thunderstorm_hour)
        # rain and thunderstorm
        if self.rain_hour != -1 and self.thunderstorm_hour != -1:
            line_one = '%s R:%s T:%s' % (self.temp, self.rain_hour, self.thunderstorm_hour)

        # rain, no thunderstorm
        elif self.rain_hour != -1 and self.thunderstorm_hour == -1:
            line_one = '%s R:%s' % (self.temp, self.rain_hour)
        
        # no rain, just thunderstorm
        elif self.rain_hour == -1 and self.thunderstorm_hour != -1:
            line_one = '%s      T:%s ' % (self.temp, self.thunderstorm_hour)

        self.display_msg(line_one, self.condition)"""

        
    def display_msg(self, line_one='', line_two='', alert=False, buffer_index=[0,1]):
        r = False

        try:
            line_one = str(line_one)[:16]
            line_two = str(line_two)[:16]

            if self.current_buffer[0] != line_one or self.current_buffer[1] != line_two:
                r = self.write_buffer(line_one, line_two, alert=alert, buffer_index=buffer_index)

            else:
                self.logger.debug('message already displayed, returning')
                self.logger.debug('line_one: %s' % line_one)
                self.logger.debug('line_two: %s' % line_two)
                self.logger.debug('self.current_buffer[0]: %s' % self.current_buffer[0])
                self.logger.debug('self.current_buffer[1]: %s' % self.current_buffer[1])
                return 

            # I think the timeout_decorator is messing with stuff, my list assignments aren't being saved. 
            if r == True:
                self.current_buffer[0] = line_one
                self.current_buffer[1] = line_two 
            else:
                self.error('something happened')

        except Exception as e:
            self.error(e)

    @timeout_decorator.timeout(1, use_signals=False)
    def write_buffer(self, line_one='', line_two='', alert=False, buffer_index=[0,1]):

        # Keep this up here so it doesn't set the buffers

        self.logger.debug('doing some buffer stuff')

        #msg[0] = ('{{0: <{}}}'.format(16).format(title))

        # don't redisplay the same message
        '''if self.buffer[buffer_index[0]] == line_one and self.buffer[buffer_index[1]] == line_two:
            self.logger.debug('message alerady displayed, returning')
            return '''

        
        '''if self.buffer[buffer_index[0]] != line_one:
            self.buffer[buffer_index[0]] = line_one


        if self.buffer[buffer_index[1]] != line_two:
            self.buffer[buffer_index[1]] = line_two'''
        
        self.logger.debug('connecting to LCD')
        self.lcd.connect()


        #print("FUCK")
        #print(self.lcd._ser.is_open)

        #if not self.lcd._ser.connected():
        #    self.logger.error("NOT CONNECTED")
        #    print("NOT CONNECTED")
        #    exit(1)


        self.logger.debug('setting autoscroll to False')
        self.lcd.set_autoscroll(False)
        self.logger.debug('setting brightness to 255 ')
        self.lcd.set_brightness(255)
        self.lcd.set_contrast(150)



        if alert:
            self.logger.debug('message was an alert, setting backlight to (255,0,0)')
            self.lcd.set_backlight_rgb(self.alert_color[0], self.alert_color[1], self.alert_color[2])

        else:
            self.logger.debug('message was not an alert, setting backlight to (255,255,0)')
            self.lcd.set_backlight_rgb(self.normal_color[0], self.normal_color[1], self.normal_color[2])
   

        if self.in_use:
            self.logger.debug('LCD in use, returning')
            return False

        if self.lcd.connected:
            self.in_use = True

            self.logger.debug('2 %s' % (self.current_buffer))

            self.logger.debug('clearing LCD')
            self.lcd.clear()
            self.logger.debug('setting cursor to (1,1)')
            self.lcd.set_cursor_position(1,1)
            self.logger.debug('writting line_one: %s' % (line_one))
            self.lcd.write(line_one)
            self.logger.debug('setting cursor to (1,2)')
            self.lcd.set_cursor_position(1,2)
            self.logger.debug('writting line_two: %s' % (line_two))
            self.lcd.write(line_two)

            self.logger.debug('disconnecting from LCD')
            self.lcd.disconnect()

            self.current_buffer[0] = copy.deepcopy(line_one)
            self.current_buffer[1] = copy.deepcopy(line_two)

            self.in_use = False

            self.logger.debug('3 %s' % (self.current_buffer))
            self.logger.debug('line_one: %s' % (line_one))
            self.logger.debug('line_two: %s' % (line_two))
        else:
            self.logger.warn('LCD not connected, returning')
            return False

        return True

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--debug',  action='store_true', default=False, help='Set the logger to DEBUG')
    parser.add_argument('--config', action='store',                     help='Set the configuration path')

    args = parser.parse_args()

    handler = Handler(args=args)
    


