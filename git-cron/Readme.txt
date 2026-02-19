# Git Repository Monitor (monitor_repos.py)

This script, `monitor_repos.py`, is designed to be executed as a cron job to continuously monitor a set of specified Git repositories.

## Purpose

The primary function of this script is twofold:
1.  **Monitor Repositories:** It keeps track of a pre-defined list of Git repositories, likely checking for updates, new commits, or other relevant changes.
2.  **Submit to GMT for Benchmarking:** Upon detecting certain conditions (e.g., changes in a specific repository or a new repository being added to the monitored list), it facilitates the submission of *another* designated repository to the GMT (Gemini Metrics Tool) system for benchmarking purposes. This allows for automated performance or quality analysis of a project.

## Setup

To run this script, it is highly recommended to set up a Python virtual environment to manage dependencies.

1.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    ```
2.  **Activate the Virtual Environment:**
    ```bash
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    Install the necessary Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Usage (Cron Job)

Once set up, this script can be scheduled to run periodically using a cron job. An example cron entry might look like this (adjust the path to `monitor_repos.py` and the frequency as needed):

```cron
0 */4 * * * /path/to/your/git-cron/venv/bin/python /path/to/your/git-cron/monitor_repos.py >> /var/log/monitor_repos.log 2>&1
```
This example would run the script every 4 hours.

## Configuration

The script's behavior is configured via `config.json` and its state is managed by `repo_state.json`. Please refer to these files for detailed configuration options and how to manage the monitored repositories and benchmarking triggers.

Each entry in `repos` watches one source repository (`repo_to_watch`/`branch_to_watch`) and contains a `runs` list. Every object in `runs` defines one GMT submission with these keys: `repo_to_run`, `machine_id`, `email`, `branch_to_run`, `filename`, and `variables`.

In a run's `variables` section you can use the magic keyword `__GIT_HASH__`; it is replaced with the latest hash of the watched branch commit.
