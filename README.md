# queuectl-CLI-Background-Job-Queue-Python-

A minimal, production-minded CLI job queue in Python with:


- enqueue / list / status CLI commands
- worker processes with graceful shutdown
- retries with exponential backoff
- Dead Letter Queue (DLQ)
- SQLite persistence
- simple configuration via `config.json`


---


## Quick start


Requirements: Python 3.10+, pip


```bash
# clone or copy files into a directory
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


# enqueue example jobs
python queuectl.py enqueue '{"id":"job1","command":"echo Hello","max_retries":3}'
python queuectl.py enqueue '{"id":"job2","command":"bash -c \"exit 1\"","max_retries":2}'


# start 2 workers
python queuectl.py worker start --count 2


# status / list
python queuectl.py status
python queuectl.py list --state pending


# DLQ
python queuectl.py dlq list
python queuectl.py dlq retry job2


# run smoke test
bash tests/smoke_test.sh
