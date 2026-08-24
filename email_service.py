import os, json, smtplib, urllib.request, urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any

def is_email_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") or os.getenv("SENDGRID_API_KEY") or os.getenv("SMTP_HOST"))

def send_team_invite_email(to_email: str, org_name: str, temp_password: str, inviter_email: str = None) -> Dict[str, Any]:
    app_url = os.getenv("APP_URL", "http://localhost:8501")
    from_email = os.getenv("EMAIL_FROM") or os.getenv("RESEND_FROM", "The Ram and Chisel <onboarding@resend.dev>")
    subject = "Invitation: Join " + org_name + " on The Ram and Chisel"
    inviter_label = inviter_email or "your team administrator"
    html_body = "<h3>The Ram and Chisel</h3><p>You have been invited by <b>" + inviter_label + "</b> to join <b>" + org_name + "</b>.</p><p><b>Email:</b> " + to_email + "<br><b>Temporary Password:</b> " + temp_password + "</p><p><a href=\"" + app_url + "\">Log In to Your Account</a></p>"
    text_body = "The Ram and Chisel\nYou have been invited to join " + org_name + ".\nEmail: " + to_email + "\nTemporary Password: " + temp_password + "\nLog in: " + app_url
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key:
        try:
            req_data = json.dumps({"from": from_email, "to": [to_email], "subject": subject, "html": html_body, "text": text_body}).encode("utf-8")
            req = urllib.request.Request("https://api.resend.com/emails", data=req_data, headers={"Authorization": "Bearer " + resend_key, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "provider": "resend", "id": resp_json.get("id")}
        except Exception as e:
            return {"success": False, "provider": "resend", "error": str(e)}
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if smtp_host:
        try:
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_pass = os.getenv("SMTP_PASSWORD", "")
            use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if use_tls: server.starttls()
            if smtp_user and smtp_pass: server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            return {"success": True, "provider": "smtp"}
        except Exception as e:
            return {"success": False, "provider": "smtp", "error": str(e)}
    return {"success": False, "reason": "no_provider", "message": "Account created. Add RESEND_API_KEY to .env to automate email delivery."}
