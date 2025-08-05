from datetime import datetime, timedelta
import re
from airflow import DAG
from airflow.operators.python import PythonOperator

from airflow_seatunnel_provider.operators.seatunnel_operator import SeaTunnelOperator
from airflow_seatunnel_provider.sensors.seatunnel_sensor import SeaTunnelJobSensor

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define a function to extract job_id from command output
def extract_job_id(**kwargs):
    # Get SeaTunnel Task Output from XCom
    seatunnel_output = kwargs['ti'].xcom_pull(task_ids='start_seatunnel_job')

    # Use regular expressions to find job_id, this pattern needs to be adjusted according to the actual output format
    # Example regular expressions, assuming job_id appears in a format like "Job id:" or "Job ID:" or similar
    # Or it could be in the format "Job xxx successfully started"
    job_id_pattern = r'[Jj]ob\s+(?:[Ii][Dd]:\s*)?([a-zA-Z0-9-]+)'
    
    match = re.search(job_id_pattern, seatunnel_output)
    if match:
        job_id = match.group(1)
        print(f"Extracted job ID: {job_id}")
        return job_id
    else:
        # If unable to extract job_id, return a default error message
        error_msg = "Could not extract job ID from SeaTunnel output"
        print(error_msg)
        raise ValueError(error_msg)

with DAG(
    'seatunnel_sensor_example',
    default_args=default_args,
    description='Example DAG demonstrating the SeaTunnelJobSensor',
    schedule=None,
    start_date=datetime.now() - timedelta(days=1),
    tags=['example', 'seatunnel', 'sensor'],
) as dag:
    
    # First, we start a SeaTunnel job
    # Note: This example works with Zeta engine only, as it exposes a REST API
    start_job = SeaTunnelOperator(
        task_id='start_seatunnel_job',
        config_content="""
env {
  parallelism = 1
  job.mode = "BATCH"
}

source {
  # This is a example source plugin **only for test and demonstrate the feature source plugin**
  FakeSource {
    plugin_output = "fake"
    parallelism = 1
    schema = {
      fields {
        name = "string"
        age = "int"
      }
    }
  }
}

transform {
}

sink {
  console {
    plugin_input="fake"
  }
}
        """,
        engine='zeta',
        seatunnel_conn_id='seatunnel_default',
    )
    
    # Add task to extract job_id
    extract_id = PythonOperator(
        task_id='extract_job_id',
        python_callable=extract_job_id,
    )
    
    # Monitor using the extracted job_id
    wait_for_job = SeaTunnelJobSensor(
        task_id='wait_for_job_completion',
        job_id="{{ task_instance.xcom_pull(task_ids='extract_job_id') }}",  # 使用提取后的job_id
        target_states=['FINISHED'],
        seatunnel_conn_id='seatunnel_default',
        poke_interval=10,  # Check every 10 seconds
        timeout=600,  # Timeout after 10 minutes
    )
    
    # Define the task dependency
    start_job >> extract_id >> wait_for_job