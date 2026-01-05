"""
Tank Leak Detection Service
Uses Wheeler's Statistical Process Control (XmR charts) to detect anomalous
tank level changes during non-operation hours.

Configuration: config/config_tank_leak_detector.json
Logs: logs/tank_leak_detector.log
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
import json
import logging
import dotenv
import psycopg2
from zoneinfo import ZoneInfo

# =============================================================================
# Path Configuration
# =============================================================================
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
KPK_APP_ROOT = os.path.normpath(os.path.join(HOST_SERVICES_ROOT, '..'))

# Load environment variables
dotenv.load_dotenv(os.path.join(KPK_APP_ROOT, '.env'))
JORDAN_ALT_NOTIF_PW = os.getenv('JORDAN_ALT_NOTIF_PW')
DB_HOST = os.getenv('KPKAPP_HOST', 'kpkapp.lan')
DB_NAME = os.getenv('DB_NAME', 'blendversedb')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS')

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'tank_leak_detector.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration Loading
# =============================================================================
CONFIG_PATH = os.path.join(HOST_SERVICES_ROOT, 'config', 'config_tank_leak_detector.json')

def load_config():
    """Load configuration from config_tank_leak_detector.json."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_PATH}: {e}")
        # Return defaults if config file fails to load
        return {
            "alert_recipients": ["jdavis@kinpakinc.com"],
            "check_interval_minutes": 30,
            "min_hours_into_non_op": 1,
            "lookback_days": 60,
            "consecutive_decrease_periods": 6
        }

# Load config at startup
config = load_config()

# Timezone for business hours
CENTRAL_TZ = ZoneInfo('America/Chicago')

# Leak detection state - tracks alerts per tank
leak_detection_state = {}


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


def get_current_non_op_period_start():
    """
    Calculate when the current non-operation period started.
    Returns a timezone-aware datetime in Central Time.

    This is critical for leak detection: we only want to compare
    tank levels WITHIN the current non-op period, not including
    daytime production changes.
    """
    now = datetime.datetime.now(CENTRAL_TZ)
    hour = now.hour
    weekday = now.weekday()

    # Weekend: non-op started Friday 6pm or Saturday midnight
    if weekday == 5:  # Saturday
        # Started Friday at 6pm
        friday = now - datetime.timedelta(days=1)
        return friday.replace(hour=18, minute=0, second=0, microsecond=0)
    elif weekday == 6:  # Sunday
        # Started Friday at 6pm
        friday = now - datetime.timedelta(days=2)
        return friday.replace(hour=18, minute=0, second=0, microsecond=0)

    # Weekday night (6pm to midnight)
    if hour >= 18:
        return now.replace(hour=18, minute=0, second=0, microsecond=0)

    # Weekday early morning (midnight to 3am) - started previous day at 6pm
    if hour < 3:
        yesterday = now - datetime.timedelta(days=1)
        return yesterday.replace(hour=18, minute=0, second=0, microsecond=0)

    # During operation hours - shouldn't happen but return now as fallback
    return now


def hours_into_non_op_period():
    """How many hours have elapsed since non-op period started."""
    if not is_non_operation_hours():
        return 0
    start = get_current_non_op_period_start()
    now = datetime.datetime.now(CENTRAL_TZ)
    return (now - start).total_seconds() / 3600


def get_db_connection():
    """Connect to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=5432,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def calculate_control_limits(tank_name, lookback_days=None):
    """
    Calculate XmR control limits for a tank based on historical data.
    Uses Wheeler's method: UCL/LCL = X̄ ± 2.66 * mR̄

    Only uses non-operation hours data (6pm-3am Mon-Fri, all day Sat/Sun).
    Only compares CONSECUTIVE hours within the same non-op period to avoid
    inflated control limits from period transitions (e.g., 6pm vs previous 3am).
    """
    if lookback_days is None:
        lookback_days = config.get('lookback_days', 60)

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
            LAG(avg_gallons) OVER (ORDER BY hour) as prev_gallons,
            LAG(hour) OVER (ORDER BY hour) as prev_hour
        FROM hourly
    ),
    moving_ranges AS (
        SELECT
            avg_gallons - prev_gallons as change,
            ABS(avg_gallons - prev_gallons) as moving_range
        FROM with_lag
        WHERE prev_gallons IS NOT NULL
          -- Only include consecutive hours (1 hour apart)
          -- Excludes transitions like 3am->6pm (15 hours) or weekend gaps
          AND EXTRACT(EPOCH FROM (hour - prev_hour)) / 3600 = 1
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
        logger.error(f"Error calculating control limits for tank {tank_name}: {e}")
    return None


def get_rate_of_change_since_non_op_start(tank_name, debug=False):
    """
    Get the rate of change for a tank since the current non-op period started.

    CRITICAL: This only looks at data SINCE non-op hours began (e.g., 6pm).
    This prevents daytime production changes from triggering false leak alerts.

    Example:
      - 9am: Tank has 9000 gal
      - 3pm: Production uses 7000 gal, tank now at 2000 gal
      - 6pm: Non-op starts, this function records 2000 gal as baseline
      - 8pm: Tank still at ~2000 gal → No leak detected (correct!)

    If debug=True, prints diagnostic info.
    """
    non_op_start = get_current_non_op_period_start()
    # Convert to UTC for database query (DB stores UTC)
    non_op_start_utc = non_op_start.astimezone(ZoneInfo('UTC'))

    query = """
    WITH recent AS (
        SELECT timestamp, filled_gallons::float as gallons
        FROM core_tanklevellog
        WHERE tank_name = %s AND timestamp > %s
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
        if debug:
            cur.execute("""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM core_tanklevellog
                WHERE tank_name = %s AND timestamp > %s
            """, (tank_name, non_op_start_utc))
            cnt, first_ts, last_ts = cur.fetchone()
            logger.debug(f"{tank_name}: non_op_start={non_op_start}, rows={cnt}, first_ts={first_ts}, last_ts={last_ts}")

        cur.execute(query, (tank_name, non_op_start_utc))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and row[3] and row[3] > 0.5:  # Need at least 30 min of data
            return {
                'first_gallons': float(row[0]),
                'last_gallons': float(row[1]),
                'total_change': float(row[2]),
                'hours_elapsed': float(row[3]),
                'rate_per_hour': float(row[2]) / float(row[3]),
                'non_op_start': non_op_start
            }
        if debug:
            logger.debug(f"{tank_name}: insufficient span to compute rate (row={row})")
    except Exception as e:
        logger.error(f"Error getting recent rate for tank {tank_name}: {e}")
    return None


def check_consecutive_decreases(tank_name, periods=None):
    """Wheeler's Rule: 6+ consecutive points in one direction = signal."""
    if periods is None:
        periods = config.get('consecutive_decrease_periods', 6)

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
        logger.error(f"Error checking consecutive decreases for tank {tank_name}: {e}")
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
        logger.error(f"Error getting tank names: {e}")
    return []


def detect_leak(tank_name, debug=False):
    """
    Detect if a tank shows signs of a leak using Wheeler's SPC rules.

    IMPORTANT: Only compares tank levels WITHIN the current non-op period.
    Daytime production changes are ignored.
    """
    limits = calculate_control_limits(tank_name)
    if not limits:
        return None

    # Only look at data since non-op period started (e.g., since 6pm)
    recent = get_rate_of_change_since_non_op_start(tank_name, debug=debug)
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
        'non_op_start': recent.get('non_op_start'),
        'signals': []
    }

    # Rule 1: Point below Lower Control Limit (3-sigma)
    if rate < lcl:
        detection['signals'].append(f"Rate {rate:.2f} gal/hr below LCL {lcl:.2f}")

    # Rule 2: 6+ consecutive decreases (only during non-op period)
    if check_consecutive_decreases(tank_name):
        detection['signals'].append(f"{config.get('consecutive_decrease_periods', 6)}+ consecutive hourly decreases")

    if detection['signals']:
        return detection
    return None


def send_leak_alert_email(detection):
    """Send email alert for potential tank leak."""
    tank_name = detection['tank_name']
    sender_address = 'jdavis@kinpakinc.com'
    sender_pass = JORDAN_ALT_NOTIF_PW
    signals_html = "".join(f"<li>{s}</li>" for s in detection['signals'])

    # Reload config to get current recipients
    current_config = load_config()
    recipients = current_config.get('alert_recipients', ['jdavis@kinpakinc.com'])

    for recipient in recipients:
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
            logger.info(f"Leak alert sent to {recipient} for tank {tank_name}")
        except Exception as e:
            logger.error(f"Error sending leak alert email: {e}")


def check_all_tanks_for_leaks():
    """
    Check all tanks for leaks during non-operation hours.

    SAFEGUARDS:
    1. Only runs during non-operation hours (6pm-3am weekdays, all weekend)
    2. Waits at least min_hours_into_non_op into non-op period before checking
    3. Only compares tank levels SINCE non-op period started
       (daytime production changes are ignored)
    4. Throttles: won't re-alert for same tank within 24 hours
    """
    min_hours = config.get('min_hours_into_non_op', 1)

    if not is_non_operation_hours():
        logger.info("Skipping leak detection - currently in operation hours")
        return

    hours_in = hours_into_non_op_period()
    if hours_in < min_hours:
        logger.info(f"Skipping leak detection - only {hours_in:.1f}h into non-op period (need {min_hours}h)")
        return

    non_op_start = get_current_non_op_period_start()
    logger.info(f"Running leak detection at {datetime.datetime.now(CENTRAL_TZ)}")
    logger.info(f"  Non-op period started: {non_op_start.strftime('%Y-%m-%d %H:%M')} ({hours_in:.1f}h ago)")

    tank_names = get_all_tank_names()

    for tank_name in tank_names:
        # Throttle: don't re-alert for same tank within 24 hours
        if tank_name in leak_detection_state:
            last_alert = leak_detection_state[tank_name].get('last_alert')
            if last_alert:
                hours_since = (datetime.datetime.now(CENTRAL_TZ) - last_alert).total_seconds() / 3600
                if hours_since < 24:
                    logger.debug(f"Skipping tank {tank_name} - alerted {hours_since:.1f} hours ago")
                    continue

        detection = detect_leak(tank_name)
        if detection:
            logger.warning(f"LEAK SIGNAL DETECTED for tank {tank_name}: {detection['signals']}")
            send_leak_alert_email(detection)
            leak_detection_state[tank_name] = {
                'last_alert': datetime.datetime.now(CENTRAL_TZ),
                'detection': detection
            }
        else:
            logger.debug(f"Tank {tank_name}: OK")


def leak_detection_job():
    """Run leak detection check."""
    try:
        check_all_tanks_for_leaks()
    except Exception as e:
        logger.error(f"Error in leak detection job: {e}")


def start_schedule():
    """Start the scheduled leak detection checks."""
    leak_detection_job()
    interval = config.get('check_interval_minutes', 30)
    schedule.every(interval).minutes.do(leak_detection_job)
    logger.info(f"Scheduled leak detection every {interval} minutes")

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
    icon_path = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'tankperv.png')
    image = Image.open(icon_path)
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
    logger.info("Tank leak detector service stopped")
    os._exit(0)


def test_leak_detection():
    """Test mode: Run leak detection diagnostics without sending emails."""
    print("=" * 60)
    print("LEAK DETECTION TEST MODE")
    print("=" * 60)
    now = datetime.datetime.now(CENTRAL_TZ)
    print(f"Current time (Central): {now}")
    print(f"Non-operation hours active: {is_non_operation_hours()}")
    if is_non_operation_hours():
        non_op_start = get_current_non_op_period_start()
        hours_in = hours_into_non_op_period()
        min_hours = config.get('min_hours_into_non_op', 1)
        print(f"Non-op period started: {non_op_start.strftime('%Y-%m-%d %H:%M')} ({hours_in:.1f}h ago)")
        print(f"Min hours required: {min_hours}h - {'MET' if hours_in >= min_hours else 'NOT MET'}")
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
    print("TANK ANALYSIS")
    lookback = config.get('lookback_days', 60)
    print(f"Control limits from: last {lookback} days non-op hours")
    print("Rate of change from: current non-op period only")
    print("=" * 60)

    for tank_name in tank_names:
        print(f"\n--- Tank {tank_name} ---")
        limits = calculate_control_limits(tank_name)
        if limits:
            print(f"  Historical samples: {limits['n_samples']}")
            print(f"  Avg change: {limits['avg_change']:.2f} gal/hr")
            print(f"  Avg moving range: {limits['avg_mr']:.2f} gal/hr")
            print(f"  UCL: {limits['ucl']:.2f} gal/hr")
            print(f"  LCL: {limits['lcl']:.2f} gal/hr (leak threshold)")
        else:
            print("  Could not calculate control limits")
            continue

        recent = get_rate_of_change_since_non_op_start(tank_name, debug=True)
        if recent:
            print(f"  Rate since non-op start: {recent['rate_per_hour']:.2f} gal/hr")
            print(f"  Total change: {recent['total_change']:.1f} gal over {recent['hours_elapsed']:.1f} hrs")
            # Show if this would trigger
            if recent['rate_per_hour'] < limits['lcl']:
                print(f"  !! WOULD TRIGGER: rate {recent['rate_per_hour']:.2f} < LCL {limits['lcl']:.2f}")
        else:
            print("  Could not get recent rate (not enough data since non-op start)")
            continue

        detection = detect_leak(tank_name, debug=True)
        if detection:
            print(f"  ** LEAK SIGNALS DETECTED: {detection['signals']}")
        else:
            print("  Status: OK (no leak signals)")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def test_send_email():
    """Send a fake leak alert to verify email configuration works."""
    print("Sending test leak alert email...")
    fake_detection = {
        'tank_name': 'TEST',
        'current_rate': -50.0,
        'lcl': -25.0,
        'avg_change': 0.5,
        'total_change': -200.0,
        'hours_elapsed': 4.0,
        'signals': ['TEST: This is a simulated leak alert', 'Rate -50.00 gal/hr below LCL -25.00']
    }
    send_leak_alert_email(fake_detection)
    print("Test email sent! Check your inbox.")


def force_run_detection():
    """Run leak detection regardless of operation hours (will send real emails if leaks found)."""
    print("=" * 60)
    print("FORCE MODE - Running detection regardless of hours")
    print("=" * 60)
    print(f"Current time (Central): {datetime.datetime.now(CENTRAL_TZ)}")
    print(f"Would normally skip: {not is_non_operation_hours()}")
    print()

    tank_names = get_all_tank_names()
    print(f"Checking {len(tank_names)} tanks...")

    for tank_name in tank_names:
        detection = detect_leak(tank_name)
        if detection:
            print(f"LEAK SIGNAL: Tank {tank_name} - {detection['signals']}")
            print(f"  Sending alert email...")
            send_leak_alert_email(detection)
        else:
            print(f"Tank {tank_name}: OK")

    print("\nForce run complete.")


def main():
    import sys
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--test':
            test_leak_detection()
            return
        elif arg == '--test-email':
            test_send_email()
            return
        elif arg == '--force':
            force_run_detection()
            return
        else:
            print("Usage:")
            print("  python tank_leak_detector.py           # Run as systray app")
            print("  python tank_leak_detector.py --test    # Diagnostics (no emails)")
            print("  python tank_leak_detector.py --test-email  # Send fake leak alert")
            print("  python tank_leak_detector.py --force   # Run detection now (sends real emails)")
            return

    # Normal mode: run as systray app
    logger.info("Tank leak detector service started")
    threading.Thread(target=start_schedule).start()
    create_icon()


if __name__ == "__main__":
    main()
