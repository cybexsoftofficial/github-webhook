# GitHub Webhook Deployment Service

[![CI](https://github.com/cybexsoftofficial/github-webhook/actions/workflows/ci.yml/badge.svg)](https://github.com/cybexsoftofficial/github-webhook/actions/workflows/ci.yml)

![Cybexsoft Consultancy Services](https://cybexsoft.com/img/logo.png)

Developed and maintained by [Cybexsoft Consultancy Services](https://cybexsoft.com)

A robust webhook service that automates deployments and notifications for multiple projects based on GitHub events. This service can handle multiple projects, execute deployment commands, and send notifications through various channels.

## About Cybexsoft

[Cybexsoft Consultancy Services](https://cybexsoft.com) specializes in delivering cutting-edge technology solutions and IT consulting services. With expertise in software development, cloud solutions, and DevOps practices, we help businesses streamline their operations and achieve digital transformation.

## Features

- 🚀 Multi-project support
- 🔒 Secure webhook validation with HMAC
- 📧 Multiple notification channels (Email, Slack, Mattermost)
- 🎯 Branch-specific deployments
- 🔄 Customizable deployment commands
- 🏥 Health check endpoint
- 📝 Detailed logging

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git
- Docker (optional, depending on your deployment needs)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/cybexsoftofficial/github-webhook
cd github-webhook
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create and configure the `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

### Environment Variables

Create a `.env` file with the following configurations:

```ini
# Webhook Server Configuration
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000

# Webhook Config File
WEBHOOK_CONFIG=projects.json

# SMTP Configuration
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
FROM_EMAIL=notifications@example.com

# Optional Notification Services
SLACK_TOKEN=your-slack-token
MATTERMOST_URL=your-mattermost-url
MATTERMOST_TOKEN=your-mattermost-token
```

### Adding a New Project

1. Open `projects.json`
2. Add a new project configuration using the following template:

```json
{
    "your-project-name": {
        "name": "your-project-name",
        "directory": "/path/to/your/project",
        "secret_token": "your-github-webhook-secret",
        "target_branch": "refs/heads/main",
        "commands": [
            ["command1", "arg1", "arg2"],
            ["command2", "arg1", "arg2"]
        ],
        "notifications": {
            "email": "admin@example.com",
            "slack_webhook": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
            "mattermost_webhook": "https://mattermost.example.com/hooks/your-webhook-url"
        }
    }
}
```

#### Project Configuration Fields

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Project identifier | Yes |
| `directory` | Deployment directory | Yes |
| `secret_token` | GitHub webhook secret | Yes |
| `target_branch` | Branch to trigger deployment | Yes |
| `commands` | List of commands to execute | Yes |
| `notifications` | Notification endpoints | No |

## GitHub Webhook Setup

1. Go to your GitHub repository settings
2. Navigate to Webhooks > Add webhook
3. Configure the webhook:
   - Payload URL: `http://your-server:port/webhook/your-project-name`
   - Content type: `application/json`
   - Secret: Same as `secret_token` in your project config
   - Events: Select 'Push' or customize based on your needs

## Running the Service

### Development
```bash
python server.py
```

### Production
It's recommended to run the service using a process manager like systemd or supervisor.

Example systemd service file (`/etc/systemd/system/github-webhook.service`):
```ini
[Unit]
Description=GitHub Webhook Service
After=network.target

[Service]
User=webhook
WorkingDirectory=/path/to/github-webhook
Environment=WEBHOOK_CONFIG=/path/to/projects.json
ExecStart=/usr/bin/python3 server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable github-webhook
sudo systemctl start github-webhook
```

## Monitoring

### Health Check

Monitor the service health using the `/health` endpoint:
```bash
curl http://your-server:port/health
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": "2025-09-13T10:00:00.000Z",
    "config_file": "projects.json"
}
```

## Security Considerations

1. Always use HTTPS in production
2. Keep webhook secrets secure
3. Use environment variables for sensitive data
4. Regularly update dependencies
5. Limit command execution permissions
6. Use specific branches for deployments

## Troubleshooting

### Common Issues

1. **Webhook Not Triggering**
   - Check if the webhook URL is accessible
   - Verify the secret token matches
   - Check GitHub webhook delivery logs

2. **Command Execution Fails**
   - Verify directory permissions
   - Check if required tools are installed
   - Review the service logs

3. **Notifications Not Working**
   - Verify SMTP/Slack/Mattermost credentials
   - Check network connectivity
   - Review notification service logs

### Logs

Check the service logs:
```bash
# If running with systemd
sudo journalctl -u github-webhook -f

# Direct output
python server.py > webhook.log 2>&1
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support and Contact

For professional support and consultations, please contact:

- Website: [https://cybexsoft.com](https://cybexsoft.com)
- Email: support@cybexsoft.com
- Phone: [Your company phone number]

## License

Copyright © 2025 Cybexsoft Consultancy Services

This project is licensed under the MIT License - see the LICENSE file for details.

---

<p align="center">Developed with ❤️ by <a href="https://cybexsoft.com">Cybexsoft Consultancy Services</a></p>
