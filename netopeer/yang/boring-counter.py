#!/build/venv/bin/python
"""
Periodically bump /boring-counter:system/counter and emit a counter-update notification.

This is intentionally resilient: the counter lives in the *running* datastore, so a client doing
a copy-config (startup -> running), or anything else that replaces running, wipes it. The next
tick simply writes it back. Any sysrepo error (locked datastore, timeout while a client holds the
lock, etc) is logged and retried on the next tick rather than letting the loop die silently -- a
dead loop means the element never comes back and clients see nondeterministic get-config output.
"""

import signal
import sys
import threading
import traceback

import sysrepo

INTERVAL = 3
XPATH = "/boring-counter:system/counter"
NOTIF_XPATH = "/boring-counter:counter-update"

counter_value = 0
stop = threading.Event()


def log(msg):
    print(f"[boring-counter] {msg}", file=sys.stderr, flush=True)


def seed_startup(conn):
    """
    Seed the counter into the startup datastore so a copy-config from startup to running does not
    remove the element entirely -- best effort, startup is not required for this plugin to work.
    """
    try:
        with conn.start_session("startup") as sess:
            sess.set_item(XPATH, 0)
            sess.apply_changes()
        log("seeded startup datastore")
    except sysrepo.SysrepoError as exc:
        log(f"failed to seed startup datastore (continuing): {exc}")


def tick(sess):
    global counter_value

    counter_value += 1

    sess.set_item(XPATH, counter_value)
    sess.apply_changes()

    sess.notification_send(NOTIF_XPATH, {f"{NOTIF_XPATH}/counter-value": counter_value})


def update_counter_forever():
    while not stop.is_set():
        try:
            with sysrepo.SysrepoConnection() as conn:
                seed_startup(conn)

                with conn.start_session("running") as sess:
                    log("running datastore session established")

                    while not stop.is_set():
                        try:
                            tick(sess)
                        except sysrepo.SysrepoError as exc:
                            # transient (locked/timeout/etc) -- keep the loop alive, retry next tick
                            log(f"tick failed, will retry: {exc}")

                        stop.wait(INTERVAL)
        except Exception:  # noqa: BLE001
            # connection/session level failure, back off and rebuild everything
            log("connection/session failure, reconnecting:")
            traceback.print_exc()

            stop.wait(INTERVAL)


def main():
    threading.Thread(target=update_counter_forever, daemon=True).start()

    signal.sigwait({signal.SIGINT, signal.SIGTERM})
    stop.set()

    return 0


if __name__ == "__main__":
    sys.exit(main())
