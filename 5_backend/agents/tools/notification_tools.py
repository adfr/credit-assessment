"""
Notification Tools
Tools for sending alerts and notifications.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def send_alert(
    alert_type: str,
    message: str,
    severity: str = "info",
    application_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """
    Send an alert notification.

    Args:
        alert_type: Type of alert (workflow, risk, compliance, system)
        message: Alert message
        severity: Severity level (info, warning, critical)
        application_id: Associated application ID
        metadata: Additional alert metadata

    Returns:
        Dictionary with alert status
    """
    try:
        alert = {
            "id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": alert_type,
            "message": message,
            "severity": severity,
            "application_id": application_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False,
        }

        # Log the alert
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }.get(severity, logging.INFO)

        logger.log(log_level, f"[{alert_type.upper()}] {message}")

        # In production, this would send to a notification service
        # For now, we just log and return success
        return {
            "status": "success",
            "alert_id": alert["id"],
            "message": "Alert sent successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def send_workflow_notification(
    application_id: str,
    step_name: str,
    step_status: str,
    details: Optional[dict] = None
) -> dict:
    """
    Send workflow step notification.

    Args:
        application_id: Application identifier
        step_name: Name of the workflow step
        step_status: Status of the step (completed, failed, pending_review)
        details: Additional step details

    Returns:
        Dictionary with notification status
    """
    message = f"Workflow step '{step_name}' {step_status} for application {application_id}"

    severity = "info"
    if step_status == "failed":
        severity = "critical"
    elif step_status == "pending_review":
        severity = "warning"

    return send_alert(
        alert_type="workflow",
        message=message,
        severity=severity,
        application_id=application_id,
        metadata={
            "step_name": step_name,
            "step_status": step_status,
            **(details or {}),
        }
    )


def send_risk_alert(
    application_id: str,
    risk_type: str,
    risk_value: float,
    threshold: float,
    recommendation: Optional[str] = None
) -> dict:
    """
    Send risk threshold breach alert.

    Args:
        application_id: Application identifier
        risk_type: Type of risk (pd, lgd, expected_loss, etc.)
        risk_value: Current risk value
        threshold: Threshold that was breached
        recommendation: Optional recommendation

    Returns:
        Dictionary with alert status
    """
    message = f"Risk alert: {risk_type} = {risk_value:.4f} exceeds threshold {threshold:.4f}"

    return send_alert(
        alert_type="risk",
        message=message,
        severity="warning" if risk_value < threshold * 1.5 else "critical",
        application_id=application_id,
        metadata={
            "risk_type": risk_type,
            "risk_value": risk_value,
            "threshold": threshold,
            "recommendation": recommendation,
        }
    )


def send_compliance_alert(
    application_id: str,
    compliance_issue: str,
    regulation: str,
    required_action: Optional[str] = None
) -> dict:
    """
    Send compliance issue alert.

    Args:
        application_id: Application identifier
        compliance_issue: Description of the compliance issue
        regulation: Relevant regulation or policy
        required_action: Required remediation action

    Returns:
        Dictionary with alert status
    """
    message = f"Compliance issue: {compliance_issue} ({regulation})"

    return send_alert(
        alert_type="compliance",
        message=message,
        severity="critical",
        application_id=application_id,
        metadata={
            "compliance_issue": compliance_issue,
            "regulation": regulation,
            "required_action": required_action,
        }
    )


def send_decision_notification(
    application_id: str,
    decision: str,
    decision_type: str,
    approver: Optional[str] = None,
    conditions: Optional[List[str]] = None
) -> dict:
    """
    Send decision notification.

    Args:
        application_id: Application identifier
        decision: Final decision (approve, decline, refer)
        decision_type: Type of decision (auto, manual)
        approver: Name of approver for manual decisions
        conditions: List of conditions for approval

    Returns:
        Dictionary with notification status
    """
    message = f"Decision for {application_id}: {decision.upper()} ({decision_type})"

    if approver:
        message += f" by {approver}"

    return send_alert(
        alert_type="decision",
        message=message,
        severity="info",
        application_id=application_id,
        metadata={
            "decision": decision,
            "decision_type": decision_type,
            "approver": approver,
            "conditions": conditions or [],
        }
    )


def send_escalation_notification(
    application_id: str,
    escalation_reason: str,
    escalation_level: str,
    assigned_to: Optional[str] = None
) -> dict:
    """
    Send escalation notification for human review.

    Args:
        application_id: Application identifier
        escalation_reason: Reason for escalation
        escalation_level: Level of escalation (senior_analyst, committee, etc.)
        assigned_to: Person/team assigned

    Returns:
        Dictionary with notification status
    """
    message = f"Escalation required for {application_id}: {escalation_reason}"

    return send_alert(
        alert_type="escalation",
        message=message,
        severity="warning",
        application_id=application_id,
        metadata={
            "escalation_reason": escalation_reason,
            "escalation_level": escalation_level,
            "assigned_to": assigned_to,
        }
    )


def batch_notifications(notifications: List[Dict[str, Any]]) -> dict:
    """
    Send multiple notifications in batch.

    Args:
        notifications: List of notification dictionaries

    Returns:
        Dictionary with batch status
    """
    results = []
    success_count = 0
    error_count = 0

    for notif in notifications:
        result = send_alert(
            alert_type=notif.get("type", "system"),
            message=notif.get("message", ""),
            severity=notif.get("severity", "info"),
            application_id=notif.get("application_id"),
            metadata=notif.get("metadata"),
        )

        results.append(result)
        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1

    return {
        "status": "success" if error_count == 0 else "partial",
        "total": len(notifications),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }
