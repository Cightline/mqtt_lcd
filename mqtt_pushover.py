import requests
import argparse
import json
import os

from mqtt_publish import Publisher


class Pushover():
    def __init__(self):
        self.secret = None
        self.id_    = None
        self.name   = 'mqtt_pushover_lcd'
        self.config_path = os.path.expanduser('~/.config/mqtt/pushover.json')

        if not os.path.exists(self.config_path):
            print('config does not exist at: %s' % (self.config_path))
            exit(1)
    
        with open(self.config_path, 'r') as cfg:
            self.config = json.load(cfg)

        self.email    = self.config['email']
        self.password = self.config['password']
        self.character_limit = self.config['character_limit']

        if 'device_id' in self.config:
            self.device_id = self.config['device_id']

        self.publisher = Publisher()

    def post_page(self, url, data={}):
        p = requests.post(url, data=data)

        if p.status_code != 200:
            print('incorrect status code: %s' % (p.status_code))
            print(p.text)
            exit(1)

        try:
            return p.json()
        
        except Exception as e:
            print("couldn't parse JSON")
            print(p.text)
            print(p.url)
            exit(1)


    def get_page(self, url, data={}):
        p = requests.get(url, data=data)

        if p.status_code != 200:
            print('incorrect status code: %s' % (p.status_code))
            print(p.text)
            exit(1)

        try:
            return p.json()
        
        except Exception as e:
            print("couldn't parse JSON")
            print(p.text)
            print(p.url)
            exit(1)

        return p.json()



    def get_secret(self):

        j = self.post_page('https://api.pushover.net/1/users/login.json', data={'email':self.email, 'password':self.password})


        if j['status'] != 1:
            print('wrong status')
            print(j)
            exit(1)

        self.secret = j['secret']


    def register_device(self):
        if not self.secret:
            print('no secret')
            return False

        j = self.post_page('https://api.pushover.net/1/devices.json', data={'secret':self.secret, 'name':self.name, 'os':'O'})

        print(j)

        if j['status'] == 0:
            print('status is 0: %s' % (j['errors']))
            exit(1)



        self.device_id = j['id']

        with open(self.config_path, 'w') as cfg:
            self.config['device_id'] = self.device_id
            cfg.write(json.dumps(self.config, sort_keys=True, indent=4, seperators={',',':'}))



    def get_messages(self):

        if not self.secret:
            self.get_secret()


        if not self.device_id:
            self.register_device


        j = self.get_page('https://api.pushover.net/1/messages.json', data={'secret':self.secret, 'device_id':self.device_id})

        messages = j['messages']

        h = []

        # dict_keys(['id', 'message', 'app', 'aid', 'icon', 'date', 'priority', 'acked', 'umid', 'title'])
        for message in j['messages']:
            msg   = message['message']

            if 'title' in message:
                title = message['title']

            else:
                title = ''

            id_  = message['id']
            h.append(id_)

            to_send = '%s...' % (msg[:self.character_limit])


            self.publisher.publish(msg=to_send, title=title, type_='pushover_%s' % (id_), alert=False, color=[0, 0, 255])

        if h:
            # Delete the messages by using the "highest" id
            d = self.post_page('https://api.pushover.net/1/devices/%s/update_highest_message.json' % (self.device_id), 
                    data={'secret':self.secret,
                          'message':max(h)})

            if d['status'] != 1:
                print(d)
                print('unable to delete messages')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    #parser.add_argument('--register',     action='store_true', help='register the device to Pushover')
    parser.add_argument('--get-messages', action='store_true', help='get the messages')

    args = parser.parse_args()


    po = Pushover()

    po.get_secret()


    #if args.register:
    #    po.register_device()

    if args.get_messages:
        po.get_messages()

    
