# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

- **Email:** [Create a GitHub issue](https://github.com/sudo-robi/heatmind/issues) (for non-sensitive issues)
- **Do NOT** open public issues for security vulnerabilities

## Security Measures

- API keys stored in environment variables (never committed)
- MongoDB connections use auth when configured
- All user inputs validated at system boundaries
- No secrets logged or exposed in error messages
- HMAC comparison for sensitive token matching

## Dependencies

Run `pip audit` regularly to check for known vulnerabilities in dependencies.
