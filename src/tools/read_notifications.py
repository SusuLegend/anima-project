"""
Read Notifications Tool

This tool provides functionality to read email notifications from Gmail.
It integrates with the existing email_api module to fetch unread emails.

Requirements:
- Google Gmail API authentication set up
- email_credential.json in src/notifications/
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


class NotificationReader:
    """
    Reads notifications from various sources (primarily email).
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
    
    def check_for_notifications(self) -> Dict[str, Any]:
        """
        Check for notifications from all sources.
        
        Returns:
            Dict with notification counts and summaries
        """
        emails = self.get_unread_emails()
        
        return {
            'email_count': len(emails),
            'emails': emails,
            'summary': self.get_email_summary()
        }


def read_notifications(credentials_path: Optional[str] = None) -> str:
    """
    Simple function to read notifications and return a summary.
    
    Args:
        credentials_path: Optional path to Gmail credentials
    
    Returns:
        String summary of notifications
    """
    reader = NotificationReader(credentials_path)
    return reader.get_email_summary()


# Example usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Notification Reader - Test")
    print("=" * 60)
    
    reader = NotificationReader()
    
    print("\nAuthenticating with Gmail...")
    if reader.authenticate():
        print("✅ Authentication successful")
        
        print("\nFetching notifications...")
        notifications = reader.check_for_notifications()
        
        print(f"\n{notifications['summary']}")
    else:
        print("❌ Authentication failed")
        print("Make sure email_credential.json exists in src/notifications/")
