from flask         import Flask
from flask_restful import Resource, Api, reqparse

from mqtt_publish import Publisher

app = Flask(__name__)
api = Api(app)

publisher = Publisher()

class Receive(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('message', type=str, help='the message to display')


    def get(self):
        args = self.parser.parse_args()
        
        if 'message' in args:
            publisher.publish(title=args.get('message'), msg='', type_='dbus', alert=False)


api.add_resource(Recieve, '/')

if __name__ == '__main__':
    app.run(debug=True)
