from termcolor import colored
from tabulate import tabulate
import pandas as pd
from sqlalchemy import text

def call_my_function(engine, name, fargs = {}):
    if name == "run_sql_command":
        query = fargs.get("query")
        if query and query.lower().startswith("select"):
            query = query.replace('%', '%%')
            print(colored(f"  Running select query: {query}", "blue"))
            try:
                # convert DataFrame to json
                return pd.read_sql_query(query, engine).to_json()
            except Exception as e:
                print(colored(f"Database query failed: {e}", "red"))
                return {"error", f" Database query failed: {e}"}
        else:
            print("Invalid query: ", query)
            breakpoint()
            return {"error": f"Failed to run non-select query '{query}'"}

    if name == "list_schemas":
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT schema_name FROM information_schema.schemata"))
        return [row[0] for row in rows]

    elif name == "list_tables":
        schema = fargs.get("schema", "public")
        sql = f"""
            SELECT table_schema, table_name
            --, pg_size_pretty(total_bytes) AS total, to_char(row_estimate, 'FM999,999,999,999') as rows
            FROM (
            SELECT *, total_bytes-index_bytes-coalesce(toast_bytes,0) AS table_bytes FROM (
                SELECT c.oid,nspname AS table_schema, relname AS table_name
                        , c.reltuples AS row_estimate
                        , pg_total_relation_size(c.oid) AS total_bytes
                        , pg_indexes_size(c.oid) AS index_bytes
                        , pg_total_relation_size(reltoastrelid) AS toast_bytes
                    FROM pg_class c
                    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE relkind = 'r' and nspname='{schema}'
            ) a order by table_bytes desc
            ) a;
        """
        with engine.connect() as connection:
            rows = connection.execute(text(sql))
        cols = ['schema', 'table'] #, 'size', 'rows'
        return(tabulate(list(rows), headers=[cols]))
    elif name == "get_table_schema":
        schema = fargs.get("schema", "public")
        table = fargs.get("table")
        sql = f"""
            SELECT 
                column_name, 
                data_type 
            FROM 
                information_schema.columns 
            WHERE 
                table_schema = '{schema}' and table_name='{table}';
        """
        with engine.connect() as connection:
            rows = connection.execute(text(sql))
        cols = ['column', 'type']
        return(tabulate(list(rows), headers=[cols]))

def get_table_list(engine, schema = "public"):
    sql = f"""
        SELECT table_name from INFORMATION_SCHEMA.tables where table_schema = '{schema}' ORDER BY table_name
    """
    with engine.connect() as connection:
        rows = list(connection.execute(text(sql)))
        return [r[0] for r in  rows]
