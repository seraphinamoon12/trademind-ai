"""Alert system for critical events."""
from datetime import datetime
from typing import List
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Send alerts for critical events.
    
    Supports:
    - Email alerts for critical/warning events
    - In-app notifications
    """
    
    def __init__(self):
        self.alert_history: List[dict] = []
        self.max_history = 100
        
        # Email config (from settings or env)
        self.email_enabled = False
        self.smtp_host = getattr(settings, 'smtp_host', None)
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.alert_email = getattr(settings, 'alert_email', None)
        
        if self.smtp_host and self.smtp_user and self.alert_email:
            self.email_enabled = True
    
    def send_alert(
        self, 
        level: str, 
        subject: str, 
        message: str,
        details: dict = None
    ):
        """
        Send alert via all configured channels.
        
        Args:
            level: 'CRITICAL', 'WARNING', 'INFO'
            subject: Alert subject
            message: Alert message
            details: Additional details dict
        """
        # Always log
        if level == "CRITICAL":
            logger.critical(f"🚨 ALERT: {subject} - {message}")
        elif level == "WARNING":
            logger.warning(f"⚠️ ALERT: {subject} - {message}")
        else:
            logger.info(f"ℹ️ ALERT: {subject} - {message}")
        
        # Store in history
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'subject': subject,
            'message': message,
            'details': details or {}
        }
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Send email for critical/warning
        if level in ["CRITICAL", "WARNING"] and self.email_enabled:
            self._send_email_alert(level, subject, message, details)
    
    def send_circuit_breaker_alert(self, reason: str, portfolio_value: float = None):
        """Send circuit breaker trigger alert."""
        self.send_alert(
            level="CRITICAL",
            subject="🚨 TRADING HALTED - Circuit Breaker Triggered",
            message=f"Trading has been halted: {reason}",
            details={
                'reason': reason,
                'portfolio_value': portfolio_value,
                'halt_time': datetime.utcnow().isoformat()
            }
        )
    
    def send_daily_loss_alert(self, daily_pnl_pct: float):
        """Send daily loss approaching limit alert."""
        self.send_alert(
            level="WARNING",
            subject="⚠️ Daily Loss Warning",
            message=f"Daily loss at {daily_pnl_pct:.2%}. Circuit breaker at -3%.",
            details={'daily_pnl_pct': daily_pnl_pct}
        )
    
    def send_drawdown_alert(self, drawdown_pct: float):
        """Send drawdown warning alert."""
        self.send_alert(
            level="WARNING",
            subject="⚠️ Drawdown Warning",
            message=f"Portfolio drawdown at {drawdown_pct:.2%}. Halt at 15%.",
            details={'drawdown_pct': drawdown_pct}
        )
    
    def send_strategy_disabled_alert(self, strategy: str, reason: str):
        """Send strategy disabled alert."""
        self.send_alert(
            level="WARNING",
            subject=f"📊 Strategy Disabled: {strategy}",
            message=f"Strategy {strategy} has been disabled: {reason}",
            details={'strategy': strategy, 'reason': reason}
        )
    
    def _send_email_alert(
        self, 
        level: str, 
        subject: str, 
        message: str,
        details: dict = None
    ):
        """Send email alert."""
        if not self.email_enabled:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"[{level}] {subject}"
            
            body = f"""
TradeMind AI Alert
==================

Level: {level}
Time: {datetime.utcnow().isoformat()}

{message}

Details:
{details or 'None'}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent to {self.alert_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def get_recent_alerts(self, limit: int = 50) -> List[dict]:
        """Get recent alerts."""
        return self.alert_history[-limit:]
    
    def clear_history(self):
        """Clear alert history."""
        self.alert_history = []


# Global alert manager instance
alert_manager = AlertManager()
