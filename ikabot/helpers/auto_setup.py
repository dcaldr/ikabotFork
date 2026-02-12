import argparse
import sys
import os
from ikabot import config
from ikabot.web.session import Session

def main():
    parser = argparse.ArgumentParser(description='Automated Ikabot Setup')
    parser.add_argument('--email', required=True, help='Email address for login')
    parser.add_argument('--password', required=True, help='Password for login')
    parser.add_argument('--otp', help='Two-factor authentication code (if enabled)', default=None)
    parser.add_argument('--account-index', type=int, default=1, help='Account selection index (1-based), default is 1')
    
    args = parser.parse_args()

    # Ensure we are in the correct directory (mimic command_line.init behavior)
    # This ensures the .ikabot file is found/created in the standard location
    home = "USERPROFILE" if os.name == "nt" else "HOME"
    target_dir = os.getenv(home)
    if target_dir:
        os.chdir(target_dir)

    print(f"[Auto-Setup] Starting setup for {args.email}...")

    # Prepare the input queue for Session()
    # Logic in session.py:
    # 1. __login calls input() for Mail (unless provided by magic, but read() handles queue) -> Email
    # 2. __login checks queue for Password -> Password
    # 3. IF 2FA triggers: code calls read() -> OTP
    # 4. IF multiple accounts: code calls read() -> Account Index
    
    # We populate the queue in the specific order they will be requested.
    inputs = []
    
    # 1. Email (consumed by read(msg="Mail:"))
    inputs.append(args.email)
    
    # 2. Password (consumed by config.predetermined_input.pop(0) in __login)
    inputs.append(args.password)
    
    # 3. OTP (Optional)
    # If the user provided OTP, we assume it WILL be asked.
    # If the server DOESN'T ask for it, this might cause desync if there are subsequent inputs.
    # However, Account selection comes AFTER OTP.
    # If OTP is NOT asked, but provided here, it would be consumed by Account Selection (which expects an int).
    # Since OTP is string/int, it might fail validation if account selection checks bounds.
    # For now, we assume if user provides --otp, they know it's needed.
    if args.otp:
        inputs.append(args.otp)
        
    # 4. Account Selection
    # This is only asked if there's more than 1 account. 
    # If there is only 1, the code auto-selects it and DOES NOT call read().
    # If we push this index and it's NOT asked, it remains in the queue (checking warning logs might show leftovers).
    # This is benign unless another input is asked later.
    inputs.append(args.account_index)

    # Inject into config
    config.predetermined_input = inputs
    
    try:
        # Initialize Session
        # This triggers the entire login flow using the injected inputs
        session = Session()
        
        if session.logged:
            print("[Auto-Setup] Login successful! Session created.")
            sys.exit(0)
        else:
            print("[Auto-Setup] Login failed. Session not created.")
            sys.exit(1)
            
    except SystemExit as e:
        # Propagate the exit
        raise e
    except Exception as e:
        print(f"[Auto-Setup] An error occurred: {e}")
        # Identify if it was a "read" recursion error or similar
        sys.exit(1)

if __name__ == '__main__':
    main()
