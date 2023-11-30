# gptsql

An LLM wrapper around your database connection. Think of it as a "smart" version of the psql cli.

Example:

```
    python -m gptsql
    > show me the schemas
    thinking...
    Running select query: SELECT schema_name FROM information_schema.schemata;
    processing the function response...
    Here are the schemas in your database:

    1. pg_catalog
    2. information_schema
    3. analytics
    4. public
    5. aws_commons
    6. bi_staging
    7. rds_tools

    > show me tables that start with "streaming_"
    thinking...
    Running select query: SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'streaming_%%';
    processing the function response...
    Here are the tables that start with "streaming_":

    1. streaming_bookings
    2. streaming_campaign_vast_tags
    3. streaming_campaigns
    4. streaming_cpx_predictions
    5. streaming_hourly_counts
    6. streaming_hourly_lift
    7. streaming_hourly_lift_dbx
    8. streaming_hourly_lift_dbx_staging
    9. streaming_impressions_log_entries
    10. streaming_impressions_logs
    11. streaming_network_extreme_reach_inventory_id_map
    12. streaming_networks
    13. streaming_provider_company_map
    14. streaming_providers
    15. streaming_reconciliations
    16. streaming_spends
    17. streaming_spends_dbx
    18. streaming_spends_dbx_staging    
```

## Getting started

Setup your `.env` file from `env.example`. Then source the values into your environment.

Run the CLI with:

    python -m gptsql
    