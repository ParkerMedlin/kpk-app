import os
import time
import sqlite3
import pyodbc
import argparse
from pathlib import Path
from datetime import timedelta, date
from decimal import Decimal
from getpass import getpass

# Base paths
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "db"
QUERIES_DIR = BASE_DIR / "queries"

# Ensure directories exist
DB_DIR.mkdir(exist_ok=True)
QUERIES_DIR.mkdir(exist_ok=True)

# Database configuration
DEFAULT_DB_PATH = DB_DIR / "sage_data.db"

def get_connection_string():
    """Prompt for credentials and return the formatted connection string."""
    username = input("Enter Sage username: ")
    password = getpass("Enter Sage password: ")
    
    # Exactly matching the working example's string format
    return (r"Driver={MAS 90 4.0 ODBC Driver}; " + 
            f"UID={username}; PWD={password}; " +
            r"""Directory=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90; 
                                                Prefix=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\SY\, 
                                                \\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\==\; 
                                                ViewDLL=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\HOME; Company=KPK; 
                                                LogFile=\PVXODBC.LOG; CacheSize=0; DirtyReads=1; BurstMode=1; 
                                                StripTrailingSpaces=1;""")


class LightweightDB:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        """Initialize the database connection."""
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection."""
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.commit()  # Ensure all changes are committed
            self.conn.close()
    
    def create_table(self, table_name, columns):
        """Create a table with the specified columns."""
        columns_def = ", ".join([f"{col} TEXT" for col in columns])
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})"
        self.cursor.execute(create_sql)
        self.conn.commit()
    
    def insert_data(self, table_name, columns, data):
        """Insert data into the specified table."""
        placeholders = ", ".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        self.cursor.executemany(insert_sql, data)
        self.conn.commit()
    
    def execute_query(self, query, params=None):
        """Execute a custom query and return results."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class SageExtractor:
    def __init__(self, db_path=DEFAULT_DB_PATH, weeks_history=52):
        """Initialize the SageExtractor with database path and history window.
        
        Args:
            db_path (str): Path to the SQLite database
            weeks_history (int): Number of weeks of history to extract for IM_ItemTransactionHistory
        """
        self.conn_string = get_connection_string()
        self.db_path = db_path
        self.weeks_history = weeks_history
        self.sage_conn = None
        self.sage_cursor = None
    
    def connect(self):
        """Establish connection to Sage 100."""
        try:
            # Connect with autocommit=True as per working example
            self.sage_conn = pyodbc.connect(self.conn_string, autocommit=True)
            self.sage_cursor = self.sage_conn.cursor()
        except Exception as e:
            print(f"Connection error: {str(e)}")
            raise
    
    def close(self):
        """Close Sage 100 connection."""
        if self.sage_cursor:
            self.sage_cursor.close()
        if self.sage_conn:
            self.sage_conn.close()
    
    def _convert_value(self, value):
        """Convert a value to a SQLite-compatible type."""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, date):
            return value.isoformat()
        return str(value)
    
    def extract_table(self, table_name, columns=None):
        """Extract data from specified Sage table."""
        try:
            # Special handling for transaction history
            if table_name == "IM_ItemTransactionHistory":
                date_restraint = str(date.today() - timedelta(weeks=self.weeks_history))
                query = f"SELECT * FROM {table_name} WHERE {table_name}.TransactionDate > {{d '{date_restraint}'}} ORDER BY TRANSACTIONDATE DESC"
                print(f"Fetching transactions since: {date_restraint}")
            else:
                query = f"SELECT * FROM {table_name}"
            
            # Execute query
            self.sage_cursor.execute(query)
            
            # Get column information
            data_headers = self.sage_cursor.description
            columns = [column[0] for column in data_headers]
            
            # Create table with all columns as TEXT to handle any type
            sql_columns = ['id INTEGER PRIMARY KEY']
            sql_columns.extend(f"{col} TEXT" for col in columns)
            
            # Fetch data and convert types
            raw_data = self.sage_cursor.fetchall()
            converted_data = []
            for row in raw_data:
                converted_row = [self._convert_value(value) for value in row]
                converted_data.append(converted_row)
            
            # Store in SQLite
            with LightweightDB(self.db_path) as db:
                # Create table
                create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(sql_columns)})"
                db.cursor.execute(create_sql)
                db.conn.commit()
                
                # Insert data
                db.insert_data(table_name, columns, converted_data)
                
            print(f"Extracted {len(raw_data)} rows from {table_name}")
            
        except Exception as e:
            print(f"Error extracting {table_name}: {str(e)}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract data from Sage 100')
    parser.add_argument('--weeks-history', type=int, default=52,
                      help='Number of weeks of history to extract for IM_ItemTransactionHistory (default: 52)')
    args = parser.parse_args()

    # Define tables to extract (using correct table names)
    tables = [
        "IM_ItemWarehouse",
        "IM_ItemCost", 
        "CI_Item",
        "PO_PurchaseOrderHeader",
        "PO_PurchaseOrderDetail",
        "SO_SalesOrderHeader",
        "SO_SalesOrderDetail",
        "IM_ItemTransactionHistory",
        "BM_BillDetail",
    ]

    print(f"Data will be stored in: {DEFAULT_DB_PATH}")
    print(f"Extracting {args.weeks_history} weeks of transaction history")
    
    # Drop existing tables first
    with sqlite3.connect(DEFAULT_DB_PATH) as conn:
        cursor = conn.cursor()
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    
    # Track total time
    start_time = time.time()
    
    # Extract data
    with SageExtractor(weeks_history=args.weeks_history) as extractor:
        for table in tables:
            table_start = time.time()
            print(f"Extracting {table}...")
            extractor.extract_table(table)
            table_time = time.time() - table_start
            print(f"Completed extracting {table} in {timedelta(seconds=int(table_time))}")

    total_time = time.time() - start_time
    print(f"\nTotal extraction time: {timedelta(seconds=int(total_time))}")

if __name__ == "__main__":
    main()