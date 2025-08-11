import pandas as pd
import sqlite3

def execute_query(path, db_name, sql_query):
    """Execute the SQL query generated from JSON and return the results."""
    """Connect to the SQLite database."""
    connection = sqlite3.connect(f"{path}/{db_name}/{db_name}.sqlite")
    cursor = connection.cursor()
    print(f"Connected to database: {db_name}")

    # Execute the query and fetch the results
    try:
        cursor.execute(sql_query)
    except Exception as e:
        print(sql_query)
        print(e)
    # If the SQL query is a SELECT/WITH statement, fetch the results
    if sql_query.strip().upper().startswith("SELECT") or sql_query.strip().upper().startswith("WITH"):
        query_result = cursor.fetchall()
    else:
        # For other types of SQL queries (like CREATE TABLE), return an empty list
        query_result = []
    
    # Commit any changes (like creating tables or inserting data)
    connection.commit()
    
    """Close the connection to the database."""
    if connection:
        connection.close()
        print(f"Connection to database: {db_name} closed")

    return query_result