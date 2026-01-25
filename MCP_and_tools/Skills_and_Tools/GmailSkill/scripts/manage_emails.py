import argparse
import smtplib
import imaplib
import email
from email.header import decode_header
from email.message import EmailMessage
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
# Try loading from the current directory, and also specific locations
load_dotenv() # Defaults
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

def send_email(sender: str, recipient: str, title: str, body: str) -> str:
    """
    Send an email using Gmail SMTP.
    """
    password = os.getenv("GMAIL_PASSWORD")
    if not password:
        print("Error: GMAIL_PASSWORD not set in environment variables.", file=sys.stderr)
        return "Error: GMAIL_PASSWORD not set"
    
    # Create the email
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = title
    msg["From"] = sender
    msg["To"] = recipient

    try:
        # Connect to Gmail SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return f"Email sent successfully to {recipient}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

def get_recent_emails(email_address: str) -> list[str]:
    """
    Retrieve the titles of the last 10 emails from the inbox.
    """
    password = os.getenv("GMAIL_PASSWORD")
    if not password:
        print("Error: GMAIL_PASSWORD not set in environment variables.", file=sys.stderr)
        return ["Error: GMAIL_PASSWORD not set"]
    
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        
        # Select the 'inbox'
        mail.select("inbox")
        
        # Search for all emails
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return ["Error retrieving emails: IMAP search failed"]
        
        # Get the list of email IDs
        email_ids = messages[0].split()
        
        # Get the last 10 email IDs (or fewer if less than 10 exist)
        last_10_ids = email_ids[-10:] if len(email_ids) >= 10 else email_ids
        
        titles = []
        # Fetch in reverse order (newest first)
        for e_id in reversed(last_10_ids):
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["Subject"]
                    if subject:
                        decoded_list = decode_header(subject)
                        subject_str = ""
                        for decoded_part, encoding in decoded_list:
                            if isinstance(decoded_part, bytes):
                                subject_str += decoded_part.decode(encoding if encoding else "utf-8", errors="ignore")
                            else:
                                subject_str += decoded_part
                        titles.append(subject_str)
                    else:
                        titles.append("(No Subject)")
                    
        mail.logout()
        # Print titles for the CLI output
        for title in titles:
            print(f"- {title}")
        return titles
    except Exception as e:
        err = f"Error retrieving emails: {str(e)}"
        print(err, file=sys.stderr)
        return [err]

def main():
    parser = argparse.ArgumentParser(description="Gmail Actions Skill")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Send email command
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--sender", required=True, help="Sender email address")
    send_parser.add_argument("--recipient", required=True, help="Recipient email address")
    send_parser.add_argument("--title", required=True, help="Email subject")
    send_parser.add_argument("--body", required=True, help="Email body")

    # Get recent emails command
    get_parser = subparsers.add_parser("get-recent", help="Get recent 10 emails")
    get_parser.add_argument("--email-address", required=True, help="Email address to check")

    args = parser.parse_args()

    if args.command == "send":
        result = send_email(args.sender, args.recipient, args.title, args.body)
        print(result)
    elif args.command == "get-recent":
        get_recent_emails(args.email_address)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
