# Weather LCD
Code for my Raspberry Pi Weather LCD  

This program was made for the 16x2 character LCD from Adafruit (https://www.adafruit.com/product/782).

Features:
- displays the local weather and conditions
- displays weather alerts (conditions are still displayed if the the alerts don't take up the entire LCD)





Installation:
```git clone https://github.com/Cightline/weather_lcd.git
cp weather_lcd.service /usr/lib/systemd/system/weather_lcd.service
pip install lcdbackpack
pip install timeout-decorator
```

You'll need to update your udev rules so the program can read the USB device. 
Run `lsusb`
```
admin@alarmpi ~/weather_lcd> lsusb
Bus 001 Device 005: ID 239a:0001  
Bus 001 Device 004: ID 0781:5571 SanDisk Corp. Cruzer Fit
Bus 001 Device 003: ID 0424:ec00 Standard Microsystems Corp. SMSC9512/9514 Fast Ethernet Adapter
Bus 001 Device 002: ID 0424:9514 Standard Microsystems Corp. SMC9514 Hub
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```

In this case my LCD was the first line, so I updated my `/etc/udev/rules.d/weather_lcd.rules` like so: 

```
ACTION=="add", ATTRS{idVendor}=="239a", ATTRS{idProduct}=="0001", , DRIVERS=="usb", GROUP="lcd", MODE="0775"
```

Reload the rules: `udevadm control --reload-rules`

You should now be able to run `echo "test" > /dev/serial/by-id/usb-239a_Adafruit_Industries-if00`

Open `weather_lcd.service` and make sure it looks correct, then copy the service file with:
`cp weather_lcd.service /etc/systemd/system/` 

Start and enable the systemd service. 
```
systemctl enable weather_lcd
systemctl start weather_lcd
```


Notes:

I'm not really sure if I didn't do a good job soldering or what, but I had to use a timeout library. The LCD would freeze/block while connecting after running for 6+ hours. 
