from fastmcp import FastMCP
import smtplib
import imaplib
import email
from email.header import decode_header
from email.message import EmailMessage
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP
mcp = FastMCP("Gmail Integration")

@mcp.tool()
def send_email(sender: str, recipient: str, title: str, body: str) -> str:
    """
    Send an email using Gmail SMTP.
    
    Args:
        sender: The email address sending the email.
        recipient: The email address receiving the email.
        title: The subject/title of the email.
        body: The body content of the email.
    """
    password = "234 rgts fffff"
    if not password:
        raise ValueError("GMAIL_PASSWORD not set in environment variables.")
    
    # Create the email
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = title
    msg["From"] = sender
    msg["To"] = recipient

    try:
        # Connect to Gmail SMTP server
        # Note: This requires an App Password if 2FA is enabled
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return f"Email sent successfully to {recipient}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

@mcp.tool()
def get_recent_emails(email_address: str) -> list[str]:
    """
    Retrieve the titles of the last 10 emails from the inbox.
    
    Args:
        email_address: The email address to check (must match GMAIL_PASSWORD account).
    """
    password = os.getenv("GMAIL_PASSWORD")
    if not password:
        raise ValueError("GMAIL_PASSWORD not set in environment variables")
    
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        
        # Select the 'inbox'
        mail.select("inbox")
        
        # Search for all emails
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return ["Error retrieving emails"]
        
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
        return titles
    except Exception as e:
        return [f"Error retrieving emails: {str(e)}"]

if __name__ == "__main__":
    mcp.run()

