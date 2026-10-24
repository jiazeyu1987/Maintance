"""Record local child identities, not command lines or credentials."""
import threading
import psutil


class Tracker:
    def __init__(self, executor, job):
        self.executor, self.job = executor, job
        self.stop = threading.Event()
        self.parent = psutil.Process()
        self.seen = set()
        job['localProcessTracking'] = True
        job['executorIdentity'] = dict(pid=self.parent.pid, createdAt=self.parent.create_time(),
                                       mode=executor.c.get('executionMode', 'console'))
        executor.save()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self):
        while not self.stop.wait(.2):
            try:
                children = self.parent.children(recursive=True)
                additions = []
                for process in children:
                    try:
                        identity = (process.pid, process.create_time())
                    except psutil.NoSuchProcess:
                        continue
                    if identity not in self.seen:
                        self.seen.add(identity)
                        additions.append(dict(pid=identity[0], createdAt=identity[1]))
                if additions:
                    with self.executor.lock:
                        self.job.setdefault('localProcesses', []).extend(additions)
                        self.executor.save()
            except Exception as error:
                # An incomplete observation never means no workers exist.
                with self.executor.lock:
                    self.job['localProcessTrackingError'] = type(error).__name__
                    self.executor.save()
                return

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('Local process recorder did not stop')
