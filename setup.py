from setuptools import setup, find_packages

setup(
    packages=find_packages(include=['airflow_seatunnel_provider', 'airflow_seatunnel_provider.*']),
)
