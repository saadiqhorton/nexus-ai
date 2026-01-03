# Security Policy

## Session Storage Privacy

### Session Data Storage

When using Nexus AI with the `--session` flag, conversation data is stored locally on your machine.

#### Storage Format
- **Location**: `~/.nexus/sessions/`
- **Format**: Encrypted JSON files (AES-256)
- **Encryption**: **Enabled by default** (when `keyring` is available)

#### Encryption & Privacy
Session files are encrypted at rest using **AES-256 (Fernet)**. This means:
1.  **Unreadable on Disk**: If someone gains access to your session files, they will see only encrypted gibberish.
2.  **Secure Key Management**: Encryption keys are stored in your OS's native credential store (Windows Credential Locker, macOS Keychain, etc.) via `keyring`. Keys are **never** stored in plaintext config files.
3.  **Transparent Access**: The Nexus CLI automatically handles decryption for you. You can read your sessions via `nexus sessions show` or export them, but they remain secure on disk.
4.  **User-Specific**: Keys are tied to your OS user account. Other users on the same machine cannot decrypt your sessions.

#### What Gets Stored (Encrypted)
Once decrypted by the authorized user, session files contain:
- Your prompts and questions
- AI model responses
- System prompts
- API responses

### Recommendations

#### For Sensitive Data
With encryption enabled, you can safely store sessions containing sensitive project details. However, responsible data practices still apply:

1.  **Backup Encryption**: Ensure your backups (which now contain encrypted files) are also secure.
2.  **Access Control**: Maintain strong security on your OS user account, as access to your account allows decryption.
3.  **Regular Cleanup**: Periodically delete unneeded sessions:
    ```bash
    nexus sessions list
    nexus sessions delete <session-name>
    ```

### Security Features

### Security Features

Nexus AI includes robust security protections:

#### Path Traversal Prevention
- Multi-layer validation prevents directory traversal attacks
- 4 layers of validation for file access
- Interactive mode for sensitive files (e.g., `.env`, config files)

#### Prompt Injection Defense
- URL decode cycling protection
- Unicode normalization
- Input validation and sanitization

#### Input Size Limits
- 10MB maximum stdin input size (prevents memory exhaustion attacks)
- Clear error messages for size violations

## Reporting Security Issues

If you discover a security vulnerability in Nexus AI, please report it to:

- **Email**: hortonsaadiq@gmail.com
- **GitHub**: Create a private security advisory at [https://github.com/saadiqhorton/nexus-ai/security/advisories/new](https://github.com/saadiqhorton/nexus-ai/security/advisories/new)

Please **do not** create public GitHub issues for security vulnerabilities.

### What to Include

When reporting security issues, please provide:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if you have one)

We will respond to security reports within 48 hours and aim to provide a fix within 7 days for critical issues.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Security Best Practices for Users

### API Key Management
- Store API keys in environment variables, **never** in code or config files
- Use `.env` files with proper file permissions (600)
- Add `.env` to `.gitignore`
- Rotate API keys regularly

### File Access
- Use `--allow-sensitive` flag carefully and only when necessary
- Review interactive prompts when accessing sensitive files
- Avoid piping sensitive data through stdin when using `--session`

### Network Security
- When using custom provider base URLs, ensure they use HTTPS
- Be cautious with self-hosted Ollama instances on untrusted networks
- Verify SSL certificates for custom endpoints

---

**Last Updated**: January 3, 2026  
**Version**: 0.3.0
