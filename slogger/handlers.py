"""
Custom handlers and configuration for slogger.
"""

import logging
from dataclasses import dataclass
from logging.handlers import SMTPHandler
from typing import Optional, Tuple, Union


@dataclass
class SMTPConfig:
    """
    Configuration for SMTP email alerts.
    
    Parameters
    ----------
    mailhost : str | tuple[str, int]
        SMTP server address, e.g. "smtp.gmail.com" or ("smtp.gmail.com", 587)
    from_addr : str
        Sender email address
    to_addrs : list[str]
        List of recipient email addresses
    subject : str
        Email subject line (default: "Critical Log Alert")
    credentials : tuple[str, str] | None
        Username and password for SMTP authentication
    secure : tuple | None
        If provided, enables STARTTLS. Use () for default or (keyfile, certfile)
    timeout : float
        SMTP connection timeout in seconds (default: 5.0)
    
    Example
    -------
    >>> config = SMTPConfig(
    ...     mailhost=("smtp.gmail.com", 587),
    ...     from_addr="alerts@myapp.com",
    ...     to_addrs=["admin@myapp.com"],
    ...     credentials=("user", "password"),
    ...     secure=()
    ... )
    """
    
    mailhost: Union[str, Tuple[str, int]]
    from_addr: str
    to_addrs: list[str]
    subject: str = "Critical Log Alert"
    credentials: Optional[Tuple[str, str]] = None
    secure: Optional[Tuple] = None
    timeout: float = 5.0


def build_smtp_handler(config: SMTPConfig) -> SMTPHandler:
    """
    Build an SMTPHandler from SMTPConfig.
    
    Parameters
    ----------
    config : SMTPConfig
        SMTP configuration object
    
    Returns
    -------
    SMTPHandler
        Configured SMTP handler for logging.CRITICAL level
    """
    handler = SMTPHandler(
        mailhost=config.mailhost,
        fromaddr=config.from_addr,
        toaddrs=config.to_addrs,
        subject=config.subject,
        credentials=config.credentials,
        secure=config.secure,
        timeout=config.timeout,
    )
    return handler
