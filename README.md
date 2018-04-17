# mqtt_lcd
Code for my Raspberry Pi LCD MQTT LCD  

This program was made for the 16x2 character LCD from Adafruit (https://www.adafruit.com/product/782).

Features:
- displays the local weather and conditions
- displays weather alerts (conditions are still displayed if the the alerts don't take up the entire LCD)
- uses the Haversine formula to determine the distance of the severe storm
- searches the alert text for the word "hail" and displays "HAL" as an alert
- supports MQTT, so you can use this to display arbitrary messages. (You'll have to setup a MQTT server though)


Notes:
I'm not really sure if I didn't do a good job soldering or what, but I had to use a timeout library. The LCD would freeze/block while connecting. 

Installation:
`git clone [repo]`
`mkdir /etc/mqtt_lcd`
`cp [repo_path]/* /etc/mqtt_lcd/`
`cp mqtt_lcd.service /usr/lib/systemd/system/mqtt_lcd.service`
`pip install lcdbackpack`
`pip install timeout-decorator`
`systemctl enable mqtt_lcd`
