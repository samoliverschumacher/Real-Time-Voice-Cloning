import multiprocessing
import os
import shutil
import tempfile
from pathlib import Path

from logging_c import BaseLogger, MetricsCapturer, aggregate_logs, logger_context_manager
import unittest
from unittest.mock import patch, MagicMock, call
import logging
import time

class TestMetricsCapturer(unittest.TestCase):

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_io_counters')
    @patch('time.sleep')
    def test_run(self, mock_sleep, mock_disk_io_counters, mock_virtual_memory, mock_cpu_percent):
        with patch('logging_c.time.sleep') as mock_sleep:
            # Test that the logger is called with the correct messages
            mock_cpu_percent.return_value = 50
            mock_virtual_memory.return_value = MagicMock(percent=60)
            mock_disk_io_counters.return_value = MagicMock(read_count=100, write_count=200)
            logger = MagicMock()
            metrics_capturer = MetricsCapturer(logger)
            
            metrics_capturer.start()  # Start capturing metrics in a separate thread

            # Wait for a short time to allow the metrics capturing thread to run
            time.sleep(2)

            metrics_capturer.stop()  # Stop capturing metrics

            # Give some time for the thread to finish execution
            # time.sleep(0.1)
            
            expected_calls = [
                call(logging.INFO, 'CPU Usage: 50%'),
                call(logging.INFO, 'Memory Usage: 60%'),
                call(logging.INFO, 'Disk I/O (Reads: 100, Writes: 200)')
            ]
            logger.log.assert_has_calls(expected_calls, any_order=True)
            
            # Test that the sleep function is called with the correct argument
            self.assertEqual(mock_sleep.call_count, 1)
    
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()

        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

    def tearDown(self):
        # Change the current working directory back to the original directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
        
    def test_only_one_instance_running(self):
        # Define the log file path
        log_file_path = 'metrics.log'

        # Remove the log file if it already exists
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        # Create a logger with a stream handler and file handler
        logger = logging.getLogger('test_logger')
        logger.setLevel(logging.INFO)

        # Create a file handler and set the log file path
        file_handler = logging.FileHandler(log_file_path)
        logger.addHandler(file_handler)

        # Create two instances of MetricsCapturer with the same logger
        capturer1 = MetricsCapturer(logger)
        capturer2 = MetricsCapturer(logger)

        # Start the first instance
        capturer1.start()

        # Try to start the second instance
        capturer2.start()

        # Stop the first instance
        capturer1.stop()

        # Stop the second instance
        capturer2.stop()

        # Assert that both instances refer to the same object
        self.assertIs(capturer1, capturer2)

        # Assert that the log file exists
        self.assertTrue(os.path.exists(log_file_path))

        # Assert that the log file is not empty
        with open(log_file_path, 'r') as log_file:
            log_contents = log_file.read()
            self.assertNotEqual(log_contents, '')

        # Assert that no additional log files were created
        self.assertEqual(len(os.listdir()), 1)
        
        
class LogTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()

        # Change the current working directory to the test directory
        os.chdir(self.test_dir)

    def tearDown(self):
        # Change the current working directory back to the original directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_base_logger(self):
        # Create a BaseLogger instance
        logfile = 'test.log'
        logger = BaseLogger(logfile)

        # Log a message
        logger.log("Test message")

        # Assert that the log file exists
        self.assertTrue(os.path.exists(logfile))

        # Assert that the log file is not empty
        with open(logfile, 'r') as f:
            log_contents = f.read()
            # print(f"{log_contents=}")
            self.assertNotEqual(log_contents, '')

        # Close the logger
        logger.close()

    def test_worker_id_set(self):
        # Create a BaseLogger instance
        logfile = Path(self.test_dir, 'test.log')
        logger = BaseLogger(logfile)

        # Set the worker ID
        worker_id = 123
        logger.set_worker_id(worker_id)

        # Assert that the worker ID is set correctly
        self.assertEqual(logger.worker_id, worker_id)

        # Assert that the log file is updated with the worker ID
        
        expected_logfile = logfile.with_stem(f"{logfile.stem}_{worker_id}")
        self.assertEqual(logger.logfile, expected_logfile)

        # Close the logger
        logger.close()
        

    def test_base_logger_multiprocessing(self):
        # Create a list to store the log file paths
        log_files = []

        def worker(worker_id, logger: BaseLogger):

            logger.set_worker_id(worker_id)
            # Log a message with the worker ID
            logger.log(f"Worker {worker_id} message")

        # Create multiple worker processes
        logfile = Path(self.test_dir, f"logging.log")
        # Create a BaseLogger instance for the workers
        logger = BaseLogger(logfile)
        num_workers = 2
        processes = []
        for i in range(num_workers):
            process = multiprocessing.Process(target=worker, args=(i,logger))
            processes.append(process)

        # Start the worker processes
        for process in processes:
            process.start()

        # Wait for the worker processes to finish
        for process in processes:
            process.join()

        # Assert that the log files were created for each worker within the test directory
        worker_logfiles = [logfile.with_stem(f"{logfile.stem}_{i}") for i in range(num_workers)]
        for logfile in worker_logfiles:
            self.assertTrue(logfile.exists())

        # Assert that the log contain worker-specific messages
        expected_worker_messages = [f"Worker {i} message" for i in range(num_workers)]
        for logfile, expected_message in zip(worker_logfiles, expected_worker_messages):
            with open(logfile, 'r') as f:
                log_contents = f.read().strip()
                self.assertTrue(log_contents.endswith(expected_message), f"{log_contents} doesnt endswith {expected_message}")

    def test_aggregate_logs(self):
        # Create temporary log files within the test directory
        log_files = [os.path.join(self.test_dir, 'log1.log'),
                     os.path.join(self.test_dir, 'log2.log'),
                     os.path.join(self.test_dir, 'log3.log')]
        log_contents = [
            '2022-01-01 10:00:00 - Log message 1\n',
            '2022-01-01 11:00:00 - Log message 2\n',
            '2022-01-01 09:00:00 - Log message 3\n',
        ]
        for i, log_file in enumerate(log_files):
            with open(log_file, 'w') as f:
                f.write(log_contents[i])

        # Aggregate the log files within the test directory
        output_file = os.path.join(self.test_dir, 'output.log')
        aggregate_logs(log_files, output_file)

        # Assert that the log messages are aggregated in the correct order
        with open(output_file, 'r') as f:
            aggregated_log_contents = [line for line in f.readlines()]
            expected_log_contents = sorted(log_contents)  # Sort the log_contents list
            self.assertTrue(all([entry.endswith(msg) for entry, msg in zip(expected_log_contents, aggregated_log_contents)]))


# class TestLoggerContextManager(unittest.TestCase):
#     def test_logger_context_manager(self):
#         # Set up the test
#         num_workers = 2
        
#         target_function = MagicMock()
#         def target_function(logger):
#             logger.set_worker_id()
            
        
#         logger = BaseLogger('test.log')

#         # Call the logger context manager function
#         log_files = logger_context_manager(target_function,logger, num_workers=num_workers, master_logfile=logger.logfile)

#         try:
#             # Check that the log files are created and contain the expected messages
#             for worker_id in range(num_workers):
#                 log_file = log_files[worker_id]
#                 self.assertTrue(log_file.exists())

#                 with open(log_file, "r") as file:
#                     log_contents = file.read()
#                     self.assertIn("Test message", log_contents)
#         finally:
#             # Clean up the test
#             for log_file in log_files:
#                 log_file.unlink()

if __name__ == "__main__":
    unittest.main()

if __name__ == '__main__':
    unittest.main()
    