# Gmail MCP Server

This is a Model Context Protocol (MCP) server that provides Gmail integration.

## Tools

1.  `send_email(sender, recipient, title, body)`: Sends an email using Gmail SMTP.
2.  `get_recent_emails(email_address)`: Retrieves the titles of the last 10 emails from the inbox.

## Setup

1.  Create a `.env` file based on `.env.example`:
    ```bash
    cp .env.example .env
    ```
2.  Add your Gmail App Password to `.env`. You can generate one in your Google Account settings (Security > 2-Step Verification > App passwords).

## Usage

Run the server using `uv`:

```bash
uv run main.py
```

## VS Code Configuration (mcp.json)

To use this server with VS Code's MCP client, add the following configuration to your MCP settings file (typically located at `~/.config/Code/User/globalStorage/mcp-servers.json` or accessible via the command palette "MCP: Configure Servers"):

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/hal/MCP_and_tools/GMailMCP",
        "run",
        "main.py"
      ],
      "env": {
        "GMAIL_PASSWORD": "your-app-password-here"
      }
    }
  }
}
```

> **Note:** Replace `/absolute/path/to/hal/MCP_and_tools/GMailMCP` with the actual full path to this directory on your machine. You can also move the sensitive `GMAIL_PASSWORD` env var here if you prefer not to rely on the `.env` file when running via VS Code, though the server code loads `.env` by default.