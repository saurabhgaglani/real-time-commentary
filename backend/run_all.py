import os
import sys
import signal
import subprocess
from typing import List


def spawn(cmd: List[str], env: dict) -> subprocess.Popen:
    # Use unbuffered Python output so logs show up immediately
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
    )


def main():
    """
    Usage:
      python run_all.py batperson69 otherUser123

    Starts:
      - 1 consumer
      - 1 producer per username
    """
    usernames = sys.argv[1:]
    if not usernames:
        print("Usage: python run_all.py <username1> [username2 ...]")
        sys.exit(1)

    # Inherit your existing env, but ensure Python prints instantly
    base_env = os.environ.copy()
    base_env["PYTHONUNBUFFERED"] = "1"

    procs: List[subprocess.Popen] = []

    try:
        # 1) Start consumer (single instance handles all games/users)
        consumer_cmd = [sys.executable, "consumer_commentary.py"]
        print(f"[master] starting consumer: {' '.join(consumer_cmd)}")
        consumer_proc = spawn(consumer_cmd, base_env)
        procs.append(consumer_proc)

        # 2) Start one producer per username
        for u in usernames:
            producer_cmd = [sys.executable, "producer_lichess.py", u]
            print(f"[master] starting producer for {u}: {' '.join(producer_cmd)}")
            p = spawn(producer_cmd, base_env)
            procs.append(p)

        # 3) Wait: if any process exits unexpectedly, stop the rest
        while True:
            for p in procs:
                code = p.poll()
                if code is not None:
                    raise RuntimeError(f"Process exited early: pid={p.pid}, code={code}")
            signal.pause()

    except KeyboardInterrupt:
        print("\n[master] Ctrl+C received, shutting down…")

    except Exception as e:
        print(f"\n[master] error: {e}\nshutting down…")

    finally:
        # Terminate all child processes
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass

        # Give them a moment to exit, then kill if needed
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    p.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
