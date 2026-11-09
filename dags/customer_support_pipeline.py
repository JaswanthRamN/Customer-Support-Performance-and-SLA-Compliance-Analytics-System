"""Apache Airflow DAG for the customer-support analytics data pipeline."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Airflow may copy this DAG outside the repository. AIRFLOW_PROJECT_ROOT makes
# project modules explicit; the repository root is the safe local default.
PROJECT_ROOT = Path(os.getenv("AIRFLOW_PROJECT_ROOT", Path(__file__).resolve().parents[1])).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from airflow.decorators import dag, task

from orchestration.airflow_tasks import (check_data_availability, clean_source,
                                         load_postgres_idempotent, post_load_checks,
                                         validate_load_inputs, validate_source)


DEFAULT_ARGS = {
    "owner": "data-analytics",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


@dag(
    dag_id="customer_support_analytics_pipeline",
    description="Validate, clean, transactionally load, and reconcile synthetic support data",
    schedule=os.getenv("AIRFLOW_SUPPORT_SCHEDULE", "0 6 * * *"),
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    default_args=DEFAULT_ARGS,
    tags=["customer-support", "postgresql", "portfolio"],
)
def customer_support_analytics_pipeline():
    @task(task_id="check_data_availability", execution_timeout=timedelta(minutes=5))
    def availability():
        return check_data_availability()

    @task(task_id="validate_source_data", execution_timeout=timedelta(minutes=15))
    def validate():
        return validate_source()

    @task(task_id="clean_and_quarantine", execution_timeout=timedelta(minutes=30))
    def clean():
        return clean_source()

    @task(task_id="validate_load_inputs", execution_timeout=timedelta(minutes=15))
    def load_preflight():
        return validate_load_inputs()

    @task(task_id="load_postgresql_idempotently", execution_timeout=timedelta(minutes=45), retries=1)
    def load():
        return load_postgres_idempotent()

    @task(task_id="post_load_reconciliation", execution_timeout=timedelta(minutes=20))
    def reconcile():
        return post_load_checks()

    availability() >> validate() >> clean() >> load_preflight() >> load() >> reconcile()


customer_support_pipeline = customer_support_analytics_pipeline()
