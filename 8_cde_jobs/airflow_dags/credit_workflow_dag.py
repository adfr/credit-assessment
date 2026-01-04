"""
Credit Workflow DAG
Orchestrates the daily credit risk pipeline.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.trigger_rule import TriggerRule


# Default arguments
default_args = {
    "owner": "credit-risk-team",
    "depends_on_past": False,
    "email": ["credit-risk-alerts@company.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# DAG definition
dag = DAG(
    dag_id="credit_workflow_daily",
    default_args=default_args,
    description="Daily credit risk workflow pipeline",
    schedule_interval="0 2 * * *",  # 2 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["credit-risk", "ml", "daily"],
    max_active_runs=1,
)


# Task definitions

# Start marker
start = DummyOperator(
    task_id="start",
    dag=dag,
)

# Data extraction
extract_new_applications = BashOperator(
    task_id="extract_new_applications",
    bash_command="""
        python /app/1_data/extract_applications.py \
            --date {{ ds }} \
            --output /data/staging/applications/{{ ds }}
    """,
    dag=dag,
)

extract_payment_updates = BashOperator(
    task_id="extract_payment_updates",
    bash_command="""
        python /app/1_data/extract_payments.py \
            --date {{ ds }} \
            --output /data/staging/payments/{{ ds }}
    """,
    dag=dag,
)

extract_bureau_updates = BashOperator(
    task_id="extract_bureau_updates",
    bash_command="""
        python /app/1_data/extract_bureau.py \
            --date {{ ds }} \
            --output /data/staging/bureau/{{ ds }}
    """,
    dag=dag,
)

# Data validation
validate_data = PythonOperator(
    task_id="validate_data",
    python_callable=lambda **kwargs: print(f"Validating data for {kwargs['ds']}"),
    provide_context=True,
    dag=dag,
)

# Feature engineering
feature_engineering = SparkSubmitOperator(
    task_id="feature_engineering",
    application="/app/8_cde_jobs/spark_jobs/feature_engineering.py",
    name="feature_engineering_{{ ds }}",
    conf={
        "spark.executor.memory": "4g",
        "spark.executor.cores": "2",
        "spark.executor.instances": "4",
        "spark.sql.shuffle.partitions": "200",
    },
    application_args=[
        "--input-path", "/data/processed",
        "--output-path", "/data/features/{{ ds }}",
        "--date", "{{ ds }}",
    ],
    dag=dag,
)

# Batch scoring
batch_scoring = SparkSubmitOperator(
    task_id="batch_scoring",
    application="/app/8_cde_jobs/spark_jobs/batch_scoring.py",
    name="batch_scoring_{{ ds }}",
    conf={
        "spark.executor.memory": "4g",
        "spark.executor.cores": "2",
        "spark.executor.instances": "4",
    },
    application_args=[
        "--features-path", "/data/features/{{ ds }}",
        "--pd-model-path", "/models/pd_model.pkl",
        "--lgd-model-path", "/models/lgd_model.pkl",
        "--output-path", "/data/scores/{{ ds }}",
        "--date", "{{ ds }}",
    ],
    dag=dag,
)

# Model monitoring
run_drift_detection = PythonOperator(
    task_id="run_drift_detection",
    python_callable=lambda **kwargs: print(f"Running drift detection for {kwargs['ds']}"),
    provide_context=True,
    dag=dag,
)

# Decision engine
run_decision_engine = BashOperator(
    task_id="run_decision_engine",
    bash_command="""
        python /app/5_backend/decision_engine.py \
            --scores-path /data/scores/{{ ds }} \
            --output /data/decisions/{{ ds }}
    """,
    dag=dag,
)

# Update database
update_database = BashOperator(
    task_id="update_database",
    bash_command="""
        python /app/1_data/load_to_iceberg.py \
            --scores-path /data/scores/{{ ds }} \
            --decisions-path /data/decisions/{{ ds }}
    """,
    dag=dag,
)

# Generate reports
generate_reports = BashOperator(
    task_id="generate_reports",
    bash_command="""
        python /app/7_monitoring/generate_daily_report.py \
            --date {{ ds }} \
            --output /reports/daily/{{ ds }}
    """,
    dag=dag,
)

# Send notifications
send_notifications = PythonOperator(
    task_id="send_notifications",
    python_callable=lambda **kwargs: print(f"Sending notifications for {kwargs['ds']}"),
    provide_context=True,
    dag=dag,
)

# Cleanup staging
cleanup_staging = BashOperator(
    task_id="cleanup_staging",
    bash_command="""
        hdfs dfs -rm -r -f /data/staging/*/{{ ds }}
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# End marker
end = DummyOperator(
    task_id="end",
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)


# Task dependencies
start >> [extract_new_applications, extract_payment_updates, extract_bureau_updates]

[extract_new_applications, extract_payment_updates, extract_bureau_updates] >> validate_data

validate_data >> feature_engineering >> batch_scoring

batch_scoring >> [run_drift_detection, run_decision_engine]

run_decision_engine >> update_database >> generate_reports >> send_notifications

[run_drift_detection, send_notifications] >> cleanup_staging >> end
