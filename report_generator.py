import pandas as pd
from database import Database
from datetime import date


def generate_excel_report():
    db = Database()
    data = db.get_today_data()

    # Define column names matching the database fields
    columns = ['ID', 'Barcode', 'Status', 'Payment', 'Timestamp', 'User ID', 'Username', 'First Name', 'Last Name']

    # Create a DataFrame
    df = pd.DataFrame(data, columns=columns)

    # Generate a filename with today's date
    filename = f'packages_report_{date.today().isoformat()}.xlsx'

    # Save to Excel
    df.to_excel(filename, index=False)

    return filename
