import os
import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Lock


from datetime import datetime
import logging
from logging.config import fileConfig
from logging.handlers import RotatingFileHandler
from threading import Event, Thread
import psutil
import time


class BaseLogger:
    """
    The `BaseLogger` class is responsible for setting up a logger with a specified logfile and providing methods for logging messages.

    Attributes:
        - logfile: A string representing the path to the log file.
        - logger: An instance of the `logging.Logger` class for logging messages.
        - lock: A lock object for thread-safety when accessing the logger.

    Methods:
        - __init__(self, logfile): Initializes the `BaseLogger` instance with the given `logfile`. It sets up the logger with the `logfile` and a log handler that rotates the log file when it reaches a certain size. The logger's level is set to `logging.INFO`.
        - set_worker_id(self, worker_id): Sets the `worker_id` attribute and updates the `logfile` with the worker ID. It also updates the log handler to use the updated `logfile`.
        - log(self, message, level=logging.INFO): Logs a message with the specified level. If the `worker_id` attribute is set, it prefixes the message with the worker ID.
        - close(self): Closes the log handler and clears the logger's handlers.

    Note: This class relies on the `logging` module and the `Lock` class from the `threading` module.
    """
    def __init__(self, logfile):
        self.logfile = logfile
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Set the logger's level to INFO
        self.lock = Lock()

        log_handler = RotatingFileHandler(logfile, maxBytes=1024 * 1024, backupCount=5)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(log_handler)

    def set_worker_id(self, worker_id):
        self.worker_id = worker_id
        self.logfile = f"{os.path.splitext(self.logfile)[0]}_{worker_id}{os.path.splitext(self.logfile)[1]}"
        log_handler = RotatingFileHandler(self.logfile, maxBytes=1024 * 1024, backupCount=5)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        if self.logger.handlers:
            handler = self.logger.handlers[0]
            handler.close()
            self.logger.handlers[0] = log_handler
        else:
            self.logger.addHandler(log_handler)
        self.logger.info(f"Worker ID set: {worker_id}")
        
    def log(self, message, level=logging.INFO):
        if hasattr(self, 'worker_id'):
            message = f'Worker {self.worker_id}: {message}'
        with self.lock:
            self.logger.log(level, message)
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()

    def close(self):
        with self.lock:
            for handler in self.logger.handlers:
                handler.close()
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            self.logger.handlers.clear()


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
    
    def __init__(self, logger):
        self.logger: logging.Logger = logger
        self.measure_performance = True
        self.metrics_thread = None
        
        self.stop_event = Event()

    def run(self):
        while not self.stop_event.is_set():
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_io_counters = psutil.disk_io_counters()

            self.logger.log(logging.INFO, f'CPU Usage: {cpu_percent}%')
            self.logger.log(logging.INFO, f'Memory Usage: {memory_info.percent}%')
            self.logger.log(logging.INFO, f'Disk I/O (Reads: {disk_io_counters.read_count}, Writes: {disk_io_counters.write_count})')
            
            self.stop_event.wait(5)

    def start(self):
        if not self.metrics_thread or not self.metrics_thread.is_alive():
            self.measure_performance = True
            self.metrics_thread = Thread(target=self.run)
            self.metrics_thread.daemon = True
            self.metrics_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.metrics_thread:
            self.metrics_thread.join()



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