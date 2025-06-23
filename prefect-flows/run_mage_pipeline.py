from prefect import flow, task
import subprocess

@task
def run_mage_pipeline(project: str, pipeline: str):
    """
    Executes the Mage pipeline using subprocess inside the orchestration container,
    calling Mage via Docker network.
    """
    cmd = f"mage start {pipeline} --project {project} --non-interactive"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error running Mage pipeline:")
        print(result.stderr)
        raise RuntimeError("Pipeline execution failed")

    print(result.stdout)

@flow(name="Loop over Mage pipeline")
def loop_pipeline(project: str, pipeline: str, runs: int = 10):
    for i in range(runs):
        print(f"Starting run {i + 1}")
        run_mage_pipeline(project, pipeline)

if __name__ == "__main__":
    loop_pipeline(project="default", pipeline="example_pipeline", runs=10)
