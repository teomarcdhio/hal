# Secret Scanning Documentation

## Overview

This repository uses [Gitleaks](https://github.com/gitleaks/gitleaks) to automatically detect hardcoded secrets, credentials, and other sensitive information in the codebase. The secret scanning workflow runs on every push and pull request to prevent accidental exposure of sensitive data.

## Detected Secret Types

Gitleaks scans for a wide variety of secret types across all file formats, including:

### Cloud Provider Credentials
- AWS Access Keys, Secret Keys, and Session Tokens
- Azure Storage Keys, Client Secrets, and Tenant IDs
- Google Cloud API Keys and Service Account Credentials
- DigitalOcean Personal Access Tokens

### Version Control & CI/CD
- GitHub Personal Access Tokens, OAuth Tokens, and App Tokens
- GitLab Personal Access Tokens and Pipeline Triggers
- Bitbucket App Passwords and Access Tokens

### Communication & Collaboration
- Slack Webhooks and API Tokens
- Discord Webhooks and Bot Tokens
- Microsoft Teams Webhooks

### Databases & Services
- Database Connection Strings (PostgreSQL, MySQL, MongoDB)
- Redis Passwords
- JDBC Connection URLs with embedded credentials

### API Keys & Tokens
- Generic API Keys and Secret Keys
- JWT Tokens with high entropy
- OAuth Client IDs and Secrets

### Cryptographic Material
- RSA Private Keys
- SSH Private Keys
- PGP Private Keys
- SSL/TLS Certificates and Private Keys

### Application-Specific
- Stripe API Keys
- SendGrid API Keys
- Twilio Auth Tokens
- Mailgun API Keys
- Passwords and secrets in configuration files (YAML, JSON, .env, etc.)

## Trigger Conditions

The secret scanning workflow is triggered automatically on:

1. **Push Events**: Any push to any branch
2. **Pull Request Events**: Any pull request targeting any branch

The workflow runs with read-only permissions (`contents: read`) following the least-privilege principle.

## Workflow Behavior

When secrets are detected:
- ✗ The workflow **fails** the build
- ✗ The commit or pull request is **blocked**
- ℹ️ Details about detected secrets are shown in the workflow logs

When no secrets are detected:
- ✓ The workflow **passes**
- ✓ The commit or pull request can proceed

## Remediation Steps

If the workflow detects a secret, follow these steps:

### 1. Verify the Detection

Review the workflow logs to understand what was detected:
```bash
# In GitHub Actions, navigate to:
# Actions → Secret Scanning → [Failed Run] → Gitleaks Secret Scan
```

### 2. Determine if It's a Real Secret

**If it's a real secret:**
1. **Immediately rotate the credential** on the provider's platform
2. Remove the secret from your code
3. Never commit secrets again - use environment variables or secret management tools

**If it's a false positive:**
1. Proceed to add it to the allowlist (see below)

### 3. Remove the Secret from Code

For real secrets, replace them with environment variables or secret management:

**Before:**
```python
API_KEY = "sk_live_1234567890abcdef"
```

**After:**
```python
import os
API_KEY = os.environ.get("API_KEY")
```

**In GitHub Actions:**
```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}
```

### 4. Remove from Git History

If the secret was already committed:

```bash
# For the most recent commit
git reset --soft HEAD~1
# Make corrections
git add .
git commit -m "Remove exposed secret"

# For older commits, consider using git-filter-repo or BFG Repo-Cleaner
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

⚠️ **Important:** After removing a secret from git history, **you must rotate it** because it may still be accessible in previous commits.

### 5. Managing False Positives

If Gitleaks incorrectly flags something as a secret, add it to the allowlist in `.gitleaks.toml`:

**By Path:**
```toml
[allowlist]
paths = [
  '''tests/fixtures/mock_credentials.py''',
  '''examples/sample_config.yaml'''
]
```

**By Regex Pattern:**
```toml
[allowlist]
regexes = [
  '''example-key-12345''',
  '''test-token-abc'''
]
```

**By Commit:**
```toml
[allowlist]
commits = [
  '''a1b2c3d4e5f6'''
]
```

**By Stopword:**
```toml
[allowlist]
stopwords = [
  '''placeholder''',
  '''example'''
]
```

After updating `.gitleaks.toml`, commit the changes and re-run the workflow.

## Local Testing

Test for secrets locally before pushing to avoid CI failures:

### Install Gitleaks

**macOS:**
```bash
brew install gitleaks
```

**Linux:**
```bash
# Download latest release (replace vX.Y.Z with current version from releases page)
# Visit https://github.com/gitleaks/gitleaks/releases for the latest version
wget https://github.com/gitleaks/gitleaks/releases/download/vX.Y.Z/gitleaks_X.Y.Z_linux_x64.tar.gz
tar -xzf gitleaks_X.Y.Z_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

**Windows:**
```powershell
# Using Chocolatey
choco install gitleaks

# Or download from GitHub releases
```

### Run Gitleaks Locally

**Scan uncommitted changes:**
```bash
gitleaks detect --source . --verbose
```

**Scan entire repository:**
```bash
gitleaks detect --source . --log-opts="--all" --verbose
```

**Scan with configuration file:**
```bash
gitleaks detect --source . --config .gitleaks.toml --verbose
```

**Scan a specific commit range:**
```bash
gitleaks detect --source . --log-opts="main..feature-branch" --verbose
```

### Pre-commit Hook (Optional)

Automatically scan for secrets before each commit:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
gitleaks protect --verbose --redact --staged
EOF

# Make it executable
chmod +x .git/hooks/pre-commit
```

## Best Practices

1. **Never commit secrets** - Use environment variables, secret managers (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
2. **Use `.env` files locally** - Add `.env` to `.gitignore` (already configured in this repo)
3. **Rotate exposed secrets immediately** - Assume any committed secret is compromised
4. **Review allowlist regularly** - Ensure false positives haven't become real secrets
5. **Educate team members** - Share this documentation with all contributors
6. **Use GitHub Secrets** - For CI/CD workflows, store secrets in GitHub repository settings

## Configuration Files

- **`.github/workflows/secret-scanning.yml`** - GitHub Actions workflow definition
- **`.gitleaks.toml`** - Gitleaks configuration with allowlist rules

## Resources

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Removing Sensitive Data from Git](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## Support

For issues or questions about secret scanning:
1. Check the [workflow logs](../../actions/workflows/secret-scanning.yml) for detailed error messages
2. Review this documentation for remediation steps
3. Open an issue in this repository if you need assistance
