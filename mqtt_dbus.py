#from pydbus import SessionBus
from gi.repository import GLib

import dbus

from dbus.mainloop.glib import DBusGMainLoop

# http://notify2.readthedocs.io/en/latest/_modules/notify2.html
mainloop = DBusGMainLoop(set_as_default=True)



#['ActionInvoked', 'CloseNotification', 'Get', 'GetAll', 'GetCapabilities', 'GetMachineId', 'GetServerInformation', 'Introspect', 'NotificationClosed', 'Notify', 'Ping', 'PropertiesChanged', 'Set', '_Introspect', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_bus', '_bus_name', '_object', '_path', 'onActionInvoked', 'onNotificationClosed', 'onPropertiesChanged']



#notifications = bus.get('.Notifications').ActionInvoked.connect(test)
#notifications = bus.get('.Notifications').PropertiesChanged.connect(test)
#notifications = bus.get('.Notifications').GetAll('org.freedesktop.Notifications')
#notifications = bus.get('.Notifications')

#help(notifications)

#GLib.MainLoop().run()


#notifications.JobNew.connect(print)

#GLib.MainLoop().run()

def _action_callback(nid, action):
    print('action: %s' % (action))

def _closed_callback(nid, reason):
    print('action: %s' % (reason))

bus = dbus.SessionBus(mainloop=mainloop)

dbus.get_default_main_loop()

dbus_obj   = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
dbus_iface = dbus.Interface(dbus_obj, dbus_interface='org.freedesktop.Notifications')

dbus_iface.connect_to_signal('ActionInvoked', _action_callback)
dbus_iface.connect_to_signal('NotificationClosed', _closed_callback)

