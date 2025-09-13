import json
import os
import sys
import subprocess
import hmac
import hashlib
import smtplib
import httpx
import datetime
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel, validator
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Load configuration from JSON file
CONFIG_FILE = os.getenv("WEBHOOK_CONFIG", "projects.json")

try:
    with open(CONFIG_FILE, 'r') as f:
        PROJECTS = json.load(f)
except FileNotFoundError:
    logger.error(f"Configuration file {CONFIG_FILE} not found")
    PROJECTS = {}

# Notification configuration (loaded from environment variables for security)
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER"),
    "smtp_port": int(os.getenv("SMTP_PORT", 587)),
    "smtp_user": os.getenv("SMTP_USER"),
    "smtp_password": os.getenv("SMTP_PASSWORD"),
    "from_email": os.getenv("FROM_EMAIL")
}

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
MATTERMOST_URL = os.getenv("MATTERMOST_URL")
MATTERMOST_TOKEN = os.getenv("MATTERMOST_TOKEN")

async def validate_signature(request: Request, secret_token: str):
    """Validate the HMAC signature from GitHub webhook."""
    body = await request.body()
    signature = request.headers.get('X-Hub-Signature-256')

    if signature is None:
        raise HTTPException(status_code=401, detail="Signature header missing")

    mac = hmac.new(secret_token.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
    if not hmac.compare_digest('sha256=' + mac.hexdigest(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

async def send_email(to_email: str, subject: str, body: str):
    """Send notification via email."""
    if not all([EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_user"], EMAIL_CONFIG["smtp_password"], EMAIL_CONFIG["from_email"]]):
        logger.warning("Email configuration incomplete, skipping email notification")
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_CONFIG["from_email"]
    msg['To'] = to_email

    try:
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["smtp_user"], EMAIL_CONFIG["smtp_password"])
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

class ProjectConfig(BaseModel):
    name: str
    directory: str
    secret_token: str
    target_branch: str
    commands: List[List[str]]
    notifications: Optional[Dict[str, str]] = {}

    @validator('commands')
    def validate_commands(cls, v):
        if not v:
            raise ValueError("At least one command must be specified")
        return v

async def send_slack(message: str, webhook_url: str):
    """Send notification to Slack with rich formatting."""
    if not SLACK_TOKEN or not webhook_url:
        logger.warning("Slack configuration incomplete, skipping Slack notification")
        return

    # Parse the message to extract project name, status, and details
    lines = message.split('\n')
    project_info = lines[0].split(' - ')
    project_name = project_info[0].replace('Webhook for ', '')
    status = project_info[1].replace('Status: ', '')
    details = '\n'.join(lines[2:])

    # Create color-coded attachments based on status
    color = '#36a64f' if status == 'Success' else '#ff0000' if status == 'Failed' else '#808080'

    payload = {
        "attachments": [{
            "color": color,
            "title": f"Webhook Notification: {project_name}",
            "fields": [
                {
                    "title": "Status",
                    "value": status,
                    "short": True
                },
                {
                    "title": "Timestamp",
                    "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "short": True
                },
                {
                    "title": "Details",
                    "value": f"```{details}```" if details else "No details available",
                    "short": False
                }
            ],
            "footer": "GitHub Webhook Service",
        }]
    }

    headers = {"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        logger.info("Slack notification sent")
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")

async def send_mattermost(message: str, webhook_url: str):
    """Send notification to Mattermost with rich formatting."""
    if not webhook_url:
        logger.warning("Mattermost webhook URL not provided, skipping Mattermost notification")
        return

    # Parse the message to extract project name, status, and details
    lines = message.split('\n')
    project_info = lines[0].split(' - ')
    project_name = project_info[0].replace('Webhook for ', '')
    status = project_info[1].replace('Status: ', '')
    details = '\n'.join(lines[2:])

    # Create a formatted message using Mattermost Markdown
    formatted_message = f"""
### :bell: Webhook Notification: {project_name}

**Status**: {':white_check_mark:' if status == 'Success' else ':x:' if status == 'Failed' else ':grey_question:'} {status}
**Time**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

#### Details:
```
{details}
```
---
*GitHub Webhook Service*
"""

    payload = {"text": formatted_message}
    headers = {"Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            response.raise_for_status()
        logger.info("Mattermost notification sent")
    except Exception as e:
        logger.error(f"Failed to send Mattermost notification: {str(e)}")

async def send_notifications(project_name: str, status: str, details: str, notifications: Dict):
    """Send notifications based on project configuration."""
    message = f"Webhook for {project_name} - Status: {status}\nDetails: {details}"

    if notifications.get("email"):
        await send_email(notifications["email"], f"Webhook Update: {project_name}", message)
    if notifications.get("slack_webhook"):
        await send_slack(message, notifications["slack_webhook"])
    if notifications.get("mattermost_webhook"):
        await send_mattermost(message, notifications["mattermost_webhook"])

async def process_webhook(request: Request, project_config: Dict):
    """Process webhook for a given project."""
    try:
        await validate_signature(request, project_config["secret_token"])
        payload = await request.json()
        logger.info(f"Received webhook for project {project_config['name']}")

        if payload.get('ref') != project_config["target_branch"]:
            await send_notifications(
                project_config["name"],
                "Ignored",
                f"Push was not to the target branch {project_config['target_branch']}.",
                project_config.get("notifications", {})
            )
            return {"message": "Push was not to the target branch, ignoring."}

        command_outputs = []
        for command in project_config["commands"]:
            logger.info(f"Executing command: {' '.join(command)}")
            result = subprocess.check_output(
                command, 
                text=True, 
                stderr=subprocess.STDOUT,
                cwd=project_config["directory"]
            )
            command_outputs.append(f"Command {' '.join(command)}: {result}")
        status = "Success"
        details = "\n".join(command_outputs)
        
    except HTTPException:
        raise
    except Exception as e:
        status = "Failed"
        details = str(e)
        logger.error(f"Error processing webhook for {project_config['name']}: {details}")
        await send_notifications(project_config["name"], status, details, project_config.get("notifications", {}))
        raise HTTPException(status_code=500, detail=details)

    await send_notifications(project_config["name"], status, details, project_config.get("notifications", {}))
    return {
        "message": f"Webhook received and processed for {project_config['name']}",
        "status": status,
        "details": details
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Verify config file is readable
        with open(CONFIG_FILE, 'r') as f:
            json.load(f)
        return {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "config_file": CONFIG_FILE
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )

@app.post("/webhook/{project_name}")
async def webhook_handler(request: Request, project_name: str):
    """Handle incoming webhook requests."""
    project_config = PROJECTS.get(project_name)
    if not project_config:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Validate project config against Pydantic model
        ProjectConfig(**project_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid project configuration: {str(e)}"
        )
        
    return await process_webhook(request, project_config)

if __name__ == "__main__":
    import uvicorn
    # Verify required environment variables
    required_vars = [
        "WEBHOOK_CONFIG", 
        "SMTP_SERVER", 
        "SMTP_USER", 
        "SMTP_PASSWORD",
        "WEBHOOK_HOST",
        "WEBHOOK_PORT"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8000"))
        
    logger.info(f"Starting webhook server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)