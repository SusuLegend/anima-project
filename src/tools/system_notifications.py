"""


very very hard, nigh impossible 




System Notifications Tool

This tool provides cross-platform functionality for reading and sending system notifications.
Works on Windows, macOS, and Linux.

Windows: Uses Windows Notification History (Win10+)
macOS: Reads from Notification Center database
Linux: Uses D-Bus notification system

Requirements:
- Windows: pip install winsdk (for Win10+)
- macOS: Built-in (uses sqlite3)
- Linux: pip install dbus-python (optional)
- Cross-platform sending: pip install plyer
"""

import sys
import platform
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


# Detect OS
CURRENT_OS = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'


class SystemNotificationReader:
    """
    Cross-platform system notification reader.
    """
    
    def __init__(self):
        """Initialize system notification reader."""
        self.os_type = CURRENT_OS
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if system notification reading is available."""
        if self.os_type == "Windows":
            try:
                # Check if winsdk is available
                import winsdk.windows.ui.notifications as notifications
                return True
            except ImportError:
                print("Windows notification reading requires: pip install winsdk")
                return False
        
        elif self.os_type == "Darwin":  # macOS
            # Check if notification database exists
            home = Path.home()
            db_path = home / "Library" / "Application Support" / "NotificationCenter"
            return db_path.exists()
        
        elif self.os_type == "Linux":
            # Linux notification reading is complex and varies by desktop environment
            return False
        
        return False
    
    def is_available(self) -> bool:
        """Check if notification reading is available on this system."""
        return self._available
    
    def get_notifications_windows(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent notifications from Windows Action Center.
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            List of notification dicts
        """
        if self.os_type != "Windows":
            return []
        
        try:
            from winsdk.windows.ui.notifications import management
            
            # Get notification manager
            manager = management.UserNotificationListener.get_current()
            
            # Request access (may prompt user first time)
            access_status = manager.request_access_async().get()
            
            if access_status != management.UserNotificationListenerAccessStatus.ALLOWED:
                return [{
                    'title': 'Permission Denied',
                    'body': 'Access to Windows notifications was denied. Grant permission in Windows Settings.',
                    'app': 'System',
                    'timestamp': datetime.now().isoformat()
                }]
            
            # Get notifications
            notifications_list = manager.get_notifications_async(
                management.NotificationKinds.TOAST
            ).get()
            
            results = []
            for i, notif in enumerate(notifications_list):
                if i >= limit:
                    break
                
                try:
                    # Parse notification
                    app_info = notif.app_info
                    notification = notif.notification
                    
                    app_name = app_info.display_info.display_name if app_info and app_info.display_info else "Unknown"
                    
                    # Get notification content
                    visual = notification.visual if notification else None
                    
                    title = ""
                    body = ""
                    
                    if visual and visual.bindings:
                        binding = visual.bindings[0]
                        if binding.get_text_elements():
                            text_elements = list(binding.get_text_elements())
                            if len(text_elements) > 0:
                                title = text_elements[0].text
                            if len(text_elements) > 1:
                                body = text_elements[1].text
                    
                    results.append({
                        'title': title or 'No Title',
                        'body': body,
                        'app': app_name,
                        'timestamp': datetime.now().isoformat(),
                        'id': notif.id if hasattr(notif, 'id') else str(i)
                    })
                
                except Exception as e:
                    print(f"Error parsing notification: {e}")
                    continue
            
            return results
        
        except Exception as e:
            print(f"Error reading Windows notifications: {e}")
            return [{
                'title': 'Error',
                'body': f'Failed to read Windows notifications: {str(e)}',
                'app': 'System',
                'timestamp': datetime.now().isoformat()
            }]
    
    def get_notifications_macos(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent notifications from macOS Notification Center.
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            List of notification dicts
        """
        if self.os_type != "Darwin":
            return []
        
        try:
            import sqlite3
            
            # Find notification database
            home = Path.home()
            db_dir = home / "Library" / "Application Support" / "NotificationCenter"
            
            # The database file may have different names across macOS versions
            db_files = list(db_dir.glob("*.db"))
            
            if not db_files:
                return [{
                    'title': 'Database Not Found',
                    'body': 'Could not locate macOS Notification Center database',
                    'app': 'System',
                    'timestamp': datetime.now().isoformat()
                }]
            
            # Try each database file
            for db_file in db_files:
                try:
                    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
                    cursor = conn.cursor()
                    
                    # Query notifications (table structure varies by macOS version)
                    # Try common table names
                    tables = ['record', 'notifications', 'notification']
                    
                    for table in tables:
                        try:
                            query = f"""
                                SELECT * FROM {table}
                                ORDER BY rowid DESC
                                LIMIT ?
                            """
                            cursor.execute(query, (limit,))
                            rows = cursor.fetchall()
                            
                            if rows:
                                # Get column names
                                columns = [description[0] for description in cursor.description]
                                
                                results = []
                                for row in rows:
                                    row_dict = dict(zip(columns, row))
                                    
                                    # Extract relevant fields (structure varies)
                                    results.append({
                                        'title': str(row_dict.get('title', row_dict.get('Title', 'No Title'))),
                                        'body': str(row_dict.get('body', row_dict.get('Body', ''))),
                                        'app': str(row_dict.get('app', row_dict.get('bundleid', 'Unknown'))),
                                        'timestamp': str(row_dict.get('delivered_date', row_dict.get('date', datetime.now().isoformat()))),
                                        'raw': str(row_dict)[:200]  # Include some raw data for debugging
                                    })
                                
                                conn.close()
                                return results
                        
                        except sqlite3.OperationalError:
                            continue
                    
                    conn.close()
                
                except Exception as e:
                    print(f"Error reading database {db_file}: {e}")
                    continue
            
            return [{
                'title': 'Unable to Parse',
                'body': 'macOS Notification Center database found but could not parse notifications',
                'app': 'System',
                'timestamp': datetime.now().isoformat()
            }]
        
        except Exception as e:
            print(f"Error reading macOS notifications: {e}")
            return [{
                'title': 'Error',
                'body': f'Failed to read macOS notifications: {str(e)}',
                'app': 'System',
                'timestamp': datetime.now().isoformat()
            }]
    
    def get_notifications(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent system notifications (cross-platform).
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            List of notification dicts with keys: title, body, app, timestamp
        """
        if not self._available:
            return [{
                'title': 'Not Available',
                'body': f'System notification reading not available on {self.os_type}',
                'app': 'System',
                'timestamp': datetime.now().isoformat()
            }]
        
        if self.os_type == "Windows":
            return self.get_notifications_windows(limit)
        
        elif self.os_type == "Darwin":
            return self.get_notifications_macos(limit)
        
        elif self.os_type == "Linux":
            return [{
                'title': 'Not Implemented',
                'body': 'Linux notification reading not yet implemented',
                'app': 'System',
                'timestamp': datetime.now().isoformat()
            }]
        
        return []
    
    def format_notifications(self, notifications: List[Dict[str, str]]) -> str:
        """
        Format notifications into readable string.
        
        Args:
            notifications: List of notification dicts
        
        Returns:
            Formatted string
        """
        if not notifications:
            return "No system notifications found."
        
        output_parts = [f"System Notifications ({len(notifications)}):\n"]
        
        for i, notif in enumerate(notifications, 1):
            title = notif.get('title', 'No Title')
            body = notif.get('body', '')
            app = notif.get('app', 'Unknown')
            
            output_parts.append(
                f"\n{i}. [{app}] {title}"
            )
            
            if body:
                # Truncate long bodies
                body_preview = body[:150]
                if len(body) > 150:
                    body_preview += "..."
                output_parts.append(f"   {body_preview}")
        
        return "\n".join(output_parts)


class SystemNotificationSender:
    """
    Cross-platform system notification sender.
    """
    
    def __init__(self):
        """Initialize notification sender."""
        self.os_type = CURRENT_OS
        self._plyer_available = False
        
        try:
            from plyer import notification
            self._plyer_available = True
        except ImportError:
            print("For sending notifications, install: pip install plyer")
    
    def send_notification(
        self,
        title: str,
        message: str,
        app_name: str = "AI Assistant",
        timeout: int = 10
    ) -> bool:
        """
        Send a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            app_name: Application name
            timeout: Notification timeout in seconds
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._plyer_available:
            print(f"Would send notification: {title} - {message}")
            return False
        
        try:
            from plyer import notification
            
            notification.notify(
                title=title,
                message=message,
                app_name=app_name,
                timeout=timeout
            )
            
            return True
        
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False


# Convenience functions
def get_system_notifications(limit: int = 10) -> str:
    """
    Get system notifications as formatted string.
    
    Args:
        limit: Maximum number of notifications
    
    Returns:
        Formatted notification string
    """
    reader = SystemNotificationReader()
    
    if not reader.is_available():
        return f"System notification reading not available on {CURRENT_OS}.\n\nWindows: Install 'winsdk' package\nmacOS: Should work natively\nLinux: Not yet supported"
    
    notifications = reader.get_notifications(limit)
    return reader.format_notifications(notifications)


def send_system_notification(title: str, message: str) -> bool:
    """
    Send a system notification.
    
    Args:
        title: Notification title
        message: Notification message
    
    Returns:
        True if sent successfully
    """
    sender = SystemNotificationSender()
    return sender.send_notification(title, message)


# Example usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print(f"System Notifications Tool - Test ({CURRENT_OS})")
    print("=" * 60)
    
    reader = SystemNotificationReader()
    
    print(f"\nOS: {CURRENT_OS}")
    print(f"Available: {reader.is_available()}")
    
    if reader.is_available():
        print("\nFetching system notifications...")
        print(get_system_notifications(limit=5))
    else:
        print("\n" + get_system_notifications())
    
    # Test sending
    print("\n" + "=" * 60)
    print("\nTesting notification sending...")
    sender = SystemNotificationSender()
    success = sender.send_notification(
        "Test Notification",
        "This is a test notification from the AI Assistant"
    )
    
    if success:
        print("✅ Notification sent successfully")
    else:
        print("❌ Failed to send notification (plyer not installed)")
        print("Install with: pip install plyer")
