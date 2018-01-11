import os
import json
import requests
import argparse

from mqtt_publish import Publisher


class Finance():
    def __init__(self):

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

    def send_bitcoin_data(self):

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
            self.publisher.publish(msg='%d (%4.2f)' % (l, c), title='BTC', type_='bitcoin', alert=False)
     

    def send_ticker_data(self, tickers):

        for ticker in tickers:
            p = self.get_price(ticker)

            if not p:
                continue

            self.publisher.publish(msg='%4.2f (%4.2f)' % (float(p['l']), float(p['cp'])), 
                                   title=ticker.upper(), 
                                   type_='ticker_%s' % (ticker), 
                                   alert=False)



if __name__ == '__main__':
    mqtt_f = Finance()

    parser = argparse.ArgumentParser()

    parser.add_argument('--bitcoin', action='store_true',       help='send the Bitcoin price')
    parser.add_argument('--tickers', action='store', nargs='+', help='send ticker prices')

    args = parser.parse_args()

    if args.tickers:
        mqtt_f.send_ticker_data(args.tickers)

    if args.bitcoin:
        mqtt_f.send_bitcoin_data()


