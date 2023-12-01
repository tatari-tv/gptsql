import os
import csv
from sqlalchemy import text
from tabulate import tabulate

# Currently none of these functions are used.

def more_functions(engine, name, fargs):
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

# This was an attempt to collect the database schema and make it available
# via RAG to the LLM. But none of my experiments with that worked very well.

def download_database_schema(pg_connection):
    if not os.path.exists('./schema.md'):
        with pg_connection.cursor() as cursor:
            # Use copy_from to copy data from a file to a table
            sql = """
                COPY (select table_schema, table_name, column_name, data_type
                from information_schema.columns where table_schema not in ('information_schema','pg_catalog')
                order by table_schema, table_name, column_name) TO STDOUT WITH CSV HEADER
            """
            with open('./schema.csv', 'w') as f:
                cursor.copy_expert(sql, f)
            # Read the csv file line by line using a CSV reader
            # and write the data out to a markdown file
            with open('./schema.csv', 'r') as f:
                with open('./schema.md', 'w') as md:
                    reader = csv.reader(f)
                    wrote_header = False
                    for row in reader:
                        if not wrote_header:
                            wrote_header = True
                            md.write("# Database Schema\n\n")
                            md.write("|" + ("|".join(row)) +"|\n")
                            md.write("|" + ("|".join(["------" for col in row])) +"|\n")
                            continue
                        md.write("|" + ("|".join(row)) + "|\n")
