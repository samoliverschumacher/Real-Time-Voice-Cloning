import multiprocessing
import os
import logging
from logging.handlers import RotatingFileHandler


import logging
from logging.config import fileConfig
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event, Thread
import psutil
import time


class BaseLogger:
    def __init__(self, logfile):
        self.logfile = Path(logfile)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Set the logger's level to INFO

        log_handler = RotatingFileHandler(logfile, maxBytes=1024 * 1024, backupCount=5)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(log_handler)

    def set_worker_id(self, worker_id):
        self.worker_id = worker_id
        self.logfile = self.logfile.with_stem(f"{self.logfile.stem}_{worker_id}")
        log_handler = RotatingFileHandler(self.logfile, maxBytes=1024 * 1024, backupCount=5)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        if self.logger.handlers:
            for handler in self.logger.handlers:
                handler.close()
            self.logger.handlers.clear()
            self.logger.addHandler(log_handler)
        else:
            self.logger.addHandler(log_handler)
        self.logger.info(f"Worker ID set: {worker_id}")

    def log(self, msg, level=logging.INFO):
        if hasattr(self, 'worker_id'):
            msg = f'Worker {self.worker_id}: {msg}'
        self.logger.log(level, msg)

    def close(self):
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()


def logger_context_manager(target, logger, args=(), kwargs={}, num_workers=1, master_logfile=None):
    processes = []
    log_files = []

    if master_logfile is None:
        master_logfile = Path('log.txt')

    for worker_id in range(num_workers):
        logfile = master_logfile.with_stem(f"{master_logfile.stem}_{worker_id}")
        log_files.append(logfile)

        kwargs['logger'] = logger
        kwargs['worker_id'] = worker_id
        process = multiprocessing.Process(target=target, args=args, kwargs=kwargs)
        processes.append(process)

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    return log_files


def aggregate_logs(log_files, output_file):
    """
    The `aggregate_logs` function is used to aggregate log files from multiple processes and create a single output file.

    Parameters:
        - log_files: A list of strings representing the paths to the log files.
        - output_file: A string representing the path to the output file.

    Usage:
        1. Create an instance of the `BaseLogger` class to set up the logger.
        2. Spawn multiple processes, each with its own `BaseLogger` instance.
        3. Each process logs messages using the `BaseLogger.log` method.
        4. After the processes have finished, use the `aggregate_logs` function to aggregate the log files.
        5. Specify the list of log files to be aggregated using the `log_files` parameter.
        6. Specify the output file to store the aggregated logs using the `output_file` parameter.
        7. The function reads each log file, extracts the timestamp and message, and appends them to a list of records.
        8. The records are sorted based on the timestamp.
        9. The sorted records are written to the output file.

    Example:
        >>> from multiprocessing import Process

        # Spawn multiple processes, each with its own logger instances
        >>> def spawn_processes():
        >>>     for worker_id in range(1, 4):
        >>>         # Create a logger instance for each process
        >>>         logger = BaseLogger(f'logs_{worker_id}')
                
        >>>         # Log a message from each worker process
        >>>         logger.log(f"Message from worker {worker_id}")
        >>> # Simulating multiple processes
        >>> spawn_processes()

        >>> # Aggregate the log files from the processes
        >>> log_files = ['logs_1.log', 'logs_2.log', 'logs_3.log']
        >>> output_file = 'aggregated_logs.txt'
        >>> aggregate_logs(log_files, output_file)

        >>> # Close the logger after aggregating the logs
        >>> logger.close()
    """
    records = []

    for log_file in log_files:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                timestamp_str, message = line.split(' - ', 1)
                records.append((timestamp_str, message))

    records.sort(key=lambda x: x[0])

    with open(output_file, 'w') as f:
        for record in records:
            f.write(f"{record[1]}")


class MetricsCapturer:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MetricsCapturer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, logger, period=5):
        self.logger: logging.Logger = logger
        
        self._measure_performance = True
        self._metrics_thread = None
        self._period = period
        self._stop_event = Event()

    def run(self):
        while not self._stop_event.is_set():
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_io_counters = psutil.disk_io_counters()

            self.logger.log(msg=f'CPU Usage: {cpu_percent}%', level=logging.INFO)
            self.logger.log(msg=f'Memory Usage: {memory_info.percent}%', level=logging.INFO)
            self.logger.log(msg=f'Disk I/O (Reads: {disk_io_counters.read_count}, Writes: {disk_io_counters.write_count})', level=logging.INFO)
            
            self._stop_event.wait(self._period)

    def start(self):
        if not self._metrics_thread or not self._metrics_thread.is_alive():
            self._measure_performance = True
            self._metrics_thread = Thread(target=self.run)
            self._metrics_thread.daemon = True
            self._metrics_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._metrics_thread:
            self._metrics_thread.join()



if __name__ == '__main__':
    logfile = 'test.log'
    logger = BaseLogger(logfile)
    logger.log("Test message")
    print(os.path.exists(logfile))
    
    print("Log file contents:", open(logfile).read())
    
    # logger = BaseLogger('test.log')
    # logger.log('Test message', logging.INFO)
    # logger.close()
    
# # Configure logging using a configuration file
# fileConfig('logging.conf')

# # Create an instance of the logger
# logger = BaseLogger('app.log')

# # Set the worker ID
# logger.set_worker_id('worker1')

# # Log some messages
# logger.log('Logging info message')
# logger.log('This is a warning', logging.WARNING)

# # Close the logger
# logger.close()

# # Create an instance of the MetricsCapturer
# capturer = MetricsCapturer(logger)

# # Start capturing metrics
# capturer.run()

# # Stop capturing metrics
# capturer.stop()

    
# def process_data(data):
#     logger = BaseLogger('app.log')
#     logger.log(f'Processing data: {data}')
#     # Perform data processing here
#     logger.log(f'Data processed: {data}')
#     logger.close()


# if __name__ == '__main__':
#     logger = BaseLogger('app.log')
#     logger.log('Logging message 1')

#     logger.set_worker_id(1)
#     logger.log('Logging message 2')

#     logger.close()

#     aggregate_logs(['app.log', 'app_1.log'], 'aggregate.log')


#     data = [1, 2, 3, 4, 5]

#     # Create a pool of worker processes
#     with Pool() as pool:
#         # Use the BaseLogger in each worker process
#         pool.map(process_data, data)