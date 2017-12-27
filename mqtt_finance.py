import os
import json
import requests

from mqtt_publish import Publisher


class Finance():
    def __init__(self):
        with open(os.path.expanduser('~/.config/mqtt/finance.json'), 'r') as cfg:
            self.config = json.load(cfg)

        self.publisher = Publisher()



    def get_price(self, ticker):

        rsp = requests.get('https://finance.google.com/finance?q=%s&output=json' % (ticker))

        if rsp.status_code != 200 and not use_cache:
            print('incorrect status code for url: %s, code: [%s]' % (rsp.url, rsp.status_code))
            return False

        try:
            fin_data = json.loads(rsp.content[6:-2].decode('unicode_escape'))

        except:
            print('Unable to load ticker')
            return False

        return fin_data

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
               
                #4,4,4,4,21,14,4 down_arrow
                self.publisher.publish(msg='%d %4.2f' % (l, c), title='BTC', type_='bitcoin', alert=False)
                

        if 'tickers' not in self.config:
            return


        for ticker in self.config['tickers']:
            p = self.get_price(ticker)

            if not p:
                continue

            self.publisher.publish(msg='%4.2f (%4.2f)' % (float(p['l']), float(p['cp'])), 
                                   title=ticker.upper(), 
                                   type_='ticker_%s' % (ticker), 
                                   alert=False)



if __name__ == '__main__':
    mqtt_f = Finance()
    mqtt_f.send_ticker_data()
