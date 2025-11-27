"""
Read Notifications Tool

This tool provides functionality to read notifications from multiple sources:
- Email notifications from Gmail
- System notifications (Windows Action Center / macOS Notification Center)

Requirements:
- Google Gmail API authentication set up
- email_credential.json in src/notifications/
- For Windows system notifications: pip install winsdk
- For sending notifications: pip install plyer
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.notifications.email_api import (
    authenticate_gmail, 
    get_new_email_subject_and_body
)

# Import system notifications if available
try:
    from src.tools.system_notifications import SystemNotificationReader
    SYSTEM_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    SYSTEM_NOTIFICATIONS_AVAILABLE = False


class NotificationReader:
    """
    Reads notifications from various sources (email and system).
    """
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: str = "token.pickle"):
        """
        Initialize notification reader.
        
        Args:
            credentials_path: Path to Gmail credentials JSON
            token_path: Path to store OAuth tokens
        """
        if credentials_path is None:
            # Default to the notification directory
            credentials_path = str(
                Path(__file__).parent.parent / "notifications" / "email_credential.json"
            )
        
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticated = False
        
        # Initialize system notification reader if available
        self.system_reader = None
        if SYSTEM_NOTIFICATIONS_AVAILABLE:
            self.system_reader = SystemNotificationReader()
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.service = authenticate_gmail(self.credentials_path, self.token_path)
            self._authenticated = True
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            self._authenticated = False
            return False
    
    def get_unread_emails(self) -> List[Dict[str, str]]:
        """
        Get all unread emails from Gmail.
        Marks them as read after fetching.
        
        Returns:
            List of dicts with keys: 'subject', 'body', 'sender'
        """
        if not self._authenticated:
            if not self.authenticate():
                return []
        
        try:
            emails = get_new_email_subject_and_body(self.service)
            return emails
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def get_email_summary(self) -> str:
        """
        Get a formatted summary of unread emails.
        
        Returns:
            String summary of emails
        """
        emails = self.get_unread_emails()
        
        if not emails:
            return "No new emails."
        
        summary_parts = [f"You have {len(emails)} new email(s):\n"]
        
        for i, email in enumerate(emails, 1):
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No Subject')
            body_preview = email.get('body', '')[:100].strip()
            
            if body_preview and len(email.get('body', '')) > 100:
                body_preview += "..."
            
            summary_parts.append(
                f"\n{i}. From: {sender}\n"
                f"   Subject: {subject}\n"
                f"   Preview: {body_preview}"
            )
        
        return "\n".join(summary_parts)
    
    def get_system_notifications(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get system notifications (Windows/macOS).
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            List of dicts with keys: 'title', 'body', 'app', 'timestamp'
        """
        if not SYSTEM_NOTIFICATIONS_AVAILABLE or not self.system_reader:
            return []
        
        try:
            return self.system_reader.get_notifications(limit)
        except Exception as e:
            print(f"Error fetching system notifications: {e}")
            return []
    
    def check_for_notifications(self) -> Dict[str, Any]:
        """
        Check for notifications from all sources.
        
        Returns:
            Dict with notification counts and summaries
        """
        emails = self.get_unread_emails()
        system_notifs = self.get_system_notifications(limit=5)
        
        # Build comprehensive summary
        summary_parts = []
        
        # Email summary
        if emails:
            summary_parts.append(f"📧 {len(emails)} new email(s)")
        
        # System notification summary
        if system_notifs and SYSTEM_NOTIFICATIONS_AVAILABLE:
            summary_parts.append(f"🔔 {len(system_notifs)} system notification(s)")
        
        total_summary = ", ".join(summary_parts) if summary_parts else "No new notifications"
        
        return {
            'email_count': len(emails),
            'emails': emails,
            'system_notification_count': len(system_notifs),
            'system_notifications': system_notifs,
            'total_count': len(emails) + len(system_notifs),
            'summary': total_summary,
            'detailed_summary': self._build_detailed_summary(emails, system_notifs)
        }
    
    def _build_detailed_summary(
        self, 
        emails: List[Dict[str, str]], 
        system_notifs: List[Dict[str, str]]
    ) -> str:
        """Build detailed notification summary."""
        parts = []
        
        # Email section
        if emails:
            parts.append(f"📧 EMAILS ({len(emails)}):")
            for i, email in enumerate(emails[:5], 1):  # Limit to 5
                sender = email.get('sender', 'Unknown')
                subject = email.get('subject', 'No Subject')
                parts.append(f"  {i}. From {sender}: {subject}")
        
        # System notification section
        if system_notifs and SYSTEM_NOTIFICATIONS_AVAILABLE:
            if parts:
                parts.append("")  # Blank line
            parts.append(f"🔔 SYSTEM NOTIFICATIONS ({len(system_notifs)}):")
            for i, notif in enumerate(system_notifs[:5], 1):  # Limit to 5
                app = notif.get('app', 'Unknown')
                title = notif.get('title', 'No Title')
                parts.append(f"  {i}. [{app}] {title}")
        
        if not parts:
            return "No new notifications"
        
        return "\n".join(parts)


def read_notifications(
    credentials_path: Optional[str] = None,
    include_system: bool = True
) -> str:
    """
    Simple function to read all notifications and return a summary.
    
    Args:
        credentials_path: Optional path to Gmail credentials
        include_system: Include system notifications (Windows/macOS)
    
    Returns:
        String summary of all notifications
    """
    reader = NotificationReader(credentials_path)
    notifications = reader.check_for_notifications()
    return notifications.get('detailed_summary', 'No notifications')


# Example usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Notification Reader - Test")
    print("=" * 60)
    
    reader = NotificationReader()
    
    print("\n🔍 Checking all notification sources...")
    notifications = reader.check_for_notifications()
    
    print(f"\n{notifications['summary']}")
    print("\n" + "=" * 60)
    print(notifications['detailed_summary'])
