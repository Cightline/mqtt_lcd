import os
import json
import requests

from pushbullet   import Pushbullet
from mqtt_publish import Publisher


class PB():
    def __init__(self):
        with open(os.path.expanduser('~/.config/mqtt/pushbullet.json'), 'r') as cfg:
            self.config = json.load(cfg)

        #self.pb        = Pushbullet(self.config['api_key'])
        #self.publisher = Publisher()


    def relay_pushes(self):
        print('f')
        #pushes = self.pb.get_pushes()

        #print(pushes)



        #self.publisher.publish(msg=w, title=t, type_='weather', alert=False)


if __name__ == '__main__':
    mqtt_pb = PB()
    mqtt_pb.relay_pushes()
