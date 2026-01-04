"""
Model Retraining DAG
Orchestrates weekly model retraining pipeline.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
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
    "email_on_retry": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=6),
}

# DAG definition
dag = DAG(
    dag_id="model_retraining_weekly",
    default_args=default_args,
    description="Weekly model retraining pipeline",
    schedule_interval="0 0 * * 0",  # Sunday midnight
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["credit-risk", "ml", "retraining", "weekly"],
    max_active_runs=1,
)


def check_retraining_needed(**kwargs):
    """Check if model retraining is needed based on drift metrics."""
    # In production, this would check drift metrics from database
    # For now, always retrain
    ti = kwargs["ti"]

    # Simulated drift check
    drift_detected = True  # Would come from monitoring

    if drift_detected:
        ti.xcom_push(key="retrain_reason", value="drift_detected")
        return "prepare_training_data"
    else:
        return "skip_retraining"


# Task definitions

# Start marker
start = DummyOperator(
    task_id="start",
    dag=dag,
)

# Check if retraining is needed
check_drift = BranchPythonOperator(
    task_id="check_drift",
    python_callable=check_retraining_needed,
    provide_context=True,
    dag=dag,
)

# Skip branch
skip_retraining = DummyOperator(
    task_id="skip_retraining",
    dag=dag,
)

# Prepare training data
prepare_training_data = SparkSubmitOperator(
    task_id="prepare_training_data",
    application="/app/2_features/feature_pipeline.py",
    name="prepare_training_data_{{ ds }}",
    conf={
        "spark.executor.memory": "8g",
        "spark.executor.cores": "4",
        "spark.executor.instances": "8",
    },
    application_args=[
        "--mode", "training",
        "--output-path", "/data/training/{{ ds }}",
        "--lookback-months", "24",
    ],
    dag=dag,
)

# Data quality checks
run_data_quality = BashOperator(
    task_id="run_data_quality",
    bash_command="""
        python /app/2_features/data_quality.py \
            --input /data/training/{{ ds }} \
            --output /data/quality_report/{{ ds }}
    """,
    dag=dag,
)

# Train PD model
train_pd_model = BashOperator(
    task_id="train_pd_model",
    bash_command="""
        python /app/3_models/train_pd_model.py \
            --data-path /data/training/{{ ds }} \
            --output-path /models/staging/pd_model_{{ ds }} \
            --experiment-name pd_model_retraining
    """,
    dag=dag,
)

# Train LGD model
train_lgd_model = BashOperator(
    task_id="train_lgd_model",
    bash_command="""
        python /app/3_models/train_lgd_model.py \
            --data-path /data/training/{{ ds }} \
            --output-path /models/staging/lgd_model_{{ ds }} \
            --experiment-name lgd_model_retraining
    """,
    dag=dag,
)

# Validate models
validate_pd_model = BashOperator(
    task_id="validate_pd_model",
    bash_command="""
        python /app/3_models/validate_models.py \
            --model-path /models/staging/pd_model_{{ ds }} \
            --model-type pd \
            --validation-data /data/training/{{ ds }}/validation
    """,
    dag=dag,
)

validate_lgd_model = BashOperator(
    task_id="validate_lgd_model",
    bash_command="""
        python /app/3_models/validate_models.py \
            --model-path /models/staging/lgd_model_{{ ds }} \
            --model-type lgd \
            --validation-data /data/training/{{ ds }}/validation
    """,
    dag=dag,
)

# Champion/Challenger comparison
def compare_models(**kwargs):
    """Compare new models with production models."""
    ti = kwargs["ti"]

    # In production, would compare metrics
    # For now, assume new model is better
    new_model_better = True

    if new_model_better:
        ti.xcom_push(key="deploy_decision", value="deploy")
        return "register_models"
    else:
        return "keep_existing"


compare_with_production = BranchPythonOperator(
    task_id="compare_with_production",
    python_callable=compare_models,
    provide_context=True,
    dag=dag,
)

# Keep existing models
keep_existing = DummyOperator(
    task_id="keep_existing",
    dag=dag,
)

# Register new models
register_models = BashOperator(
    task_id="register_models",
    bash_command="""
        python /app/3_models/register_models.py \
            --pd-model /models/staging/pd_model_{{ ds }} \
            --lgd-model /models/staging/lgd_model_{{ ds }} \
            --version {{ ds }}
    """,
    dag=dag,
)

# Deploy to endpoints
deploy_pd_model = BashOperator(
    task_id="deploy_pd_model",
    bash_command="""
        python /app/9_deployment/deploy_model.py \
            --model-name pd_model \
            --model-path /models/staging/pd_model_{{ ds }} \
            --endpoint pd-model
    """,
    dag=dag,
)

deploy_lgd_model = BashOperator(
    task_id="deploy_lgd_model",
    bash_command="""
        python /app/9_deployment/deploy_model.py \
            --model-name lgd_model \
            --model-path /models/staging/lgd_model_{{ ds }} \
            --endpoint lgd-model
    """,
    dag=dag,
)

# Update risk engine
update_risk_engine = BashOperator(
    task_id="update_risk_engine",
    bash_command="""
        python /app/9_deployment/update_risk_engine.py \
            --pd-version {{ ds }} \
            --lgd-version {{ ds }}
    """,
    dag=dag,
)

# Run smoke tests
smoke_tests = BashOperator(
    task_id="smoke_tests",
    bash_command="""
        python /app/tests/smoke_tests.py \
            --endpoint https://pd-model.{{ var.value.cml_domain }} \
            --endpoint https://lgd-model.{{ var.value.cml_domain }}
    """,
    dag=dag,
)

# Send notification
send_retraining_notification = PythonOperator(
    task_id="send_retraining_notification",
    python_callable=lambda **kwargs: print(f"Model retraining completed for {kwargs['ds']}"),
    provide_context=True,
    trigger_rule=TriggerRule.ONE_SUCCESS,
    dag=dag,
)

# Archive old models
archive_old_models = BashOperator(
    task_id="archive_old_models",
    bash_command="""
        python /app/9_deployment/archive_models.py \
            --keep-versions 5
    """,
    trigger_rule=TriggerRule.ONE_SUCCESS,
    dag=dag,
)

# End marker
end = DummyOperator(
    task_id="end",
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)


# Task dependencies
start >> check_drift

check_drift >> skip_retraining >> end
check_drift >> prepare_training_data >> run_data_quality

run_data_quality >> [train_pd_model, train_lgd_model]

train_pd_model >> validate_pd_model
train_lgd_model >> validate_lgd_model

[validate_pd_model, validate_lgd_model] >> compare_with_production

compare_with_production >> keep_existing >> send_retraining_notification
compare_with_production >> register_models

register_models >> [deploy_pd_model, deploy_lgd_model]

[deploy_pd_model, deploy_lgd_model] >> update_risk_engine >> smoke_tests

smoke_tests >> send_retraining_notification >> archive_old_models >> end
