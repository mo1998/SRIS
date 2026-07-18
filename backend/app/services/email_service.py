"""
Email service for sending invitations and notifications
"""

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config import settings
from datetime import datetime
from typing import Optional
from html import escape


# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_FROM,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,
)


def render_invitation_email(
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    custom_message: Optional[str] = None,
) -> tuple[str, str]:
    """Render the invitation email subject and HTML body."""
    safe_candidate_name = escape(candidate_name)
    safe_interview_title = escape(interview_title)
    safe_interview_link = escape(interview_link)
    formatted_expiry = escape(expires_at.strftime('%B %d, %Y at %I:%M %p'))
    safe_custom_message = escape(custom_message).replace('\n', '<br>') if custom_message else None
    custom_message_html = f"""
            <div style="background-color: #eef6ff; padding: 16px; border-left: 4px solid #3498db; margin: 20px 0;">
                <p style="margin: 0; color: #2c3e50;">{safe_custom_message}</p>
            </div>
    """ if safe_custom_message else ""

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50; margin-bottom: 20px;">Interview Invitation</h1>
            <p>Dear {safe_candidate_name},</p>
            <p>You have been invited to participate in a remote interview for the position related to: <strong>{safe_interview_title}</strong></p>
            {custom_message_html}
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2c3e50; margin-top: 0;">Interview Details</h3>
                <p><strong>Interview:</strong> {safe_interview_title}</p>
                <p><strong>Valid Until:</strong> {formatted_expiry}</p>
            </div>
            
            <p style="margin: 20px 0;">Click the button below to start your interview:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{safe_interview_link}"
                   style="background-color: #3498db; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                    Start Interview
                </a>
            </div>
            
            <p style="color: #7f8c8d; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #3498db; word-break: break-all; font-size: 12px;">{safe_interview_link}</p>
            
            <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                This interview is conducted by an AI system. Please ensure you have:
            </p>
            <ul style="color: #7f8c8d; font-size: 12px;">
                <li>A stable internet connection</li>
                <li>A working microphone and camera</li>
                <li>A quiet environment with good lighting</li>
                <li>Your face clearly visible</li>
            </ul>
            
            <p style="color: #7f8c8d; font-size: 12px; margin-top: 20px;">
                If you have any questions, please contact the employer directly.
            </p>
        </div>
    </body>
    </html>
    """

    return f"Interview Invitation - {interview_title}", html_content


async def send_invitation_email(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    custom_message: Optional[str] = None,
):
    """Send interview invitation email"""
    subject, html_content = render_invitation_email(
        candidate_name=candidate_name,
        interview_title=interview_title,
        interview_link=interview_link,
        expires_at=expires_at,
        custom_message=custom_message,
    )
    
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=html_content,
        subtype="html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)


async def send_completion_email(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    score: float,
    passed: bool
):
    """Send interview completion email with results"""
    
    result_text = "passed" if passed else "did not pass"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50;">Interview Completed!</h1>
            <p>Dear {candidate_name},</p>
            <p>Thank you for completing your interview for <strong>{interview_title}</strong></p>
            
            <div style="background-color: {'#d4edda' if passed else '#f8d7da'}; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: {'#155724' if passed else '#721c24'}; margin-top: 0;">Results</h3>
                <p style="font-size: 18px;"><strong>Score:</strong> {score:.1f}%</p>
                <p style="font-size: 18px;"><strong>Status:</strong> You {result_text} the interview</p>
            </div>
            
            <p>A detailed report has been shared with the employer. They will review your performance and contact you if you move forward in the process.</p>
            
            <p style="margin-top: 30px;">Best of luck!</p>
        </div>
    </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Interview Results - {interview_title}",
        recipients=[to_email],
        body=html_content,
        subtype="html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)
