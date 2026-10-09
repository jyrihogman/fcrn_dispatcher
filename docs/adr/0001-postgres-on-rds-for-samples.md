# Plain Postgres on RDS stores the samples

Every sample (timestamp, frequency, commanded power, actual power, SoC) goes to one `samples` table in plain PostgreSQL on Amazon RDS. FCR-N samples must stay queryable for months, and one battery writes only 10 rows per second (about 864k rows per day). Postgres handles that with a BRIN index and `COPY` batches. RDS gives backups, point-in-time recovery and Multi-AZ with no extra work.

## Considered Options

- **TimescaleDB.** RDS cannot run it. Its compression and continuous aggregates are under the Timescale License (TSL), and the TSL stops AWS from hosting them. Using Timescale means Tiger Cloud or self-hosting. It is the next step at fleet scale, because the `samples` table can become a hypertable.
- **InfluxDB 3 Core on Amazon Timestream for InfluxDB.** It fits the data model well. But Core is single-node, has no compaction, and limits a query to about 72 hours by default. That is weak for long history.
- **InfluxDB 3 Enterprise or 2.7 on Timestream.** They keep long history, but Enterprise costs money and 2.7 is the older generation. Neither gives SQL joins with other business data such as bids and assets.
