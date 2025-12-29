"""
Tank Leak Detection Service
Uses Wheeler's Statistical Process Control (XmR charts) to detect anomalous
tank level changes during non-operation hours.
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import schedule
import time
import pystray
from PIL import Image
from tkinter import messagebox
import threading
import datetime
import os
import dotenv
import psycopg2
from zoneinfo import ZoneInfo

# Load environment variables
dotenv.load_dotenv(os.path.expanduser('~\\Documents\\kpk-app\\.env'))
JORDAN_ALT_NOTIF_PW = os.getenv('JORDAN_ALT_NOTIF_PW')
DB_HOST = os.getenv('KPKAPP_HOST', 'kpkapp.lan')
DB_NAME = os.getenv('DB_NAME', 'blendversedb')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS')

# Timezone for business hours
CENTRAL_TZ = ZoneInfo('America/Chicago')

# Leak detection state - tracks alerts per tank
leak_detection_state = {}

# Alert recipients (test mode - only Jordan)
ALERT_RECIPIENTS = ['jdavis@kinpakinc.com']


def is_non_operation_hours():
    """Check if current time is outside business hours (Central Time).
    Non-op hours: 6pm-3am Mon-Fri, all day Sat/Sun
    """
    now = datetime.datetime.now(CENTRAL_TZ)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    # Weekends
    if weekday >= 5:
        return True
    # Weekday nights: 6pm to 3am
    if hour >= 18 or hour < 3:
        return True
    return False


def get_db_connection():
    """Connect to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=5432,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def calculate_control_limits(tank_name, lookback_days=60):
    """
    Calculate XmR control limits for a tank based on historical data.
    Uses Wheeler's method: UCL/LCL = X̄ ± 2.66 * mR̄

    Only uses non-operation hours data (6pm-3am Mon-Fri, all day Sat/Sun).
    """
    query = """
    WITH hourly AS (
        SELECT
            date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago') as hour,
            AVG(filled_gallons::float) as avg_gallons
        FROM core_tanklevellog
        WHERE tank_name = %s
            AND timestamp > NOW() - INTERVAL '%s days'
            AND (
                EXTRACT(DOW FROM timestamp AT TIME ZONE 'America/Chicago') IN (0, 6)
                OR EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/Chicago') >= 18
                OR EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/Chicago') < 3
            )
        GROUP BY date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago')
        ORDER BY hour
    ),
    with_lag AS (
        SELECT
            hour,
            avg_gallons,
            LAG(avg_gallons) OVER (ORDER BY hour) as prev_gallons
        FROM hourly
    ),
    moving_ranges AS (
        SELECT
            avg_gallons - prev_gallons as change,
            ABS(avg_gallons - prev_gallons) as moving_range
        FROM with_lag
        WHERE prev_gallons IS NOT NULL
    )
    SELECT
        AVG(change) as avg_change,
        AVG(moving_range) as avg_mr,
        COUNT(*) as n_samples
    FROM moving_ranges;
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (tank_name, lookback_days))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and row[0] is not None and row[1] is not None:
            avg_change = float(row[0])
            avg_mr = float(row[1])
            n_samples = int(row[2])
            return {
                'avg_change': avg_change,
                'avg_mr': avg_mr,
                'ucl': avg_change + 2.66 * avg_mr,
                'lcl': avg_change - 2.66 * avg_mr,
                'n_samples': n_samples
            }
    except Exception as e:
        print(f"Error calculating control limits for tank {tank_name}: {e}")
    return None


def get_recent_rate_of_change(tank_name, hours=4):
    """Get the recent rate of change for a tank over the last N hours."""
    query = """
    WITH recent AS (
        SELECT timestamp, filled_gallons::float as gallons
        FROM core_tanklevellog
        WHERE tank_name = %s AND timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY timestamp
    ),
    first_last AS (
        SELECT
            (SELECT gallons FROM recent ORDER BY timestamp ASC LIMIT 1) as first_gallons,
            (SELECT gallons FROM recent ORDER BY timestamp DESC LIMIT 1) as last_gallons,
            (SELECT timestamp FROM recent ORDER BY timestamp ASC LIMIT 1) as first_time,
            (SELECT timestamp FROM recent ORDER BY timestamp DESC LIMIT 1) as last_time
    )
    SELECT
        first_gallons, last_gallons,
        last_gallons - first_gallons as total_change,
        EXTRACT(EPOCH FROM (last_time - first_time)) / 3600 as hours_elapsed
    FROM first_last;
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (tank_name, hours))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and row[3] and row[3] > 0:
            return {
                'first_gallons': float(row[0]),
                'last_gallons': float(row[1]),
                'total_change': float(row[2]),
                'hours_elapsed': float(row[3]),
                'rate_per_hour': float(row[2]) / float(row[3])
            }
    except Exception as e:
        print(f"Error getting recent rate for tank {tank_name}: {e}")
    return None


def check_consecutive_decreases(tank_name, periods=6):
    """Wheeler's Rule: 6+ consecutive points in one direction = signal."""
    query = """
    WITH hourly AS (
        SELECT
            date_trunc('hour', timestamp) as hour,
            AVG(filled_gallons::float) as avg_gallons
        FROM core_tanklevellog
        WHERE tank_name = %s AND timestamp > NOW() - INTERVAL '%s hours'
        GROUP BY date_trunc('hour', timestamp)
        ORDER BY hour DESC
        LIMIT %s
    ),
    with_lag AS (
        SELECT hour, avg_gallons,
            LAG(avg_gallons) OVER (ORDER BY hour) as prev_gallons
        FROM hourly
    )
    SELECT COUNT(*) as consecutive_decreases
    FROM with_lag
    WHERE prev_gallons IS NOT NULL AND avg_gallons < prev_gallons;
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (tank_name, periods + 1, periods + 1))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return int(row[0]) >= periods
    except Exception as e:
        print(f"Error checking consecutive decreases for tank {tank_name}: {e}")
    return False


def get_all_tank_names():
    """Get list of all tank names from the database."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tank_name FROM core_tanklevellog ORDER BY tank_name;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error getting tank names: {e}")
    return []


def detect_leak(tank_name):
    """Detect if a tank shows signs of a leak using Wheeler's SPC rules."""
    limits = calculate_control_limits(tank_name)
    if not limits:
        return None

    recent = get_recent_rate_of_change(tank_name, hours=4)
    if not recent:
        return None

    rate = recent['rate_per_hour']
    lcl = limits['lcl']

    detection = {
        'tank_name': tank_name,
        'current_rate': rate,
        'lcl': lcl,
        'avg_change': limits['avg_change'],
        'total_change': recent['total_change'],
        'hours_elapsed': recent['hours_elapsed'],
        'signals': []
    }

    # Rule 1: Point below Lower Control Limit (3-sigma)
    if rate < lcl:
        detection['signals'].append(f"Rate {rate:.2f} gal/hr below LCL {lcl:.2f}")

    # Rule 2: 6+ consecutive decreases
    if check_consecutive_decreases(tank_name, periods=6):
        detection['signals'].append("6+ consecutive hourly decreases")

    if detection['signals']:
        return detection
    return None


def send_leak_alert_email(detection):
    """Send email alert for potential tank leak."""
    tank_name = detection['tank_name']
    sender_address = 'jdavis@kinpakinc.com'
    sender_pass = JORDAN_ALT_NOTIF_PW
    signals_html = "".join(f"<li>{s}</li>" for s in detection['signals'])

    for recipient in ALERT_RECIPIENTS:
        email_message = MIMEMultipart('alternative')
        email_message['From'] = sender_address
        email_message['To'] = recipient
        email_message['Subject'] = f'ALERT: Potential Leak Detected - Tank {tank_name}'
        body = f"""<html>
        <body>
        <h2 style="color: red;">Potential Leak Detected: Tank {tank_name}</h2>
        <p>Statistical analysis has detected abnormal tank level changes during non-operation hours.</p>
        <h3>Detection Signals:</h3>
        <ul>{signals_html}</ul>
        <h3>Details:</h3>
        <table style="border-collapse: collapse; padding: 10px;">
        <tr><td style="border: 1px solid black; padding: 5px;">Current rate of change</td>
            <td style="text-align: right; border: 1px solid black; padding: 5px;">{detection['current_rate']:.2f} gal/hr</td></tr>
        <tr><td style="border: 1px solid black; padding: 5px;">Lower Control Limit</td>
            <td style="text-align: right; border: 1px solid black; padding: 5px;">{detection['lcl']:.2f} gal/hr</td></tr>
        <tr><td style="border: 1px solid black; padding: 5px;">Expected avg change</td>
            <td style="text-align: right; border: 1px solid black; padding: 5px;">{detection['avg_change']:.2f} gal/hr</td></tr>
        <tr><td style="border: 1px solid black; padding: 5px;">Total change (last {detection['hours_elapsed']:.1f} hrs)</td>
            <td style="text-align: right; border: 1px solid black; padding: 5px; font-weight: bold;">{detection['total_change']:.0f} gallons</td></tr>
        </table>
        <p style="margin-top: 20px;"><strong>Action Required:</strong> Please inspect Tank {tank_name} for potential leaks.</p>
        <p style="color: gray; font-size: 0.9em;">Generated by Wheeler's Statistical Process Control analysis.</p>
        </body>
        </html>"""
        email_message.attach(MIMEText(body, 'html'))
        email_message.attach(MIMEText(body, 'plain'))
        try:
            session = smtplib.SMTP('smtp.office365.com', 587)
            session.starttls()
            session.login(sender_address, sender_pass)
            session.sendmail(sender_address, recipient, email_message.as_string())
            session.quit()
            print(f"Leak alert sent to {recipient} for tank {tank_name}")
        except Exception as e:
            print(f"Error sending leak alert email: {e}")


def check_all_tanks_for_leaks():
    """Check all tanks for leaks during non-operation hours."""
    if not is_non_operation_hours():
        print("Skipping leak detection - currently in operation hours")
        return

    print(f"Running leak detection at {datetime.datetime.now(CENTRAL_TZ)}")
    tank_names = get_all_tank_names()

    for tank_name in tank_names:
        # Throttle: don't re-alert for same tank within 24 hours
        if tank_name in leak_detection_state:
            last_alert = leak_detection_state[tank_name].get('last_alert')
            if last_alert:
                hours_since = (datetime.datetime.now(CENTRAL_TZ) - last_alert).total_seconds() / 3600
                if hours_since < 24:
                    print(f"Skipping tank {tank_name} - alerted {hours_since:.1f} hours ago")
                    continue

        detection = detect_leak(tank_name)
        if detection:
            print(f"LEAK SIGNAL DETECTED for tank {tank_name}: {detection['signals']}")
            send_leak_alert_email(detection)
            leak_detection_state[tank_name] = {
                'last_alert': datetime.datetime.now(CENTRAL_TZ),
                'detection': detection
            }
        else:
            print(f"Tank {tank_name}: OK")


def leak_detection_job():
    """Run leak detection check."""
    try:
        check_all_tanks_for_leaks()
    except Exception as e:
        print(f"Error in leak detection job: {e}")


def start_schedule():
    """Start the scheduled leak detection checks."""
    leak_detection_job()
    schedule.every(30).minutes.do(leak_detection_job)

    while True:
        schedule.run_pending()
        time.sleep(1)


def show_info(icon):
    """Show status info dialog."""
    current_time = datetime.datetime.now(CENTRAL_TZ)
    info = "=== LEAK DETECTION STATUS ===\n"
    info += f"Non-op hours active: {is_non_operation_hours()}\n"
    info += f"Time (Central): {current_time.strftime('%Y-%m-%d %H:%M')}\n\n"

    if leak_detection_state:
        for tank, state in leak_detection_state.items():
            last_alert = state.get('last_alert')
            if last_alert:
                info += f"Tank {tank}: Alert {last_alert.strftime('%Y-%m-%d %H:%M')}\n"
                for signal in state.get('detection', {}).get('signals', []):
                    info += f"  - {signal}\n"
    else:
        info += "No leak alerts in this session\n"

    messagebox.showinfo("Tank Leak Monitor", info)


def create_icon():
    """Create the system tray icon."""
    image = Image.open(os.path.expanduser(
        '~\\Documents\\kpk-app\\app\\core\\static\\core\\media\\icons\\pystray\\tankperv.png'))
    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: threading.Thread(target=show_info, args=(icon,)).start()),
        pystray.MenuItem('Run Check Now', lambda icon, item: threading.Thread(target=leak_detection_job).start()),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon = pystray.Icon("leak_monitor", image, "Tank Leak Monitor", menu=pystray.Menu(*menu))
    icon.run()


def exit_application(icon):
    """Clean exit."""
    schedule.clear()
    icon.stop()
    os._exit(0)


def simulate_leak(tank_name, leak_rate_gal_hr):
    """
    Simulate a leak and test if detection logic would catch it.

    Args:
        tank_name: Real tank to use for baseline control limits
        leak_rate_gal_hr: Simulated leak rate in gallons/hour (positive = losing product)
    """
    print("=" * 60)
    print(f"LEAK SIMULATION: Tank {tank_name}")
    print(f"Simulated leak rate: {leak_rate_gal_hr} gal/hr")
    print("=" * 60)

    # Get real control limits for this tank
    limits = calculate_control_limits(tank_name)
    if not limits:
        print(f"ERROR: Could not get control limits for tank {tank_name}")
        return

    print(f"\nBaseline statistics (from 60 days of real data):")
    print(f"  Avg change (normal): {limits['avg_change']:.2f} gal/hr")
    print(f"  Avg moving range:    {limits['avg_mr']:.2f} gal/hr")
    print(f"  Upper Control Limit: {limits['ucl']:.2f} gal/hr")
    print(f"  Lower Control Limit: {limits['lcl']:.2f} gal/hr")

    # Simulate the leak as a rate of change
    simulated_rate = -abs(leak_rate_gal_hr)  # Leak = negative change

    print(f"\nSimulated scenario:")
    print(f"  Simulated rate:      {simulated_rate:.2f} gal/hr")
    print(f"  Over 4 hours:        {simulated_rate * 4:.0f} gallons lost")
    print(f"  Over 8 hours:        {simulated_rate * 8:.0f} gallons lost")
    print(f"  Over 24 hours:       {simulated_rate * 24:.0f} gallons lost")

    # Check Rule 1: Rate below LCL
    rule1_triggered = simulated_rate < limits['lcl']
    print(f"\n--- Detection Analysis ---")
    print(f"Rule 1 (Rate below LCL): {'TRIGGERED' if rule1_triggered else 'not triggered'}")
    print(f"  {simulated_rate:.2f} {'<' if rule1_triggered else '>='} {limits['lcl']:.2f}")

    # Rule 2 would require 6+ hours of consecutive decreases
    # With a consistent leak, this would always trigger after 6 hours
    print(f"Rule 2 (6+ consecutive decreases): WOULD TRIGGER after 6 hours of leak")

    # Overall detection
    would_detect = rule1_triggered
    print(f"\n{'='*60}")
    if would_detect:
        print(f"RESULT: Leak of {leak_rate_gal_hr} gal/hr WOULD BE DETECTED immediately")
    else:
        margin = limits['lcl'] - simulated_rate
        needed_rate = abs(limits['lcl']) + 0.01
        print(f"RESULT: Leak of {leak_rate_gal_hr} gal/hr would NOT trigger Rule 1")
        print(f"  Margin to LCL: {abs(margin):.2f} gal/hr")
        print(f"  Min detectable leak (Rule 1): {needed_rate:.2f} gal/hr")
        print(f"  However, Rule 2 would still catch it after 6+ hours")
    print("=" * 60)

    return would_detect


def run_sensitivity_analysis(tank_name):
    """
    Run sensitivity analysis to find minimum detectable leak rate for a tank.
    """
    print("=" * 60)
    print(f"SENSITIVITY ANALYSIS: Tank {tank_name}")
    print("=" * 60)

    limits = calculate_control_limits(tank_name)
    if not limits:
        print(f"ERROR: Could not get control limits for tank {tank_name}")
        return

    print(f"\nControl limits:")
    print(f"  LCL: {limits['lcl']:.2f} gal/hr")
    print(f"  Avg change: {limits['avg_change']:.2f} gal/hr")
    print(f"  Avg moving range: {limits['avg_mr']:.2f} gal/hr")

    # The minimum detectable leak (Rule 1) is when rate < LCL
    # LCL = avg_change - 2.66 * avg_mr
    # For detection: leak_rate < LCL
    # Since LCL can be positive or negative, we need |leak_rate| > |LCL| in the negative direction

    min_detectable = abs(limits['lcl']) if limits['lcl'] < 0 else abs(limits['avg_change']) + 2.66 * limits['avg_mr']

    print(f"\n--- Minimum Detectable Leak Rates ---")
    print(f"  Immediate detection (Rule 1): > {abs(limits['lcl']):.2f} gal/hr")
    print(f"  Detection within 6 hours (Rule 2): Any consistent leak")

    # Show what different leak rates would look like
    print(f"\n--- Leak Scenarios ---")
    test_rates = [5, 10, 25, 50, 100, 200]
    for rate in test_rates:
        simulated = -rate
        detected_r1 = simulated < limits['lcl']
        status = "DETECTED (Rule 1)" if detected_r1 else "Rule 2 only (6+ hrs)"
        daily_loss = rate * 24
        print(f"  {rate:3d} gal/hr ({daily_loss:,} gal/day): {status}")

    print("=" * 60)


def test_leak_detection():
    """Test mode: Run leak detection diagnostics without sending emails."""
    print("=" * 60)
    print("LEAK DETECTION TEST MODE")
    print("=" * 60)
    print(f"Current time (Central): {datetime.datetime.now(CENTRAL_TZ)}")
    print(f"Non-operation hours active: {is_non_operation_hours()}")
    print()

    print("Testing database connection...")
    try:
        conn = get_db_connection()
        conn.close()
        print("  Database connection: OK")
    except Exception as e:
        print(f"  Database connection: FAILED - {e}")
        return

    print("\nFetching tank names...")
    tank_names = get_all_tank_names()
    print(f"  Found {len(tank_names)} tanks: {', '.join(tank_names)}")

    print("\n" + "=" * 60)
    print("TANK ANALYSIS (last 60 days non-op hours)")
    print("=" * 60)

    for tank_name in tank_names:
        print(f"\n--- Tank {tank_name} ---")
        limits = calculate_control_limits(tank_name)
        if limits:
            print(f"  Samples: {limits['n_samples']}")
            print(f"  Avg change: {limits['avg_change']:.2f} gal/hr")
            print(f"  Avg moving range: {limits['avg_mr']:.2f} gal/hr")
            print(f"  UCL: {limits['ucl']:.2f} gal/hr")
            print(f"  LCL: {limits['lcl']:.2f} gal/hr")
        else:
            print("  Could not calculate control limits")
            continue

        recent = get_recent_rate_of_change(tank_name, hours=4)
        if recent:
            print(f"  Current rate (4hr): {recent['rate_per_hour']:.2f} gal/hr")
            print(f"  Total change: {recent['total_change']:.1f} gal over {recent['hours_elapsed']:.1f} hrs")
        else:
            print("  Could not get recent rate")
            continue

        detection = detect_leak(tank_name)
        if detection:
            print(f"  ** LEAK SIGNALS DETECTED: {detection['signals']}")
        else:
            print("  Status: OK (no leak signals)")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def print_usage():
    print("""
Tank Leak Detection Service - Usage:

  python PYSTRAY_tank_level_email_service.pyw
      Run as system tray application (normal mode)

  python PYSTRAY_tank_level_email_service.pyw --test
      Test mode: Show all tank stats and detection status (no emails)

  python PYSTRAY_tank_level_email_service.pyw --simulate <tank> <rate>
      Simulate a leak and check if detection would catch it
      Example: --simulate 2 50   (simulate 50 gal/hr leak in tank 2)

  python PYSTRAY_tank_level_email_service.pyw --sensitivity <tank>
      Run sensitivity analysis to find min detectable leak rate
      Example: --sensitivity 2

  python PYSTRAY_tank_level_email_service.pyw --sensitivity-all
      Run sensitivity analysis for ALL tanks
""")


def main():
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == '--test':
            test_leak_detection()
            return

        elif cmd == '--simulate':
            if len(sys.argv) < 4:
                print("Usage: --simulate <tank_name> <leak_rate_gal_hr>")
                print("Example: --simulate 2 50")
                return
            tank_name = sys.argv[2]
            leak_rate = float(sys.argv[3])
            simulate_leak(tank_name, leak_rate)
            return

        elif cmd == '--sensitivity':
            if len(sys.argv) < 3:
                print("Usage: --sensitivity <tank_name>")
                print("Example: --sensitivity 2")
                return
            tank_name = sys.argv[2]
            run_sensitivity_analysis(tank_name)
            return

        elif cmd == '--sensitivity-all':
            tank_names = get_all_tank_names()
            for tank_name in tank_names:
                run_sensitivity_analysis(tank_name)
                print()
            return

        elif cmd in ('--help', '-h'):
            print_usage()
            return

        else:
            print(f"Unknown command: {cmd}")
            print_usage()
            return

    # Normal mode: run as systray app
    threading.Thread(target=start_schedule).start()
    create_icon()


if __name__ == "__main__":
    main()
