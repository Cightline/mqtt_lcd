import os
import json
import requests

from pushbullet   import Pushbullet
from mqtt_publish import Publisher


class Finance():
    def __init__(self):
        with open(os.path.expanduser('~/.config/mqtt/finance.json'), 'r') as cfg:
            self.config = json.load(cfg)

        self.publisher = Publisher()


    def send_ticker_data(self):

        if self.config['bitcoin'] == True:
            import gdax

            public_client = gdax.PublicClient()

            data = public_client.get_product_24hr_stats(product_id='BTC-USD')

            if 'message' in data and 'maintenance' in data['message']:
                self.publisher.publish(msg='down for MX', title='GDAX', type_='bitcoin', alert=False)

            else:
                l = float(data['last'])
                o = float(data['open'])

                c = ((l - o)/o) * 100
                
                self.publisher.publish(msg='%s %4.2f' % (l, c), title='BTC', type_='bitcoin', alert=False)


if __name__ == '__main__':
    mqtt_f = Finance()
    mqtt_f.send_ticker_data()
