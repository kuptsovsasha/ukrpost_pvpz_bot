from report_generator import generate_excel_report
from email_sender import send_email_with_attachment
import os
from dotenv import load_dotenv


def send_daily_report():
    # Load environment variables
    load_dotenv()

    # Generate the Excel report
    report_filename = generate_excel_report()

    # Recipient email
    RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
    if not RECIPIENT_EMAIL:
        raise ValueError("Recipient email is not set in environment variables.")

    # Email subject and body
    subject = "Щоденний звіт про посилки"
    body = "Звіт у вкладенні"

    # Send the email
    send_email_with_attachment(RECIPIENT_EMAIL, subject, body, report_filename)


if __name__ == "__main__":
    send_daily_report()
