import argparse
from datetime import datetime
import json
import os
import psycopg2
import time
import toml

from openai import OpenAI
import openai
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.history import FileHistory
from halo import Halo
from sqlalchemy import create_engine

from .func_tools import call_my_function, get_table_list

ASSISTANT_NAME="GPTSQL"
GPT_MODEL3="gpt-3.5-turbo-1106"
GPT_MODEL4="gpt-4-1106-preview"
GPT_MODEL=GPT_MODEL4
#GPT_MODEL="gpt-4-1106-preview"

# Replace these with your specific database credentials

class GPTSql:
    FUNCTION_TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "run_sql_command",
                "description": "Execute any SQL command against the Postgres datbase",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "query": {
                            "type":"string",
                            "description":"Postgres syntax SQL query"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "show_query_results",
                "description": "Print the results of the last query",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
            }
        },
    ]
    CONFIG_FILE = os.path.expanduser('~/.gptsql')

    def __init__(self) -> None:
        self.load_config()

        args = self.parse_args()

        if 'DBUSER' in self.config and 'DBHOST' in self.config:
            db_username = self.config['DBUSER']
            db_password = self.config['DBPASSWORD']
            db_host = self.config['DBHOST']
            db_port = int(self.config['DBPORT'])
            db_name = self.config['DBNAME']
        else:
            db_username = args.username or os.environ.get('DBUSER')
            db_password = args.password or os.environ.get('DBPASSWORD')
            db_host = args.host or os.environ.get('DBHOST')
            db_port = args.port or 5432
            db_name = args.dbname or os.environ.get('DBNAME')

        if db_host is None:
            connection_good = False
            while not connection_good:
                print("Let's setup your database connection...")
                db_host = prompt("Enter your database host: ")
                db_username = prompt("Enter your database username: ")
                db_password = prompt("Enter your database password: ", is_password=True)
                db_name = prompt("Enter the database name: ")
                db_port = prompt("Enter your database port (5432): ") or 5432
                db_port = int(db_port)
                print("Validating connection info...")
                try:
                    pgconn = psycopg2.connect(
                        f"host={db_host} dbname={db_name} user={db_username} password={db_password}",
                        connect_timeout=10
                    )
                    with pgconn.cursor() as cursor:
                        cursor.execute("SELECT version();")
                    connection_good = True
                except psycopg2.OperationalError as e:
                    print("Error: ", e)
                    continue
                breakpoint()
                self.config |= {
                    "DBUSER": db_username,
                    "DBPASSWORD": db_password,
                    "DBHOST": db_host,
                    "DBPORT": db_port,
                    "DBNAME": db_name
                }

            self.save_config()
        
        # PostgreSQL connection string format
        self.db_config = {
            'db_username': db_username,
            'db_password': db_password,
            'db_host': db_host,
            'db_port': db_port,
            'db_name': db_name
        }
        self.connection_string = f'postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}'

        self.engine = create_engine(self.connection_string)
        # Connect to your database
        self.pgconn = psycopg2.connect(
            f"host={db_host} dbname={db_name} user={db_username} password={db_password}"
        )
        self.thread = None

        api_key = self.config.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if api_key is None:
            api_key = prompt("Enter your Open AI API key: ")
            self.save_config("OPENAI_API_KEY", api_key)

        if 'model' not in self.config:
            print("Which model do you want to use?")
            print(f"1. {GPT_MODEL3}")
            print(f"2. {GPT_MODEL4}")
            choice = prompt("(1 or 2) >")
            if choice == "1":
                self.save_config("model", GPT_MODEL3)
            else:
                self.save_config("model", GPT_MODEL4)

        self.oaclient = OpenAI(api_key=api_key)
        self.get_or_create_assistant()

    def parse_args(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-help', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit')

        parser.add_argument('-h', '--host', type=str, required=False)
        parser.add_argument('-p', '--port', type=int, required=False)
        parser.add_argument('-U', '--username', type=str, required=False)
        parser.add_argument('-d', '--dbname', type=str, required=False)
        parser.add_argument('--password', type=str, required=False)

        return parser.parse_args()
    
    def save_config(self, key=None, value=None):
        if key and value:
            self.config[key] = value

        for k, v in self.config.items():
            if isinstance(v, datetime):
                self.config[k] = v.isoformat()

        with open(self.CONFIG_FILE, 'w') as f:
            f.write(json.dumps(self.config))

    def load_config(self):
        self.config = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.loads(f.read())

        for k, v in self.config.items():
            try:
                dt = datetime.fromisoformat(v)
                self.config[k] = dt
            except:
                pass

    def get_version(self):
        pyproject = toml.load("pyproject.toml")
        return pyproject["tool"]["poetry"]["version"]

    def get_or_create_assistant(self):
        # Create or retriveve our Assistant. We also upload the schema file
        # for RAG uses by the assistant.
        self.assistant = None
        if self.config["assistant_id"] is not None:
            try:
                self.assistant = self.oaclient.beta.assistants.retrieve(self.config["assistant_id"])
            except openai.NotFoundError:
                pass

        if self.assistant is None:
            # My attempt to use RAG to pre-populate the db schema never really worked
            # file = self.oaclient.files.create(
            #     file=open("schema.csv", "rb"),
            #     purpose='assistants'
            # )

            print("Creating your PSQL assistant")
            self.assistant = self.oaclient.beta.assistants.create(
                name=ASSISTANT_NAME,
                instructions="""
You are an assistant helping with data analysis and to query a postgres database. 
For any requst to print query results you can use the function `show_query_results()`.
""",
                tools=[{"type": "code_interpreter"},{"type": "retrieval"}] + self.FUNCTION_TOOLS,
                model=GPT_MODEL
            )   
            self.save_config("assistant_id", self.assistant.id)

    def chat_loop(self):
        session = PromptSession(history=FileHistory(os.path.expanduser('~/.myhistory')))

        if self.config["thread_id"] is not None:
            thread = self.oaclient.beta.threads.retrieve(self.config["thread_id"])
        else:
            thread = self.oaclient.beta.threads.create()
            self.save_config("thread_id", thread.id)

        self.thread = thread

        if self.config.get("last_run_id") is not None:
            try:
                self.oaclient.beta.threads.runs.cancel(thread_id=thread.id, run_id=self.config["last_run_id"])
            except openai.BadRequestError:
                pass
            
        self.last_message_created_at = self.config.get('last_messsage_time')
        self.table_list = get_table_list(self.engine)

        spinner = Halo(text='thinking', spinner='dots')
        self.spinner = spinner

        print("""
Welcome to GPTSQL, the chat interface to your Postgres database.
You can ask questions like:
    "help" (show some system commands)
    "show all the tables"
    "show me the first 10 rows of the users table"
    "show me the schema for the orders table"
        """)
        while True:
            try:
                cmd = session.prompt("\n> ")
                if cmd == "":
                    continue
                elif cmd == "history":
                    self.display_messages(show_all=True)
                    continue
                elif cmd == "help":
                    print("""
connection - show the database connection info
history - show the complete message history
new thread - start a new thread
exit
                          """)
                    continue
                elif cmd == "new thread":
                    if session.prompt("Do you want to start a new thread (y/n)? ") == "y":
                        thread = self.oaclient.beta.threads.create()
                        self.save_config("thread_id", thread.id)
                        self.thread = thread
                    continue
                elif cmd == "connection":
                    print(f"Host: {self.db_config['db_host']}, Database: {self.db_config['db_name']}, User: {self.db_config['db_username']}")
                    print(f"Model: {self.config['model']}")
                    print(f"Version: {self.get_version()}")
                    continue
                elif cmd == "exit":
                    return

                cmd = "This list of tables in the database:\n" + ",".join(self.table_list) + "\n----\n" + cmd
                spinner.start("thinking...")
                self.process_command(thread, cmd)
                spinner.stop()
                self.display_messages()
            except (KeyboardInterrupt, EOFError):
                spinner.stop()
                return

    def display_messages(self, show_all=False):
            messages = self.oaclient.beta.threads.messages.list(
                thread_id=self.thread.id
            )
            for msg in reversed(list(messages)):
                if msg.role == "user" and not show_all:
                    continue
                if self.last_message_created_at is None or (msg.created_at > self.last_message_created_at) or show_all:
                    self.last_message_created_at = msg.created_at
                    self.save_config("last_messsage_time", self.last_message_created_at)
                    if hasattr(msg.content[0], 'text'):
                        print(f"[{msg.role}] --> {msg.content[0].text.value}")
                    else:
                        print(f"[{msg.role}] --> {type(msg)}")

    def log(self, msg):
        self.spinner.start(msg);
    
    def process_command(self, thread, cmd: str):
        self.oaclient.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=cmd
        )
        runobj = self.oaclient.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id
        )
        self.save_config("last_run_id", runobj.id)
        last_step_count = 0
        while runobj.status not in ["completed", "expired", "cancelled", "failed"]:
            if runobj.status == "in_progress":
                # check for new steps
                run_steps = self.oaclient.beta.threads.runs.steps.list(
                    thread_id=thread.id,
                    run_id=runobj.id
                )
                run_steps = list(run_steps)
                #print(run_steps)
                #print("\n\n")
                if len(run_steps) > last_step_count:
                    for step in run_steps[last_step_count:]:
                        for step_detail in step.step_details:
                            if step_detail[0] == 'tool_calls':
                                for tool_call in step_detail[1]:
                                    if 'Function' in str(type(tool_call)):
                                        self.log(f"  --> {tool_call.function.name}()")
                                    elif 'Code' in str(type(tool_call)):
                                        self.log(f"  [code] {tool_call.code_interpreter.input}")
                last_step_count = len(run_steps)
            elif runobj.status == "requires_action":
                # Run any functions that the assistant has requested
                if runobj.required_action.type == "submit_tool_outputs":
                    tool_outputs = []
                    for tool_call in runobj.required_action.submit_tool_outputs.tool_calls:
                        res = str(call_my_function(self.engine, tool_call.function.name, json.loads(tool_call.function.arguments)))
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": res
                        })
                    self.oaclient.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=runobj.id,
                        tool_outputs=tool_outputs
                    )
                    self.spinner.text = "considering results..."
                else:
                    print("Unknown action: ", runobj.required_action.type)
            time.sleep(1)
            runobj = self.oaclient.beta.threads.runs.retrieve(thread_id=thread.id, run_id=runobj.id)


def main():
    gptsql = GPTSql()
    gptsql.chat_loop()

if __name__ == "__main__":
    main()

