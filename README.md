# mqtt_lcd
Code for my Raspberry Pi LCD MQTT LCD display 

This program was made for the 16x2 character LCD from Adafruit (https://www.adafruit.com/product/782).

Features:
- displays the local weather and conditions
- displays weather alerts (conditions are still displayed if the the alerts don't take up the entire LCD)
- uses haversine formula to determine the distance of a storm
- searches the alert text for the word "hail" and displays "HAL" as an alert. 
- supports MQTT, so you can use this to display arbitrary messages. (You'll have to setup a MQTT server though)
