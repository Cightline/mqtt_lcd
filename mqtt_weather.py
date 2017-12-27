import os
import json
import requests

from mqtt_publish import Publisher


class Weather():
    def __init__(self):
        with open(os.path.expanduser('~/.config/mqtt/weather.json'), 'r') as cfg:
            self.config = json.load(cfg)


        self.api_key   = self.config['api_key']
        self.publisher = Publisher()


    def get_page(self, url):
        page = requests.get(url)

        if page.status_code != 200:
            # log this
            print('unable to get page: %s' % (page.url))

            
        # log this
        return page.json()
    
    def send_conditions(self):
        url = 'http://api.wunderground.com/api/%s/conditions/q/%s/%s.json' % (self.config['api_key'], 
                                                                              self.config['state'], 
                                                                              self.config['city'])

        data = self.get_page(url)['current_observation']

        t, w = data['temp_f'], data['weather']

        self.publisher.publish(msg=w, title=t, type_='weather', alert=False)


if __name__ == '__main__':
    weather = Weather()
    weather.send_conditions()
