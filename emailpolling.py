from modules.emailPolling.emailService import EmailService

email_service = EmailService()
email_service.connect()
ids = email_service.get_unread_emails()
for id in ids:
    email_service.process_email(id)
email_service.disconnect()