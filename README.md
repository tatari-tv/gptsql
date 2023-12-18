# gptsql

An LLM-powered chat interface to your database. This tool understands Postgres syntax and can easily translate English queries into proper SQL queries. Because of the wide training of the LLM model it can also infer relevant information about the structure and meaning of your tables and data. Uses an [Open AI](https://openai.com) model via the [Assistant API](https://platform.openai.com/docs/assistants/overview).

There are lots of tools around to enable "chat with your data" (mostly based on the [RAG](https://research.ibm.com/blog/retrieval-augmented-generation-RAG) architecture), but this is actually the quickest way to enable LLM chat with your data - no preparation is needed.


Here's a quick demo showing natural language queries about the [IMDB](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/2QYZBT) movie database. You can even see the Assistant encounter SQL errors and then correct itself:



https://github.com/tatari-tv/gptsql/assets/80947/7e946bdd-1ed9-4a03-9dc1-aca8d3a44926




## Installation

You will need:

1. credentials for your database
2. an OpenAI [API Key](https://platform.openai.com/account/api-keys) from your OpenAI account.

then

```
pip install gptsql
```

or download the source. 

Run the CLI with:

    gptsql

or use `python -m gptsql` to run from source.

## What can it do?

Then Open AI model understands most Postgres syntax, so it can generate both generic SQL commands as well as very Postgres-specific ones like querying system settings.

The LLM is also good at analyzing tables, understanding what they are likely used for, and inferring relationships between tables. It is quite good at writing JOINs between tables without explicit instruction.

It can write queries to group and summarize results.

By virtue of the Assistant API, it can also write multi-step queries and combine the results of queries together. It is also maintaining a history of the chat, so you can easily ask follow up questions like "now summarize by month" that refer back to prior queries.

At the moment the tool limits to only SELECT queries and does not allow mutations (but see the [SAFETY](#safety) section for details).

## Chat examples

```
% gptsql

Welcome to GPTSQL, the chat interface to your Postgres database.
        
> show me the available schemas
⠋ thinking...  Running select query: SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;
[assistant] --> The available schemas in the database are:

1. information_schema
2. pg_catalog
3. pg_toast
4. public
```

Show tables matching a string:
```
> show all tables that have "sales" in the name
⠴ thinking...  Running select query: SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%%sales%%' ORDER BY table_name;
[assistant] --> The tables with 'sales' in the name are as follows:

- salesorderdetail
- salesorderheader
- salesorderheadersalesreason
- salesperson
- salespersonquotahistory
- salesreason
- salestaxrate
- salesterritory
- salesterritoryhistory
- vsalesperson
- vsalespersonsalesbyfiscalyears
- vsalespersonsalesbyfiscalyearsdata
```
List columns for a table:
```
> show the columns of the salesorderheader table
⠹ thinking...  Running select query: SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'salesorderheader' ORDER BY ordinal_position;
[assistant] --> The columns of the `salesorderheader` table along with their data types are as follows:

- `salesorderid` (integer)
- `revisionnumber` (smallint)
- `orderdate` (timestamp without time zone)
- `duedate` (timestamp without time zone)
- `shipdate` (timestamp without time zone)
- `status` (smallint)
- `subtotal` (numeric)
- `taxamt` (numeric)
- `freight` (numeric)
- `totaldue` (numeric)
- `comment` (character varying)
- `rowguid` (uuid)
- `modifieddate` (timestamp without time zone)
```
Run a calculation against a table:
```
> calculate the sum of the totaldue column by month
⠇ thinking...  Running select query: SELECT DATE_TRUNC('month', orderdate) AS month, SUM(totaldue) AS total_sales FROM sales.salesorderheader GROUP BY month ORDER BY month;
[assistant] --> Here are the sums of the `totaldue` column by month:

Month               Total Sales
-------------------------------------
2011-05-01          567,020.95
2011-06-01          507,096.47
2011-07-01        2,292,182.88
2011-08-01        2,800,576.17
2011-09-01          554,791.61
2014-02-01        1,478,213.29
2014-03-01        8,097,036.31
2014-04-01        1,985,886.15
2014-05-01        6,006,183.21
2014-06-01           54,151.48
These figures represent the total sales for each month.
```
Query data from a table:
```
> show me the names of the stores
⠹ thinking...  Running select query: SELECT name FROM sales.store;
> print the results
⠧ thinking...LAST QUERY RESULTS:
⠇ thinking...                                    name
0                   Next-Door Bike Store
1         Professional Sales and Service
2                         Riders Company
3                     The Bike Mechanics
4                      Nationwide Supply
5                  Area Bike Accessories
6           Bicycle Accessories and Kits
7                  Clamps & Brackets Co.
8             Valley Bicycle Specialists
9                      New Bikes Company
10   Vinyl and Plastic Goods Corporation
11                 Top of the Line Bikes
12                    Fun Toys and Bikes
13                          Great Bikes 
14         Metropolitan Sales and Rental
15                     Irregulars Outlet
16                      Valley Toy Store
17             Worthwhile Activity Store
```
Explain your data:
```
> what is the purpose of the salespersonquotahistory table?
[assistant] --> The purpose of the `salespersonquotahistory` table is typically to maintain a record of the sales quota assigned to each salesperson over time. The table likely includes columns for:

- Identifying the salesperson, which may reference a `businessentityid` or similar key that links to another table containing salesperson details.
- The sales quota amount, which indicates the target sales figure the salesperson is expected to meet for a given period.
- Date fields, which may specify the period or specific dates for the quota.
- Any changes or historical adjustments made to the quota over time.

It serves as a historical log that can be used for performance tracking, compensation calculation, sales management, and analysis. The exact columns and usage may vary depending on the specific design of the database. If you have access to the table structure, you can review the columns to understand more about the data it holds. Would you like me to retrieve the columns of the `salespersonquotahistory` table to provide more detailed information?
```
Easily run custom Postgres SQL:
```
> show the top 10 tables by size on disk
⠸ thinking...  Running select query: SELECT table_schema || '.' || table_name AS full_table_name,
pg_total_relation_size('"' || table_schema || '"."' || table_name || '"') AS size_on_disk
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY size_on_disk DESC
LIMIT 10;
[assistant] --> The top 10 tables by size on disk are as follows:

1. `sales.salesorderdetail`: 15,073,280 bytes
2. `person.person`: 14,688,256 bytes
3. `production.transactionhistory`: 11,304,960 bytes
4. `production.workorderrouting`: 9,355,264 bytes
5. `production.transactionhistoryarchive`: 8,896,512 bytes
6. `production.workorder`: 7,823,360 bytes
7. `sales.salesorderheader`: 6,676,480 bytes
8. `production.productphoto`: 4,431,872 bytes
9. `person.address`: 3,522,560 bytes
10. `person.password`: 2,842,624 bytes

These sizes are in bytes, and the tables are listed in decreasing order of their size on disk.
```

### Configuration

You can configure the database connection either using `psql` style command line arguments
or the env vars `DBHOST`, `DBNAME`, `DBUSER`, `DBPASSWORD`, `DBPORT`.

Else when you first run the program it will prompt you for the connection credentials as
well as your OpenAI API key.

After first setup all the configuration information is stored in `~/.gptsql`. Delete that
file if you want to start over.
        
## How it works

`gptsql` uses the OpenAI [Assistants API](https://platform.openai.com/docs/assistants/overview) to create an intelligent assistant to work with your database.
The key to accessing the database is providing a function _tool_ to the assistant. Amazingly
only a single function is required:

```json
        {
            "type": "function",
            "function": {
                "name": "run_sql_command",
                "description": "Execute any SQL command against the Postgres datbase",
            }
        }
```

When requested the LLM automatically generates the right SQL and calls this function to execute it. The query results are then returned to the Assistant where it can decide to print or summarize the results. 

If the LLM needs to know about your tables it will just execute SQL commands against the
`information schema` to extract it. 

Since table reference is so common, we help the assistant by pre-emptively injecting the table
list into the LLM prompt.

Because of the LLM context limits, you won't always be able to see all the rows returned from a query.
So we provide a second function tool, `show_query_results` which can print up to 200 rows resulting from
the last query. Sometimes the assistant is smart enough to call this function by itself, but other times
you may have to request "print results" to see all the result rows.

### Command Reference

There are a few system commands supported for meta operations: 

`help` - show system commands

`connection` - show the current db connection details, and the active LLM model

`history` - print the assistant's message history

`new thread` - start a new thread (clearing out any existing conversation context)

`exit` or ctrl-d to exit

If you want to change the LLM model you can edit the assistant via the OpenAI web portal.

## SAFETY

**Please do not run this against a production database!** And **make sure you have a backup** of your data. That said, the query function has a simple protector which will refuse to run any query that doesn't start with `SELECT`. Note that this is not foolproof. It is very likely that the LLM can construct a destructive query which will get around this simple check, if you ask it properly. So don't rely on this for perfect safety. I strongly recommend running with a `read-only` db connection just in case.

Also please note that this tool **sends your data to OpenAI**. Query results are sent back to Assistant API for processing. Please make your own decision on whether you are OK with this or not.

## Limitations

The biggest limitation is that the LLM is **slooooowwww**. In my testing it can easily take 20-30 seconds of "thinking" before the LLM responds. One reason is that the LLM runs once when you issue your question, and then it runs again to process any results returned from the functions. 

It is also the case the the Assistants API will run multiple "steps" to process your question, even though we don't get a lot of feedback when this is happening.

One other thing: the tool is **expensive** :). I ran up a bill of about $100 just doing development. It is recommnded to stick with the **GPT3** model if you want to keep your costs down.
