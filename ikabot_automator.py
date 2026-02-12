import os
import sys
import json
import argparse
import traceback
from ikabot import config
from ikabot.web.session import Session
from ikabot.helpers.gui import banner
import importlib

def load_env():
    """Simple parser for .env file to avoid dependencies."""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k, v)

def main(argv=None):
    parser = argparse.ArgumentParser(description='Ikabot Automator')
    parser.add_argument('--config', default='setup.json', help='Path to configuration JSON')
    args = parser.parse_args(argv)

    # Load Env
    load_env()
    
    # Load Config
    try:
        with open(args.config, 'r') as f:
            setup_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Configuration file '{args.config}' is invalid JSON.")
        sys.exit(1)

    # Resolve Credentials
    email = os.getenv('IKABOT_EMAIL') or setup_config.get('email')
    password = os.getenv('IKABOT_PASSWORD')
    otp = os.getenv('IKABOT_OTP')
    account_index = setup_config.get('account_index', 1)

    if not email:
        # Try interactive fallback if not in env or config
        import getpass
        # Simple input for email
        try:
           email = input("Enter Email: ")
        except EOFError:
           pass
           
    if not email:
        print("Error: 'email' is required in .env (IKABOT_EMAIL) or setup.json")
        sys.exit(1)
    if not password:
        # Fallback to interactive (or fail if strictly automated)
        # For this script, we assume automation, so we fail or ask.
        # Let's ask using getpass if allowed, else fail.
        import getpass
        password = getpass.getpass("Enter Password: ")

    # Ensure CWD is User Home (Standard Ikabot behavior for finding .ikabot)
    home = "USERPROFILE" if os.name == "nt" else "HOME"
    target_dir = os.getenv(home)
    if target_dir:
        os.chdir(target_dir)

    print(f"[Automator] Starting session for {email}...")

    # Inject Login Inputs
    # Sequence: [Email, Password, (OTP?), AccountIndex]
    inputs = [email, password]
    if otp:
        inputs.append(otp)
    inputs.append(account_index)
    
    config.predetermined_input = inputs

    try:
        session = Session()
        if not session.logged:
            print("[Automator] Login failed.")
            sys.exit(1)
        
        print("[Automator] Login successful.")

        # Run Actions
        actions = setup_config.get('actions', [])
        for action in actions:
            name = action.get('name')
            action_inputs = action.get('inputs', []) # List of strings/ints
            
            print(f"[Automator] Running action: {name}")
            
            # Setup Inputs for the action
            # The Session is already created, so these inputs are for the function calls (read())
            config.predetermined_input = action_inputs 
            
            try:
                # Dynamic Import
                # Try ikabot.function.{name}
                module_name = f"ikabot.function.{name}"
                module = importlib.import_module(module_name)
                
                # Get the function
                # Convention: function name usually matches module name
                # But sometimes it's camelCase vs snake_case
                # Based on file views: 
                # alertLowWine.py -> def alertLowWine
                # alertAttacks.py -> def alertAttacks
                # monitor_nearby.py -> def monitor_nearby
                if hasattr(module, name):
                    func = getattr(module, name)
                else:
                    # Fallback check?
                    print(f"Warning: Could not find function '{name}' in module '{module_name}'")
                    continue

                # Prepare Args
                # Functions expect: (session, event, stdin_fd, predetermined_input)
                # We need to mock event and stdin_fd
                import multiprocessing
                event = multiprocessing.Event()
                stdin_fd = sys.stdin.fileno()
                
                # Run it
                # Note: Most ikabot functions fork a process or thread.
                # If they fork, they return quickly. 
                # If we want to run multiple, we just call them sequentially.
                func(session, event, stdin_fd, config.predetermined_input)
                
                print(f"[Automator] Action {name} initiated.")
                
            except ImportError:
                print(f"Error: Could not import module 'ikabot.function.{name}'")
            except Exception as e:
                print(f"Error running action {name}: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"[Automator] Critical Error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
