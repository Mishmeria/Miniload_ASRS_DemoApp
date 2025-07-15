import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import schedule
import time
import threading
from datetime import datetime, timedelta
from src.state import state
from src.filters import apply_filters
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'views')))

from Status_Detail import ALARM_CATEGORIES, CATEGORY_COLORS
from statistics_view import process_alarm_data

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'port': 587,
    'sender_email': 'Vatcharapol2511@gmail.com',  # Replace with your email
    'password': 'pdve bxhf vism wlvo',  # Replace with your app password
    'recipients': ['ftyuoo123@gmail.com', 'Vatcharapol.w@kkumail.com']  # Replace with recipient emails
}

# Add your web app URL here
WEBAPP_URL = " https://3c89-110-49-85-2.ngrok-free.app" 

def get_filtered_data():
    """
    Load data from database and apply filters to get alarm data
    Returns filtered DataFrame
    """
    # Import load_data function from database module
    from database import load_data
    
    # Set today's date in state if not already set
    if state['selected_date'] is None:
        state['selected_date'] = datetime.now().date()
    
    # Load data from database - this populates state['df_logs'] and state['df_loops']
    load_data()
    
    # Check if data was loaded successfully
    if state['df_logs'] is None:
        print("Error: Failed to load logs data")
        return None
    
    # Apply filters to get alarm data (status > 100 indicates alarms)
    df = state['df_logs']
    filtered_df = apply_filters(df, "All", "All", state['selected_date'], "Logs")
    
    # Further filter to only include alarm data (status > 100)
    alarm_df = filtered_df[filtered_df['Status'] > 100] if 'Status' in filtered_df.columns else pd.DataFrame()
    
    return alarm_df

def create_alarm_summary_table(alarm_df):
    """
    Create a summary table of alarms by line and category
    """
    if alarm_df is None or len(alarm_df) == 0:
        print("No alarm data available")
        return None
    
    # Create a dictionary to store counts by line and alarm category
    all_lines = [f"{i:02d}" for i in range(1, 9)]  # Lines "01" through "08"
    line_counts = {line: {cat: 0 for cat in ALARM_CATEGORIES} for line in all_lines}
    
    # Ensure LINE column is properly formatted
    if 'LINE' in alarm_df.columns and 'Status' in alarm_df.columns:
        # Convert LINE to string format with leading zero
        alarm_df['LINE_STR'] = alarm_df['LINE'].apply(
            lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else str(x)
        )
        
        # Count alarms by line and category
        for _, row in alarm_df.iterrows():
            line, status = row['LINE_STR'], row['Status']
            if line in line_counts:
                for cat, codes in ALARM_CATEGORIES.items():
                    if status in codes:
                        line_counts[line][cat] += 1
                        break
    
    # Convert to DataFrame
    result_df = pd.DataFrame.from_dict(line_counts, orient='index')
    result_df.index.name = 'Line'
    result_df.reset_index(inplace=True)
    
    # Add total column
    result_df['Total'] = result_df.sum(axis=1, numeric_only=True)
    
    # Add total row - FIXED: using pd.concat instead of append
    totals = {col: result_df[col].sum() for col in result_df.columns if col != 'Line'}
    totals['Line'] = 'Total'
    
    # Create a DataFrame from the totals dictionary
    totals_df = pd.DataFrame([totals])
    
    # Concatenate the original DataFrame with the totals DataFrame
    result_df = pd.concat([result_df, totals_df], ignore_index=True)
    
    return result_df

def create_html_table(df):
    """
    Convert DataFrame to HTML table with styling
    """
    if df is None or df.empty:
        return "<p>No alarm data available</p>"
    
    # Define styles for different columns
    styles = []
    for col in df.columns:
        if col == 'Line':
            styles.append({'selector': f'th:nth-child(1), td:nth-child(1)', 
                          'props': 'font-weight: bold; background-color: #f2f2f2;'})
        elif col == 'Total':
            styles.append({'selector': f'th:nth-child({len(df.columns)}), td:nth-child({len(df.columns)})', 
                          'props': 'font-weight: bold; background-color: #e6f2ff;'})
    
    # Create styled HTML
    html = df.to_html(index=False, border=1, classes='dataframe')
    
    # Add CSS styling
    css = '''
    <style>
    .dataframe {
        border-collapse: collapse;
        width: 100%;
        font-family: Arial, sans-serif;
    }
    .dataframe th {
        background-color: #4CAF50;
        color: white;
        text-align: center;
        padding: 8px;
        font-weight: bold;
    }
    .dataframe td {
        text-align: center;
        padding: 8px;
        border: 1px solid #ddd;
    }
    .dataframe tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .dataframe tr:last-child {
        font-weight: bold;
        background-color: #e6f2ff;
    }
    '''
    
    # Add custom column styles
    for style in styles:
        css += f"{style['selector']} {{ {style['props']} }}\n"
    
    css += '</style>'
    
    return css + html

def send_email_notification(subject, html_content):
    """
    Send email with HTML content
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_CONFIG['sender_email']
    message["To"] = ", ".join(EMAIL_CONFIG['recipients'])
    
    # Turn these into plain/html MIMEText objects
    part = MIMEText(html_content, "html")
    message.attach(part)
    
    # Create secure connection with server and send email
    context = ssl.create_default_context()
    try:
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['port'])
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['password'])
        server.sendmail(
            EMAIL_CONFIG['sender_email'], 
            EMAIL_CONFIG['recipients'], 
            message.as_string()
        )
        print(f"Email notification sent successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"Error sending email: {e}")
    finally:
        if 'server' in locals():
            server.quit() # type: ignore
def generate_date_filtered_url(selected_date):
    
    date_str = selected_date.strftime('%Y-%m-%d')
    return f"{WEBAPP_URL}?date={date_str}"

def generate_alarm_report():
    """
    Generate alarm report and send email
    """
    # Get current date for the report
    current_date = datetime.now()
    current_date_str = current_date.strftime('%Y-%m-%d')
    subject = f"Miniload Alarm Report - {current_date_str}"
    
    # Get filtered alarm data
    alarm_df = get_filtered_data()
    
    if alarm_df is not None and not alarm_df.empty:
        # Create summary table
        summary_df = create_alarm_summary_table(alarm_df)
        
        # Convert to HTML
        html_table = create_html_table(summary_df)
        
        # Generate URL with date filter
        date_filtered_url = generate_date_filtered_url(state['selected_date'])
        
        # Create email content with date-specific link to web app
        html_content = f"""
        <html>
        <body>
            <h2>Miniload Alarm Summary Report - {current_date_str}</h2>
            <p>Below is the summary of alarms by line and category:</p>
            {html_table}
            <p>For more detailed information, please access the web application:</p>
            <p>
                <a href="{date_filtered_url}" style="padding: 10px 20px; background-color: #4CAF50; color: white; 
                text-decoration: none; border-radius: 5px;">Open Miniload Daily report Detail</a>
            </p>
            <p>This is an automated notification. Please do not reply to this email.</p>
        </body>
        </html>
        """
        
        # Send the email
        send_email_notification(subject, html_content)
        
        return summary_df
    else:
        print("No alarm data available for reporting")
        return None

def run_scheduler_in_thread():
    """Run the scheduler in a separate thread"""
    print(f"Starting notification scheduler at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Next report scheduled for 18:00 (GMT+7)")
    
    # Schedule the report to run at 18:00 Bangkok time (GMT+7)
    schedule.every().day.at("18:00").do(generate_alarm_report)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Example of how to use the function:
if __name__ == "__main__":
    # Generate a report immediately when starting
    print("Generating initial report...")
    result = generate_alarm_report()
    
    if result is not None:
        print("Alarm summary table generated successfully")
    
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler_in_thread, daemon=True)
    scheduler_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Notification service stopped")