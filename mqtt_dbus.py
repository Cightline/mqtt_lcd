import dbus

from dbus.mainloop.glib import DBusGMainLoop

from gi.repository import GLib

from mqtt_publish import Publisher

publisher = Publisher()

def notifications(bus, message):

    l = len(message.get_args_list())
    print(l)
    
    if l >= 3:
        to_publish = str(message.get_args_list()[3])

        #to_publish_l = len(to_publish)

        #if to_publish_l > 32:
        #    to_publish = to_publish[:32]

        #publisher.publish(title=to_publish[:16], msg=to_publish[16:], alert=False, type_='immediate', qos=0)
        publisher.publish(title='', msg=to_publish, alert=False, type_='immediate', qos=0)




DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()

bus.add_match_string_non_blocking("eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'")
bus.add_message_filter(notifications)
mainloop = GLib.MainLoop()
mainloop.run()
