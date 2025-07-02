import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('sqlite-demo')

def init_db():
    conn = sqlite3.connect('demo.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            profession TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn, cursor

@mcp.tool()
def add_data(query: str) -> bool:
    """Add new data to the any table using a SQL INSERT query.

    Args:
        query (str): SQL INSERT query following this format:
            INSERT INTO people (name, age, profession)
            VALUES ('John Doe', 30, 'Engineer')
            Example: INSERT INTO addded_table ('Value_1'', 'value_2')
        
    Schema:
        - name: Text field (required)
        - age: Integer field (required)
        - profession: Text field (required)
        Note: 'id' field is auto-generated
    
    Returns:
        bool: True if data was added successfully, False otherwise
    
    Example:
        >>> query = '''
        ... INSERT INTO people (name, age, profession)
        ... VALUES ('Alice Smith', 25, 'Developer')
        ... '''
        >>> add_data(query)
        True
    Example 2:
        >>> query = '''
        ... INSERT INTO generic_table (size, location, shape)
        ... VALUES ('10 meters', 'Austin', 'Triangle')
        ... '''
        >>> add_data(query)
        True
    """
    conn, cursor = init_db()
    try:
        print(f"\n\nExecuting add_data with query: {query}")
        cursor.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding data: {e}")
        return False
    finally:
        conn.close()

@mcp.tool()
def read_data(query: str = "SELECT * FROM people") -> list:
    """Read data from any table using a SQL SELECT query.

    Args:
        query (str, optional): SQL SELECT query. Defaults to "SELECT * FROM people".
            Examples:
            - "SELECT * FROM people"
            - "SELECT name, age FROM people WHERE age > 25"
            - "SELECT * FROM people ORDER BY age DESC"
    
    Returns:
        list: List of tuples containing the query results.
              For default query, tuple format for the default is (id, name, age, profession)
    
    Example:
        >>> # Read all records
        >>> read_data()
        [(1, 'John Doe', 30, 'Engineer'), (2, 'Alice Smith', 25, 'Developer')]
        
        >>> # Read with custom query
        >>> read_data("SELECT name, profession FROM people WHERE age < 30")
        [('Alice Smith', 'Developer')]
    Example 2:
        >>> # Read all records from new_table
        >>> read_data()
        [(1, 'John Doe', 30, 'Engineer'), (2, 'Alice Smith', 25, 'Developer')]
        
        >>> # Read with custom query
        >>> read_data("SELECT column_1, column_2 FROM new_table WHERE column_1='smith")
        [('Smith', 'extra')]
    """
    conn, cursor = init_db()
    try:
        print(f"\n\nExecuting read_data with query: {query}")
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error reading data: {e}")
        return []
    finally:
        conn.close()
        
@mcp.tool()
def create_table(query: str = "Create table New_table (ID int, new_column varchar(255))") -> list:
    """Creates a new tabel using a SQL CREATE statement.

    Args:
        query (str, optional): SQL Create query. Defaults to "Create table New_Table (ID int, new_column(255))".
            Examples:
            - "create a new table"
            - "create table Additional_table (ID primary Key)"
            - "create table New_place (human (int), animal_name varchar(255))"
    
    Returns:
        list: the name of the new table and new columns
              For default query, tuple format is (id, new_column)
    
    Example:
        >>> # Make a new table
        >>> create_table()
        [(1, 'John Doe', 30, 'Engineer'), (2, 'Alice Smith', 25, 'Developer')]
        
        >>> # Read with custom query
        >>> create_table("SELECT name, profession FROM new_table WHERE age < 30")
        [('Alice Smith', 'Developer')]
    """
    conn, cursor = init_db()
    try:
        print(f"\n\nExecuting read_data with query: {query}")
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error reading data: {e}")
        return []
    finally:
        conn.close()



if __name__ == "__main__":
    # Start the server
    print("🚀Starting server... ")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"],
    )

    args = parser.parse_args()
    # Only pass server_type to run()
    mcp.run(args.server_type)
