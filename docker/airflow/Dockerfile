ARG AIRFLOW_IMAGE_NAME=apache/airflow:2.10.5-python3.12
FROM ${AIRFLOW_IMAGE_NAME}

ARG AIRFLOW_VERSION=2.10.5
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /tmp/requirements-airflow.txt
