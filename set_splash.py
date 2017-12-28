import argparse

from lcdbackpack import LcdBackpack


parser = argparse.ArgumentParser()

parser.add_argument('--string', action='store', help='the string you want displayed at LCD startup')

args = parser.parse_args()


if args.string:
    lcd = LcdBackpack('/dev/serial/by-id/usb-239a_Adafruit_Industries-if00', 115200)
    lcd.connect()

    lcd.set_splash_screen(args.string, 32)
