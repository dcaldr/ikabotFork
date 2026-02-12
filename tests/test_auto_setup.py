import unittest
from unittest.mock import MagicMock, patch
import json
import os
from ikabot import config

# We need to mock sys.argv or the parsed args before importing auto_setup if it were a script,
# but since we'll import it as a module, we can test functions directly.
# However, auto_setup likely will run logic on import if not careful, so we should structure it with a main() function.

class TestAutoSetup(unittest.TestCase):
    
    def setUp(self):
        # Reset predetermined_input before each test
        config.predetermined_input = []

    def test_argument_parsing_simple(self):
        """Test that arguments are correctly parsed and populated into predetermined_input."""
        # This assumes we have a function in auto_setup that takes args and populates the config
        # Let's define the expected behavior of the module we are about to write.
        from ikabot.helpers import auto_setup
        
        args = [
            '--email', 'test@example.com',
            '--password', 'password123',
            '--account-index', '1'
        ]
        
        # Mock sys.argv
        with patch('sys.argv', ['auto_setup.py'] + args):
            with patch('ikabot.web.session.Session') as mock_session_cls:
                mock_session = MagicMock()
                mock_session.logged = True
                mock_session.padre = True
                mock_session_cls.return_value = mock_session
                
                # Mock system exit to prevent actual exit
                with self.assertRaises(SystemExit) as cm:
                    auto_setup.main()
                
                # Verify exit code 0 (success)
                self.assertEqual(cm.exception.code, 0)
                
                # Verify input queue
                # Expected: [email, password, account_index]
                # The pop() order in session.py is:
                # 1. read(msg="Mail:") -> pops email
                # 2. config.predetermined_input.pop(0) -> pops password
                # 3. read(min=1, max=i) -> selection of account (if multiple)
                
                # NOTE: If we mocked Session, the __init__ might not have actually run the logic that Pops data 
                # unless we verified that the 'main' function POPULATED it.
                # We can check what's LEFT in the list or what was put IN.
                # Since Session is mocked, it won't consume them. checking config.predetermined_input.
                
                expected_inputs = ['test@example.com', 'password123', 1]
                self.assertEqual(config.predetermined_input, expected_inputs)

    def test_argument_parsing_with_otp(self):
        """Test input sequence with OTP."""
        from ikabot.helpers import auto_setup
        
        args = [
            '--email', 'test@example.com',
            '--password', 'password123',
            '--otp', '123456',
            '--account-index', '2'
        ]
        
        with patch('sys.argv', ['auto_setup.py'] + args):
             with patch('ikabot.web.session.Session') as mock_session_cls:
                mock_session = MagicMock()
                mock_session.logged = True
                mock_session_cls.return_value = mock_session
                
                with self.assertRaises(SystemExit) as cm:
                    auto_setup.main()
                
                self.assertEqual(cm.exception.code, 0)
                
                # Expected order: Email, Password, OTP, Account Selection
                expected_inputs = ['test@example.com', 'password123', '123456', 2]
                self.assertEqual(config.predetermined_input, expected_inputs)

if __name__ == '__main__':
    unittest.main()
