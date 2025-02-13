from xrpl.wallet import generate_faucet_wallet, Wallet
from xrpl.clients import JsonRpcClient
import json

def generate_test_wallets():
    # Connect to testnet
    client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
    
    # Generate wallets
    wallets = {
        "government": generate_faucet_wallet(client, debug=True),
        "dept_a": generate_faucet_wallet(client, debug=True),
        "dept_b": generate_faucet_wallet(client, debug=True),
        "dept_c": generate_faucet_wallet(client, debug=True)
    }
    
    # Create wallet info dictionary
    wallet_info = {}
    for name, wallet in wallets.items():
        wallet_info[name] = {
            "seed": wallet.seed,
            "classic_address": wallet.classic_address
        }
    
    # Save to file
    with open("wallet_credentials.json", "w") as f:
        json.dump(wallet_info, f, indent=4)
        
    # Create .env file
    env_content = f"""GOVERNMENT_WALLET_SEED={wallet_info['government']['seed']}
DEPT_A_WALLET_SEED={wallet_info['dept_a']['seed']}
DEPT_B_WALLET_SEED={wallet_info['dept_b']['seed']}
DEPT_C_WALLET_SEED={wallet_info['dept_c']['seed']}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    return wallet_info

if __name__ == "__main__":
    print("Generating test wallets...")
    wallet_info = generate_test_wallets()
    print("\nWallet credentials have been saved to 'wallet_credentials.json' and '.env'")
    print("\nGovernment wallet address:", wallet_info['government']['classic_address'])
    print("Department A wallet address:", wallet_info['dept_a']['classic_address'])
    print("Department B wallet address:", wallet_info['dept_b']['classic_address'])
    print("Department C wallet address:", wallet_info['dept_c']['classic_address'])