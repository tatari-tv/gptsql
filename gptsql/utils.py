import os
import csv

def download_companies():
    query = """
    SELECT DISTINCT ON (companies.name)
           companies.name || '-' || cast(companies.id as VARCHAR) as name, 
           companies.id,
           product_description, 
           landing_pages.landing_page_url
    FROM companies 
    INNER JOIN landing_pages 
    ON companies.id = landing_pages.company_id
    WHERE industry IS NOT NULL
    ORDER BY companies.name, LENGTH(landing_pages.landing_page_url)
    LIMIT 2;
    """

    df = pd.read_sql_query(query, engine)
    print(df)
    return df

def download_campaigns(company_id):
    pass

def enrich_companies(df):
    # Takes our list of companies+landing pages and as ChatGPT to summarize the
    # company for us. 
    for row in df.itertuples():
        # This code is for v1 of the openai package: pypi.org/project/openai
        print(row)
        print("Asking ChatGPT for context")
        response = client.chat.completions.create(
          model=GPT_MODEL,
          messages=[
            {
              "role": "user",
              "content": f"Browse this website and generate a description of the company and its products: {row.landing_page_url}."
            }
          ],
          temperature=1,
          max_tokens=256,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0
        )
        print(response.choices[0].message.content)

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


