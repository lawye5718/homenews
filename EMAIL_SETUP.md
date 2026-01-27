# Email Configuration Guide

## Overview
The Daily News Agent now supports automatic email delivery of generated reports.

## Setup Instructions

### 1. Configure Email Environment Variables

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- **SMTP_USER**: Your email address (e.g., `your-email@gmail.com`)
- **SMTP_PASSWORD**: Your email app-specific password (NOT your login password)
- **EMAIL_TO**: Recipient email address (e.g., `recipient@example.com`)

### Optional Configuration

- **SMTP_SERVER**: SMTP server address (default: `smtp.gmail.com`)
- **SMTP_PORT**: SMTP port number (default: `587`)

### 2. Gmail-Specific Setup

If you're using Gmail, you need to create an **App Password**:

1. Go to your Google Account settings
2. Navigate to Security → 2-Step Verification
3. Scroll down to "App passwords"
4. Generate a new app password for "Mail"
5. Use this generated password as `SMTP_PASSWORD`

### 3. Other Email Providers

For other email providers:
- **Outlook/Hotmail**: `smtp.office365.com` (Port 587)
- **Yahoo**: `smtp.mail.yahoo.com` (Port 587)
- **Custom SMTP**: Set `SMTP_SERVER` and `SMTP_PORT` accordingly

## Features

- **Automatic Report Delivery**: HTML reports are automatically emailed after generation
- **Graceful Fallback**: If email configuration is missing, the system will skip email sending and continue normally
- **File Archival**: Reports are saved to the `reports/` folder with date-based filenames (e.g., `news_2026-01-27.html`)

## Troubleshooting

If email sending fails:
1. Verify your email credentials are correct
2. Check that you're using an app-specific password (not your regular password)
3. Ensure your email provider allows SMTP access
4. Check the workflow logs for specific error messages

## Security Notes

- Never commit email credentials directly in code
- Always use GitHub Secrets for sensitive information
- Use app-specific passwords instead of account passwords
- The `reports/` folder is excluded from git via `.gitignore`
