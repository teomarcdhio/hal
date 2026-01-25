# Gmail Skill

This skill allows you to send emails via Gmail SMTP and retrieve the last 10 emails from the inbox using IMAP.

## Requirements

- Python 3.12+
- `uv` package manager
- A `.env` file containing `GMAIL_PASSWORD` (App Password if 2FA is enabled).

## Environment Setup

Ensure you have a `.env` file in the root of your workspace or in this directory with:
```bash
GMAIL_PASSWORD=your_app_password
```

## Usage

You can execute the script using `uv run`.

### Send an Email

```bash
uv run scripts/manage_emails.py send \
  --sender "your_email@gmail.com" \
  --recipient "recipient@example.com" \
  --title "Hello from VS Code" \
  --body "This is a test email sent from the Gmail Skill."
```

### Get Recent 10 Emails

```bash
uv run scripts/manage_emails.py get-recent \
  --email-address "your_email@gmail.com"
```

## Capabilities

- **Send Email**: Sends an email with subject and body.
- **Get Recent Emails**: Retrieves list of subjects for the last 10 emails in the Inbox.
