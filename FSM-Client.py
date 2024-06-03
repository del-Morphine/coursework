import socket
import ssl
import re
import unittest
import argparse

class UniversalClient:
    def __init__(self, host, port, use_ssl=False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_ssl:
            ssl_context = ssl.create_default_context()
            self.sock = ssl_context.wrap_socket(self.sock, server_hostname=self.host)
        self.sock.connect((self.host, self.port))

    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def read_commands_from_file(self, filename):
        tests = []
        pair_pattern = re.compile(r'(.+?/.+?)(?=\s|$)')
        with open(filename, 'r') as file:
            for line in file:
                pairs = pair_pattern.findall(line.strip())
                commands = []
                expected_responses = []
                for pair in pairs:
                    command, expected_response = pair.rsplit('/', 1)
                    commands.append(command.strip() + "\r\n")
                    expected_responses.append(expected_response)
                tests.append((commands, expected_responses))
        return tests

    def send_command(self, command):
        self.sock.send(command.encode())
        return self.receive_response()

    def receive_response(self):
        response = b""  
        self.sock.settimeout(2)      
        try:
            while True:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                response += chunk  
        except socket.timeout:
            pass
        return response.decode()

    def close(self):
        if self.sock:
            self.sock.close()

def parse_args():
    parser = argparse.ArgumentParser(description='Universal Client for Server Testing')
    parser.add_argument('host', type=str, help='Server host address')
    parser.add_argument('port', type=int, help='Server port')
    parser.add_argument('--ssl', action='store_true', help='Use SSL for the connection')
    parser.add_argument('--commands', type=str, default='commands.txt', help='Path to commands file')
    parser.add_argument('--continue-on-error', action='store_true', help='Continue on error and trace incorrect responses')    
    return parser.parse_args()

class TestUniversalClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global args
        cls.client = UniversalClient(args.host, args.port, use_ssl=args.ssl)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_protocol_implementation(self):
        tests = self.client.read_commands_from_file(args.commands)
        failures = []

        for test_index, (commands, expected_responses) in enumerate(tests):
            self.client.disconnect()
            self.client.connect()
            self.client.receive_response()  # Skip server's "hello" message
            for command, expected_response in zip(commands, expected_responses):
                actual_response = self.client.send_command(command)
                try:
                    self.assertIn(expected_response, actual_response, f"Expected: {expected_response}, but got: {actual_response}")
                    print(actual_response)
                except AssertionError as e:
                    failures.append(f"Test {test_index + 1}, Command: {command.strip()} | Expected: {expected_response} | Got: {actual_response}")
                    if not args.continue_on_error:
                        raise e

        if failures:
            for failure in failures:
                print(f"FAILURE: {failure}")
            self.fail(f"{len(failures)} failures encountered. See details above.")

if __name__ == "__main__":
    args = parse_args()
    unittest.main(argv=['first-arg-is-ignored'], exit=False)