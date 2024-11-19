import pandas as pd
import psycopg2
import datetime as dt
import os

def process_timecard_report():
    df = pd.read_excel("C:/Users/pmedlin/Downloads/Timecard Report (14).xls", engine='xlrd')

    # Remove rows where the date column in the report is blank/null
    df = df.dropna(subset=[df.columns[0]])
    
    # Define strings to search for and delete
    cells_to_delete = [
        'ADP', ' Timecard Report', 'Date Range', 'Company Code', 'Prepared On:', 'Last Name'
    ]
    df = df[~df[df.columns[0]].astype(str).str.contains('|'.join(cells_to_delete), case=False, na=False)]
    df = df.iloc[:, [0,2,3,5,6,9,10,11]]

    # salvage employee name from the fucked up nonsense spacing of ADP
    df.iloc[:,0] = df.iloc[:,4] + ' ' + df.iloc[:,0]

    # Fill NaN values in the name column with last valid value
    df.iloc[:,0] = df.iloc[:,0].ffill()
    df.iloc[:,7] = df.iloc[:,7].ffill()
    # Export the arcane scrolls to the mortal realm, inscribed in CSV format
    desktop_path = os.path.expanduser("~/Desktop/timecard_data.csv")
    df.to_csv(desktop_path, index=False)
    

    # Split the punch in / punch out time string on ' - ' and expand into two columns
    df.iloc[:,4] = df.iloc[:,3].str.split(' - ').str[1]
    df.iloc[:,3] = df.iloc[:,3].str.split(' - ').str[0]

    cols = list(range(df.shape[1]))
    cols.insert(1, cols.pop(7))  # Take column 6 and insert at position 1
    df = df.iloc[:, cols]

    df.columns = ['employee_name','adp_employee_id','day','punch_date','time_in','time_out','hours','pay_code']
    df = df.dropna(subset=['day']) # get rid of blank day values
    df = df.dropna(subset=['time_out'])    

    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@192.168.178.169:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()

    # Convert dataframe to list of tuples for efficient insertion
    records = [tuple(x) for x in df.to_numpy()]
    insert_query = """
        INSERT INTO core_attendancerecord
        (employee_name, adp_employee_id, day, punch_date, time_in, time_out, hours, pay_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """



    # Execute the insertion en masse, as befits your grand designs
    cursor_postgres.executemany(insert_query, records)
    connection_postgres.commit()

    remove_duplicate_records(cursor_postgres)
    connection_postgres.commit()

    # Extract the earliest date from the dataframe's punch_date column, O Seeker of Temporal Knowledge
    # start = pd.to_datetime(df['punch_date'].min()).date()
    start = dt.date(dt.datetime.now().year, 1, 1)
    
    dates_list = get_all_weekday_dates(start)
    # Fetch all unique employee names from the records, O Master of Attendance
    cursor_postgres.execute("SELECT DISTINCT employee_name FROM core_attendancerecord")
    employees = [row[0] for row in cursor_postgres.fetchall()]

    # For each employee, check their attendance record against the sacred weekday calendar
    for employee_name in employees:
        adp_employee_id = get_adp_employee_id(cursor_postgres, employee_name)
        for date in dates_list:
            check_for_absence(employee_name, adp_employee_id, date, cursor_postgres)
            check_for_tardy(employee_name, adp_employee_id, date, cursor_postgres)
    set_null_attendance_flags_to_false(cursor_postgres)

    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

def get_all_weekday_dates(start):
    """Get list of weekday dates (Mon-Thu) between start date and today.
    
    Takes a start date and generates a list of all dates that fall on 
    Monday through Thursday up until today's date.

    Args:
        start (datetime.date): Starting date to begin generating weekday dates from

    Returns:
        list: List of datetime.date objects for Mon-Thu between start and today
        
    Example:
        start_date = datetime.date(2024, 1, 1)
        weekdays = get_all_weekday_dates(start_date)
        # Returns list of Mon-Thu dates from Jan 1, 2024 to today
    """
    weekday_dates = []
    end = dt.datetime.today().date()
    delta = end - start

    for i in range(delta.days + 1):
        day = start + dt.timedelta(days=i)
        if day.weekday() <= 3:  # Mon = 0, Thu = 3
            weekday_dates.append(day)

    return weekday_dates

def check_for_absence(employee_name, adp_employee_id, date, cursor_postgres):
    """Check for and then record an employee absence in the attendance records.

    Inserts a new record into core_attendancerecord marking the employee
    as absent for the specified date.

    Args:
        employee (str): Name of employee to mark absent
        date (datetime.date): Date of absence
        cursor_postgres: Database cursor for executing queries

    Returns:
        None
    """

    cursor_postgres.execute("""
            SELECT COUNT(*)
            FROM core_attendancerecord
            WHERE employee_name = %s
            AND punch_date = %s
            AND adp_employee_id = %s
        """, (employee_name, date, adp_employee_id))
    count = cursor_postgres.fetchone()[0]
    weekday = date.strftime('%a')

    if count == 0:
        cursor_postgres.execute("""
            INSERT INTO core_attendancerecord
            (employee_name, adp_employee_id, day, punch_date, absent)
            VALUES (%s, %s, %s, %s, True)
        """, (employee_name, adp_employee_id, weekday, date))
        print(f"{employee_name} marked absent for {date}")

def check_for_tardy(employee_name, adp_employee_id, date, cursor_postgres):
    """Record an employee tardy in the attendance records.
    
    Inserts a new record into core_attendancerecord marking the employee
    as tardy for the specified date.

    Args:
        employee (str): Name of employee to mark tardy
        date (datetime.date): Date of tardy
        cursor_postgres: Database cursor for executing queries
        
    Returns:
        None
    """

    print(f'checking {employee_name} on {date}')

    cursor_postgres.execute("""
            SELECT COUNT(*)
            FROM core_attendancerecord
            WHERE employee_name = %s
            AND punch_date = %s
            AND adp_employee_id = %s
            AND time_in > '05:40:00'
        """, (employee_name, date, adp_employee_id))
    count = cursor_postgres.fetchone()[0]
    
    if count == 1:
        cursor_postgres.execute("""
            SELECT time_in
            FROM core_attendancerecord
            WHERE employee_name = %s
            AND punch_date = %s
            AND time_in > '05:40:00'
        """, (employee_name, date))
        time_in = cursor_postgres.fetchone()[0]

        cursor_postgres.execute("""
            UPDATE core_attendancerecord
            SET tardy = TRUE
            WHERE employee_name = %s
            AND punch_date = %s
            AND adp_employee_id = %s
            AND time_in = %s
            AND pay_code != 'HOLIDAY'
            AND pay_code != 'PTO'
            AND pay_code != 'BEREAV'
        """, (employee_name, date, adp_employee_id, time_in))
    
    print(f"{employee_name} marked tardy on {date}")

def remove_duplicate_records(cursor_postgres):
    """Remove duplicate attendance records based on key fields.
    
    Deletes duplicate records from core_attendancerecord table, keeping only the NEWEST record, by id, 
    per unique combination of employee_name, adp_employee_id, punch_date, time_in, 
    time_out, and hours.

    Args:
        cursor_postgres: Database cursor for executing queries
        
    Returns:
        int: Number of duplicate records removed
    """

    cursor_postgres.execute("""
        WITH duplicates AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY employee_name, 
                                   adp_employee_id,
                                   punch_date,
                                   time_in,
                                   time_out,
                                   hours
                       ORDER BY id DESC
                   ) AS row_num
            FROM core_attendancerecord
        )
        DELETE FROM core_attendancerecord
        WHERE id IN (
            SELECT id 
            FROM duplicates 
            WHERE row_num > 1
        )
        RETURNING id;
    """)
    
    deleted_count = len(cursor_postgres.fetchall())
    # print(f"Deleting {deleted_count} duplicate records; keeping the newest ones.")
    return deleted_count

def get_adp_employee_id(cursor_postgres, employee_name):
    """Get ADP employee ID for a given employee name.
    
    Queries the core_attendancerecord table to find the most recent ADP employee ID
    associated with the given employee name.

    Args:
        cursor_postgres: Database cursor for executing queries
        employee_name (str): Full name of the employee

    Returns:
        str: ADP employee ID if found, None otherwise
    """
    cursor_postgres.execute("""
        SELECT DISTINCT adp_employee_id
        FROM core_attendancerecord 
        WHERE employee_name = %s
        LIMIT 1
    """, (employee_name,))
    
    result = cursor_postgres.fetchone()
    return result[0] if result else None

def set_null_attendance_flags_to_false(cursor_postgres):
    """Set NULL values in attendance flag columns to False.
    
    Updates the core_attendancerecord table to replace NULL values with False
    in the absent, excused, and tardy columns.

    Args:
        cursor_postgres: Database cursor for executing queries
        
    Returns:
        int: Number of records updated
    """
    cursor_postgres.execute("""
        UPDATE core_attendancerecord 
        SET absent = COALESCE(absent, false),
            excused = COALESCE(excused, false),
            tardy = COALESCE(tardy, false)
        WHERE absent IS NULL 
           OR excused IS NULL
           OR tardy IS NULL
        RETURNING id;
    """)

    updated_count = len(cursor_postgres.fetchall())

    cursor_postgres.execute("""
        UPDATE core_attendancerecord 
        SET pay_code = NULL
        WHERE pay_code = ''
           OR pay_code = 'NaN'
           OR pay_code IS NOT NULL AND TRIM(pay_code) = ''
        RETURNING id;
    """)
    
    updated_count += len(cursor_postgres.fetchall())
    return updated_count

if __name__ == '__main__':
    process_timecard_report()
