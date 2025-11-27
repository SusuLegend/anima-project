import base64
from email.mime.text import MIMEText
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail(credentials_path, token_path):
    """
    Authenticate with Gmail API using user's credentials.json.
    Stores OAuth tokens in token_path.
    """
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service

def list_unread_emails(service):
    """
    List all unread emails in the user's inbox.
    Marks them as read after printing.
    """
    results = service.users().messages().list(userId='me', labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No new messages.")
    else:
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
            print(f"From: {sender}, Subject: {subject}")
            # Optionally mark as read
            service.users().messages().modify(
                userId='me', 
                id=msg['id'], 
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

def get_new_email_subject_and_body(service):
    """
    Returns a list of dicts with subject and body for each new unread email.
    Marks them as read after fetching.
    """
    results = service.users().messages().list(userId='me', labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])
    emails = []
    if not messages:
        return emails
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
        # Get the body (text/plain)
        body = ""
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = part['body'].get('data', "")
                    import base64
                    body = base64.urlsafe_b64decode(body.encode()).decode(errors='ignore')
                    break
        else:
            body = msg_data['payload']['body'].get('data', "")
            if body:
                import base64
                body = base64.urlsafe_b64decode(body.encode()).decode(errors='ignore')
        emails.append({
            'subject': subject,
            'body': body,
            'sender': sender
        })
        # Mark as read
        service.users().messages().modify(
            userId='me',
            id=msg['id'],
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    return emails

def reply_to_email(service, to_email, subject, body, thread_id=None):
    """
    Send a reply email using Gmail API.
    Args:
        service: Authenticated Gmail API service
        to_email: Recipient email address
        subject: Subject of the reply
        body: Body of the reply
        thread_id: (Optional) Gmail thread ID to reply in context
    Returns:
        Sent message response
    """
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {'raw': raw_message}
    if thread_id:
        message_body['threadId'] = thread_id
    sent_message = service.users().messages().send(userId='me', body=message_body).execute()
    return sent_message

if __name__ == "__main__":
    # Use email_credential.json in the current directory by default
    credentials_path = os.path.join(os.path.dirname(__file__), "email_credential.json")
    token_path = "token.pickle"  # This will store OAuth tokens for this user

    print(f"Using credentials file: {credentials_path}")
    service = authenticate_gmail(credentials_path, token_path)

    # Example: check for new emails every 1 second
    import time
    while True:
        new_emails = get_new_email_subject_and_body(service)
        if new_emails:
            for email in new_emails:
                print(f"From: {email['sender']}, Subject: {email['subject']}, Body: {email['body']}")
        else:
            print("No new messages.")
        time.sleep(5)
