CREATE TABLE samples (
    run_id uuid NOT NULL,
    at timestamptz NOT NULL,
    frequency_hz double precision NOT NULL,
    commanded_w double precision NOT NULL,
    actual_w double precision NOT NULL,
    soc double precision NOT NULL
);

CREATE INDEX samples_at_brin ON samples USING brin (at);

CREATE INDEX samples_run_id_at ON samples (run_id, at);
