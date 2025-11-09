import sqlite3, time, subprocess, uuid, signal
from datetime import datetime, timedelta
from db import get_conn, ISO


STOP = False




def handle_sig(signum, frame):
global STOP
STOP = True




signal.signal(signal.SIGINT, handle_sig)
signal.signal(signal.SIGTERM, handle_sig)




def claim_job(conn, worker_id, now_iso):
cur = conn.cursor()
cur.execute("""
UPDATE jobs SET state='processing', worker_id=?, updated_at=?
WHERE id = (
SELECT id FROM jobs
WHERE state='pending' AND (next_run IS NULL OR next_run <= ?)
ORDER BY created_at LIMIT 1
)
""", (worker_id, now_iso, now_iso))
return cur.rowcount > 0




def get_processing_job(conn, worker_id):
cur = conn.cursor()
cur.execute("SELECT * FROM jobs WHERE state='processing' AND worker_id=? LIMIT 1", (worker_id,))
return cur.fetchone()




def process_job_row(row, conn, base_backoff=2):
job_id = row["id"]
cmd = row["command"]
attempts = row["attempts"] or 0
max_retries = row["max_retries"]
print(f"[{job_id}] running: {cmd} (attempts={attempts})")
proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
now = ISO()
if proc.returncode == 0:
conn.execute("UPDATE jobs SET state='completed', updated_at=?, output=? WHERE id=?",
(now, proc.stdout, job_id))
print(f"[{job_id}] completed")
else:
attempts += 1
last_err = proc.stderr or proc.stdout or f"exit:{proc.returncode}"
if attempts >= max_retries:
conn.execute("UPDATE jobs SET state='dead', attempts=?, last_error=?, updated_at=? WHERE id=?",
(attempts, last_err, now, job_id))
print(f"[{job_id}] moved to DLQ (dead) after {attempts}")
else:
delay = base_backoff ** attempts
next_run = (datetime.utcnow() + timedelta(seconds=delay)).isoformat() + "Z"
conn.execute("""UPDATE jobs SET state='pending', attempts=?, next_run=?, last_error=?, updated_at=?, worker_id=NULL
WHERE id=?""",
(attempts, next_run, last_err, now, job_id))
print(f"[{job_id}] failed — will retry at {next_run} (attempt {attempts})")




def worker_loop(worker_id, base_backoff=2):
conn = get_conn()
try:
while not STOP:
now = datetime.utcnow().isoformat() + "Z"
claimed = claim_job(conn, worker_id, now)
if not claimed:
time.sleep(1)
continue
row = get_processing_job(conn, worker_id)
if row:
process_job_row(row, conn, base_backoff)
finally:
conn.close()
print(f"worker {worker_id} shutting down")
