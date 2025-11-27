# Source - https://stackoverflow.com/a
# Posted by Vincent Schmandt, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-28, License - CC BY-SA 4.0
from winrt.runtime

from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
from winrt.windows.ui.notifications import NotificationKinds, KnownNotificationBindings

if not ApiInformation.is_type_present("Windows.UI.Notifications.Management.UserNotificationListener"):
    print("UserNotificationListener is not supported on this device.")
    exit()

listener = UserNotificationListener.get_current()
accessStatus = await listener.request_access_async()

if accessStatus != UserNotificationListenerAccessStatus.ALLOWED:
    print("Access to UserNotificationListener is not allowed.")
    exit()

def handler(listener, event):
    notification = listener.get_notification(event.user_notification_id)

    # get some app info if available
    if hasattr(notification, "app_info"):
        print("App Name: ", notification.app_info.display_info.display_name)

listener.add_notification_changed(handler)   
