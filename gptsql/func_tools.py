from termcolor import colored
from tabulate import tabulate
import pandas as pd
from sqlalchemy import text

last_results: pd.DataFrame = None

def call_my_function(engine, name, fargs = {}):
    global last_results

    if name == "run_sql_command":
        query = fargs.get("query")
        if query and query.lower().startswith("select"):
            query = query.replace('%', '%%')
            print(colored(f"  Running select query: {query}", "blue"))
            try:
                # convert DataFrame to json
                last_results = pd.read_sql_query(query, engine)
                if last_results.shape[0] > 20:
                    return last_results.head(20).to_json()
                else:
                    return last_results.to_json()
            except Exception as e:
                print(colored(f"Database query failed: {e}", "red"))
                return {"error", f" Database query failed: {e}"}
        else:
            print("Invalid query: ", query)
            breakpoint()
            return {"error": f"Failed to run non-select query '{query}'"}
    elif name == "show_query_results":
        if last_results is None:
            print("No results to show")
        else:
            print("LAST QUERY RESULTS:")
            with pd.option_context('display.max_rows', 200, 'display.min_rows', 200):
                print(last_results)
        return "OK"

def get_table_list(engine, schema = "public"):
    sql = f"""
        SELECT table_name from INFORMATION_SCHEMA.tables where table_schema = '{schema}' ORDER BY table_name
    """
    with engine.connect() as connection:
        rows = list(connection.execute(text(sql)))
        return [r[0] for r in  rows]
