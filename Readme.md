## Objective

This project builds a simple, end-to-end machine learning system that predicts how strong a chemical compound’s effect might be in a lab test, using only a few basic traits of the compound. The dataset comes from a public bioactivity resource called **ChEMBL**.

Each compound in the dataset is described by four features, which the model uses to make its prediction:

| Column Name     | Description                                 | Why It's Useful                                                               |
|-----------------|---------------------------------------------|-------------------------------------------------------------------------------|
| `mw_freebase`   | Molecular Weight – how heavy the molecule is | Heavier or lighter compounds behave differently in chemical reactions        |
| `alogp`         | LogP – whether the compound prefers oily or watery environments | Affects how the compound travels in the body or interacts with cells         |
| `hba`           | Hydrogen Bond Acceptors – how many "hands" the molecule has to receive hydrogen bonds | Influences how sticky or interactive the compound is                         |
| `hbd`           | Hydrogen Bond Donors – how many "hands" it has to give hydrogen bonds | Affects how well it binds or interacts with other molecules                 |

Using just these four inputs, the model predicts a fifth value:

- **`standard_value`**: A numerical measure of the compound's activity in a biological test. Lower values generally mean stronger activity.


## High-Level Architecture

- **Data Storage**  
  All compound data, are stored in a PostgreSQL database for reliable and centralized access.

- **Pipeline Orchestration**  
  Mage and Prefect coordinate and manage the data workflows, including data loading, model training, and batch or streaming prediction jobs.

- **Experiment Tracking and Logging**  
  MLflow is used to track model versions, log training metrics, and manage model artifacts, ensuring reproducibility and auditability.

- **Data Quality and Model Monitoring**  
  Evidently monitors input data quality and model performance over time, detecting drifts or anomalies in predictions.

- **Metrics Collection and Visualization**  
  Prometheus collects runtime metrics, including prediction statistics , which are visualized in Grafana dashboards for real-time monitoring.

- **Model Serving**  
  The trained model is served via MLflow endpoints, enabling real-time predictions through API calls.

- **Synthetic Data Generation and Streaming**  
  Synthetic Data Vault (SDV) generates realistic synthetic compound data which is pushed into Kafka streams.

- **Data Consumption and Prediction**  
  A Kafka consumer listens to these streams, processes incoming data by calling the MLflow model serving API, and obtains predictions.

- **Metrics Export and Monitoring**  
  Prediction results and related metrics are pushed to a Prometheus Pushgateway, allowing Prometheus to scrape them and Grafana to display updated dashboards.

- **Dockerized and Local Setup**  
  The entire system is containerized using Docker, enabling easy local development, testing, and deployment without external dependencies.


This architecture supports an end-to-end automated, scalable, and monitored machine learning pipeline for chemical compound activity prediction.



