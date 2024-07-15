import socket
import ssl
import re
import unittest
import argparse
import json

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

    def read_commands_from_json(self, filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        return data['test_cases']

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
    parser.add_argument('--commands', type=str, default='commands.json', help='Path to commands file')
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
        test_cases = self.client.read_commands_from_json(args.commands)
        failures = []

        for test_index, test_case in enumerate(test_cases):
            self.client.disconnect()
            self.client.connect()
            self.client.receive_response()  # Skip server's "hello" message

            for command_data in test_case['commands']:
                command = command_data['command']
                expected_response = command_data['expected_response']
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
