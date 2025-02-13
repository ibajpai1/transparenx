from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
import traceback
import json

# ------------------- XRPL-PY IMPORTS -------------------
from xrpl.clients import JsonRpcClient
from xrpl.wallet import generate_faucet_wallet, Wallet
from xrpl.models.requests import AccountInfo, AccountTx
from xrpl.models.transactions import Payment
from xrpl.transaction import autofill, sign, submit
from xrpl.utils import xrp_to_drops

# ------------------- SETUP FLASK -------------------
app = Flask(__name__)

# ------------------- XRPL TAX SYSTEM CLASS -------------------
class XRPLTaxSystem:
    def __init__(self):
        """
        Initialize the XRPL client and either load existing wallets from .env
        or generate new ones if they don't exist.
        """
        # Load environment variables
        load_dotenv()
        
        # Use the Devnet JSON-RPC endpoint
        self.client = JsonRpcClient("https://s.devnet.rippletest.net:51234")

        # Initialize system wallets (either from .env or generate new ones)
        self.tax_pool = self._get_or_create_wallet('TAX_POOL')
        self.exit_pool = self._get_or_create_wallet('EXIT_POOL')
        self.gov_wallet = self._get_or_create_wallet('GOV_WALLET')
        
        # Department wallet IDs
        department_ids = [
            "dept_transport", "dept_labor", "dept_education",
            "penn_dept_transport", "penn_dept_labor", "penn_dept_education",
            "pitt_dept_transport", "pitt_dept_labor", "pitt_dept_education",
            "squirrel_hill_dept_transport"
        ]
        
        # Initialize department wallets
        self.department_wallets = {}
        for dept_id in department_ids:
            env_key = f"WALLET_{dept_id.upper()}"
            self.department_wallets[dept_id] = self._get_or_create_wallet(env_key)

    def _get_or_create_wallet(self, env_key: str) -> Wallet:
        """
        Helper method to either load a wallet from environment variables
        or create a new one and save it to .env
        """
        try:
            # Try to load existing wallet from environment
            seed = os.getenv(env_key)
            if seed:
                return Wallet.from_seed(seed)
            
            # If no wallet exists, generate a new one
            print(f"Generating new wallet for {env_key}...")
            wallet = generate_faucet_wallet(self.client, debug=True)
            
            # Append the new wallet to .env file
            with open('.env', 'a') as f:
                f.write(f'\n{env_key}={wallet.seed}')
            
            return wallet
            
        except Exception as e:
            print(f"Error handling wallet {env_key}: {e}")
            # If there's an error, generate a new wallet but don't save it
            return generate_faucet_wallet(self.client, debug=True)

    def get_wallet_balance(self, wallet: Wallet) -> float:
        """Query the on-ledger balance (in XRP) for the given wallet."""
        try:
            acct_info_request = AccountInfo(
                account=wallet.classic_address,
                ledger_index="validated"
            )
            response = self.client.request(acct_info_request)
            result = response.result

            # If the XRPL doesn't recognize the account, it won't have "account_data"
            if "account_data" not in result:
                # Possibly "actNotFound" if it were unfunded, but we are funding from faucet
                raise ValueError(f"account_data not found in response: {result}")

            balance_drops = float(result["account_data"]["Balance"])
            balance_xrp = balance_drops / 1_000_000
            return balance_xrp

        except Exception as e:
            print(f"Error getting wallet balance: {e}")
            return 0.0


    def process_tax_payment(self, amount_xrp: float, tax_payer_id: str):
        """
        Process a tax payment by sending XRP from tax pool to government wallet.
        Args:
            amount_xrp: Amount of XRP to pay
            tax_payer_id: ID of the department paying tax
        """
        try:
            # Check if tax pool has sufficient balance
            pool_balance = self.get_wallet_balance(self.tax_pool)
            if pool_balance < amount_xrp:
                return {
                    "success": False,
                    "error": f"Insufficient balance in tax pool. Current balance: {pool_balance} XRP"
                }

            # Send from tax pool to government wallet
            amount_drops = xrp_to_drops(amount_xrp)
            payment_tx = Payment(
                account=self.tax_pool.classic_address,
                amount=amount_drops,
                destination=self.gov_wallet.classic_address,
                source_tag=int(hash(tax_payer_id) % (2**32))  # Convert tax_payer_id to a 32-bit integer for tracking
            )
            
            # Process payment
            autofilled_tx = autofill(payment_tx, self.client)
            signed_tx = sign(autofilled_tx, self.tax_pool)
            response = submit(signed_tx, self.client)

            if not response.is_successful():
                return {
                    "success": False,
                    "error": f"Payment failed: {response.result.get('engine_result_message', 'Unknown error')}"
                }

            tx_hash = response.result.get("tx_json", {}).get("hash", "")
            if not tx_hash:
                return {
                    "success": False,
                    "error": "Transaction submitted but hash not found"
                }

            return {
                "success": True,
                "message": "Tax payment processed successfully",
                "tax_payer_id": tax_payer_id,
                "amount": amount_xrp,
                "tx_hash": tx_hash
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def distribute_funds(self, sender: str, receiver: str, amount_xrp: float):
        """
        Transfer XRP between any system wallets
        Args:
            sender: ID of the sending wallet
            receiver: ID of the receiving wallet 
            amount_xrp: Amount of XRP to transfer
        Returns:
            Dictionary with transaction result
        """
        try:
            # Get sender wallet
            if sender == "GOV_WALLET":
                sender_wallet = self.gov_wallet
            elif sender == "tax_pool":
                sender_wallet = self.tax_pool
            elif sender == "exit_pool":
                sender_wallet = self.exit_pool
            elif sender in self.department_wallets:
                sender_wallet = self.department_wallets[sender]
            else:
                return {
                    "success": False,
                    "error": f"Invalid sender: {sender}"
                }
            
            # Get receiver wallet
            if receiver == "GOV_WALLET":
                receiver_wallet = self.gov_wallet
            elif receiver == "tax_pool":
                receiver_wallet = self.tax_pool
            elif receiver == "exit_pool":
                receiver_wallet = self.exit_pool
            elif receiver in self.department_wallets:
                receiver_wallet = self.department_wallets[receiver]
            else:
                return {
                    "success": False, 
                    "error": f"Invalid receiver: {receiver}"
                }

            if sender == receiver:
                return {
                    "success": False,
                    "error": "Sender and receiver cannot be the same"
                }
            
            # Check sender has sufficient balance
            sender_balance = self.get_wallet_balance(sender_wallet)
            if sender_balance < amount_xrp:
                return {
                    "success": False,
                    "error": f"Insufficient balance. Sender has {sender_balance} XRP"
                }

            # Create and submit payment transaction
            amount_drops = xrp_to_drops(amount_xrp)
            payment_tx = Payment(
                account=sender_wallet.classic_address,
                amount=amount_drops,
                destination=receiver_wallet.classic_address
            )
            
            # Autofill transaction details
            autofilled_tx = autofill(payment_tx, self.client)
            
            # Sign with sender's wallet
            signed_tx = sign(autofilled_tx, sender_wallet)
            
            # Submit transaction
            response = submit(signed_tx, self.client)
            
            if not response.is_successful():
                return {
                    "success": False,
                    "error": f"Transaction failed: {response.result.get('engine_result_message', 'Unknown error')}"
                }

            tx_hash = response.result.get("tx_json", {}).get("hash", "")
            if not tx_hash:
                return {
                    "success": False,
                    "error": "Transaction submitted but hash not found"
                }

            return {
                "success": True,
                "message": "Transaction successful",
                "tx_hash": tx_hash,
                "sender": sender,
                "receiver": receiver,
                "amount": amount_xrp
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_all_balances(self):
        """Return a dict of the government + department wallet balances."""
        return {
            "government": self.get_wallet_balance(self.gov_wallet),
            "dept_transport": self.get_wallet_balance(self.department_wallets["dept_transport"]),
            "dept_labor": self.get_wallet_balance(self.department_wallets["dept_labor"]),
            "dept_education": self.get_wallet_balance(self.department_wallets["dept_education"]),
            "penn_dept_transport": self.get_wallet_balance(self.department_wallets["penn_dept_transport"]),
            "penn_dept_labor": self.get_wallet_balance(self.department_wallets["penn_dept_labor"]),
            "penn_dept_education": self.get_wallet_balance(self.department_wallets["penn_dept_education"]),
            "pitt_dept_transport": self.get_wallet_balance(self.department_wallets["pitt_dept_transport"]),
            "pitt_dept_labor": self.get_wallet_balance(self.department_wallets["pitt_dept_labor"]),
            "pitt_dept_education": self.get_wallet_balance(self.department_wallets["pitt_dept_education"]),
            "squirrel_hill_dept_transport": self.get_wallet_balance(self.department_wallets["squirrel_hill_dept_transport"]),
        }

    def get_transactions(self, wallet=None):
        """Get all transactions for a wallet or all wallets"""
        try:
            transactions = []
            processed_tx_hashes = set()  # To avoid duplicate transactions
            
            # Determine which wallets to check
            if wallet:
                print(f"Checking transactions for specific wallet: {wallet.classic_address}")
                wallets_to_check = [(None, wallet)]
            else:
                print("Checking transactions for all wallets")
                wallets_to_check = [
                    ('tax_pool', self.tax_pool),
                    ('government', self.gov_wallet),
                    ('exit_pool', self.exit_pool)
                ]
                # Add all department wallets
                for dept_id, dept_wallet in self.department_wallets.items():
                    wallets_to_check.append((dept_id, dept_wallet))

            print(f"Total wallets to check: {len(wallets_to_check)}")
            
            # Check each wallet's transactions
            for dept_name, dept_wallet in wallets_to_check:
                print(f"\nChecking {dept_name if dept_name else 'wallet'}: {dept_wallet.classic_address}")
                
                try:
                    # Get account transaction history with higher limit
                    tx_request = AccountTx(
                        account=dept_wallet.classic_address,
                        ledger_index_min=-1,  # Get all historical transactions
                        ledger_index_max=-1,
                        limit=200  # Increased limit
                    )
                    response = self.client.request(tx_request)
                    
                    if not response.is_successful():
                        print(f"Error getting transactions: {response.result.get('error_message', 'Unknown error')}")
                        continue
                    
                    # Process each transaction
                    for tx_info in response.result.get('transactions', []):
                        try:
                            # Get transaction data
                            tx = tx_info.get('tx_json') or tx_info.get('tx') or tx_info.get('transaction')
                            if not tx:
                                print("No transaction data found")
                                continue
                            
                            # Get transaction hash
                            tx_hash = tx.get('hash', '') or tx_info.get('hash', '')
                            if not tx_hash:
                                print("No transaction hash found")
                                continue
                            
                            # Skip if we've already processed this transaction
                            if tx_hash in processed_tx_hashes:
                                print(f"Skipping duplicate transaction: {tx_hash}")
                                continue
                            
                            # Only process Payment type transactions
                            if tx.get('TransactionType') != 'Payment':
                                print(f"Skipping non-payment transaction: {tx.get('TransactionType')}")
                                continue
                            
                            # Get sender and receiver
                            sender = tx.get('Account', '')
                            receiver = tx.get('Destination', '')
                            if not sender or not receiver:
                                print("Missing sender or receiver")
                                continue
                            
                            # Convert addresses to department names
                            sender_name = self._get_dept_name(sender)
                            receiver_name = self._get_dept_name(receiver)
                            if not sender_name or not receiver_name:
                                print(f"Unknown sender or receiver: {sender} -> {receiver}")
                                continue
                            
                            # Get amount
                            meta = tx_info.get('meta', {})
                            amount = None
                            for amount_field in ['Amount', 'DeliverMax', 'delivered_amount']:
                                if amount_field in tx:
                                    amount = tx[amount_field]
                                    break
                                elif amount_field in meta:
                                    amount = meta[amount_field]
                                    break
                            
                            if not amount:
                                print("No amount found")
                                continue
                            
                            # Convert amount to XRP
                            try:
                                amount_xrp = float(amount) / 1_000_000
                            except (ValueError, TypeError):
                                print(f"Invalid amount format: {amount}")
                                continue
                            
                            # Get timestamp
                            timestamp = tx.get('date', 0)
                            if timestamp:
                                timestamp += 946684800  # Convert Ripple epoch to Unix timestamp
                            
                            # Check if transaction was successful
                            if meta.get('TransactionResult') != 'tesSUCCESS':
                                print(f"Transaction not successful: {meta.get('TransactionResult')}")
                                continue
                            
                            # Add transaction to list
                            processed_tx_hashes.add(tx_hash)
                            transactions.append({
                                'type': 'Tax Payment' if tx.get('SourceTag') else 'Payment',
                                'sender': sender_name,
                                'receiver': receiver_name,
                                'amount_xrp': amount_xrp,
                                'timestamp': timestamp,
                                'tx_hash': tx_hash,
                                'success': True
                            })
                            print(f"Added transaction: {tx_hash} - {sender_name} -> {receiver_name}: {amount_xrp} XRP")
                            
                        except Exception as tx_error:
                            print(f"Error processing transaction: {tx_error}")
                            continue
                        
                except Exception as wallet_error:
                    print(f"Error checking wallet {dept_name}: {wallet_error}")
                    continue
                
            print(f"Total transactions found: {len(transactions)}")
            # Sort transactions by timestamp, newest first
            transactions.sort(key=lambda x: x['timestamp'], reverse=True)
            return transactions
            
        except Exception as e:
            print(f"Error getting transactions: {e}")
            traceback.print_exc()
            return []

    def get_department_hierarchy(self, dept_id):
        """
        Get hierarchical transaction data showing the entire transaction tree
        Returns aggregated transaction data showing full transaction flow
        """
        try:
            hierarchy_data = {
                'nodes': [],
                'links': [],
                'transactions': {},
                'chains': []
            }
            
            # Initialize with all wallets
            wallets_to_check = list(self.department_wallets.items())
            wallets_to_check.append(('government', self.gov_wallet))
            wallets_to_check.append(('tax_pool', self.tax_pool))
            wallets_to_check.append(('exit_pool', self.exit_pool))
            
            print(f"Total wallets to check: {len(wallets_to_check)}")
            
            # First, add all wallets as nodes
            for dept_name, _ in wallets_to_check:
                hierarchy_data['nodes'].append({
                    'id': dept_name,
                    'name': dept_name.replace('_', ' ').title(),
                    'level': 0  # We'll adjust levels later
                })
            
            # Get all transactions for all wallets
            all_transactions = []
            processed_tx_hashes = set()
            
            for dept_name, wallet in wallets_to_check:
                print(f"\nGetting transactions for {dept_name}")
                txs = self.get_transactions(wallet)
                for tx in txs:
                    if tx['tx_hash'] not in processed_tx_hashes:
                        processed_tx_hashes.add(tx['tx_hash'])
                        all_transactions.append(tx)
            
            print(f"Total unique transactions found: {len(all_transactions)}")
            
            # Sort transactions by timestamp to establish flow
            all_transactions.sort(key=lambda x: x['timestamp'])
            
            # Process all transactions to create links
            for tx in all_transactions:
                sender = tx['sender']
                receiver = tx['receiver']
                
                # Only process if both parties are in our wallet list
                if any(name == sender for name, _ in wallets_to_check) and \
                   any(name == receiver for name, _ in wallets_to_check):
                    
                    # Add or update link
                    existing_link = next((l for l in hierarchy_data['links'] 
                                       if l['source'] == sender and l['target'] == receiver), None)
                    
                    if existing_link:
                        existing_link['value'] += float(tx['amount_xrp'])
                        existing_link['transactions'].append(tx)
                    else:
                        hierarchy_data['links'].append({
                            'source': sender,
                            'target': receiver,
                            'value': float(tx['amount_xrp']),
                            'transactions': [tx]
                        })
            
            # Calculate levels based on transaction flow from the selected department
            def calculate_levels(start_dept, visited=None, level=0):
                if visited is None:
                    visited = set()
                
                if start_dept in visited:
                    return
                
                visited.add(start_dept)
                
                # Update level for this department
                node = next(node for node in hierarchy_data['nodes'] if node['id'] == start_dept)
                node['level'] = level
                
                # Find all outgoing transactions
                outgoing_links = [link for link in hierarchy_data['links'] if link['source'] == start_dept]
                
                # Recursively update levels for connected departments
                for link in outgoing_links:
                    calculate_levels(link['target'], visited, level + 1)
            
            # Calculate levels starting from the selected department
            calculate_levels(dept_id)
            
            # Calculate transaction metrics for all nodes
            for node in hierarchy_data['nodes']:
                dept = node['id']
                dept_wallet = next(wallet for name, wallet in wallets_to_check if name == dept)
                
                # Get all transactions for this department
                dept_txs = [tx for tx in all_transactions 
                           if tx['sender'] == dept or tx['receiver'] == dept]
                
                sent_txs = [tx for tx in dept_txs if tx['sender'] == dept]
                received_txs = [tx for tx in dept_txs if tx['receiver'] == dept]
                
                hierarchy_data['transactions'][dept] = {
                    'total_sent': sum(float(tx['amount_xrp']) for tx in sent_txs),
                    'total_received': sum(float(tx['amount_xrp']) for tx in received_txs),
                    'balance': self.get_wallet_balance(dept_wallet),
                    'transaction_count': len(dept_txs),
                    'sent_transactions': sent_txs,
                    'received_transactions': received_txs
                }
            
            print(f"\nFinal Statistics:")
            print(f"Total wallets: {len(hierarchy_data['nodes'])}")
            print(f"Total links: {len(hierarchy_data['links'])}")
            print(f"Total transactions: {len(all_transactions)}")
            
            return hierarchy_data
            
        except Exception as e:
            print(f"Error building hierarchy: {e}")
            traceback.print_exc()
            return {
                'nodes': [],
                'links': [],
                'transactions': {},
                'chains': []
            }

    def _get_dept_name(self, address: str) -> str:
        """Helper to get department name from wallet address"""
        try:
            # Check system wallets first
            if address == self.tax_pool.classic_address:
                return "tax_pool"
            if address == self.exit_pool.classic_address:
                return "exit_pool"
            if address == self.gov_wallet.classic_address:
                return "government"
            
            # Check department wallets
            for dept_name, wallet in self.department_wallets.items():
                if address == wallet.classic_address:
                    return dept_name
            
            # If no match found, return None instead of the address
            return None
            
        except Exception as e:
            print(f"Error in _get_dept_name for address {address}: {e}")
            return None

# Instantiate the tax system once (global to the Flask app)
tax_system = XRPLTaxSystem()

# ------------------- FLASK ROUTES -------------------

@app.route('/')
def index():
    """Render an index page (you need an index.html template or remove this route)."""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Render an index page (you need an index.html template or remove this route)."""
    return render_template('admin.html')

@app.route('/api/balances', methods=['GET'])
def get_balances():
    """Return JSON with current balances of all wallets."""
    return jsonify(tax_system.get_all_balances())

@app.route('/api/pay-tax', methods=['POST'])
def pay_tax():
    """POST JSON: {"amount": number, "tax_payer_id": string}"""
    try:
        data = request.json
        amount = float(data["amount"])
        tax_payer_id = data["tax_payer_id"]
        result = tax_system.process_tax_payment(amount, tax_payer_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/transfer', methods=['POST'])
def transfer():
    """
    POST JSON: {
        "sender": "dept_id",
        "receiver": "dept_id",
        "amount": number
    }
    """
    try:
        data = request.json
        sender = data["sender"]
        receiver = data["receiver"]
        amount = float(data["amount"])
        
        result = tax_system.distribute_funds(sender, receiver, amount)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get all transactions for the system"""
    try:
        transactions = tax_system.get_transactions()
        return jsonify({
            "success": True,
            "transactions": transactions
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/transactions')
def transactions():
    """Render the transactions page"""
    return render_template('transactions.html')

@app.route('/api/transactions/<wallet_id>', methods=['GET'])
def get_wallet_transactions(wallet_id):
    """Get transactions for a specific wallet"""
    try:
        # Get the wallet object based on wallet_id
        if wallet_id == 'government':
            wallet = tax_system.gov_wallet
        elif wallet_id == 'tax_pool':
            wallet = tax_system.tax_pool
        elif wallet_id == 'exit_pool':
            wallet = tax_system.exit_pool
        elif wallet_id in tax_system.department_wallets:
            wallet = tax_system.department_wallets[wallet_id]
        else:
            return jsonify({
                "success": False,
                "error": f"Invalid wallet ID: {wallet_id}"
            }), 400

        # Get transactions for this wallet
        transactions = tax_system.get_transactions(wallet)
        
        # Get current balance
        balance = tax_system.get_wallet_balance(wallet)
        
        return jsonify({
            "success": True,
            "wallet_id": wallet_id,
            "wallet_address": wallet.classic_address,
            "wallet_balance": balance,
            "transactions": transactions
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/department-tracking')
def department_tracking():
    """Render the department tracking page"""
    return render_template('department_tracking.html')

@app.route('/api/department-hierarchy/<dept_id>')
def get_department_data(dept_id):
    """Get hierarchical transaction data for a department"""
    try:
        hierarchy_data = tax_system.get_department_hierarchy(dept_id)
        if hierarchy_data:
            return jsonify({
                "success": True,
                "data": hierarchy_data
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not build hierarchy"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/transaction-tree')
def get_transaction_tree():
    """Get the complete transaction tree data"""
    try:
        # Get all wallets and their balances
        nodes = []
        
        # Add government wallet
        gov_balance = tax_system.get_wallet_balance(tax_system.gov_wallet)
        nodes.append({
            "id": "government",
            "name": "Federal Government",
            "balance": gov_balance,
            "totalSent": 0,
            "totalReceived": 0
        })
        
        # Add pool wallets
        tax_balance = tax_system.get_wallet_balance(tax_system.tax_pool)
        nodes.append({
            "id": "tax_pool",
            "name": "Tax Pool",
            "balance": tax_balance,
            "totalSent": 0,
            "totalReceived": 0
        })
        
        exit_balance = tax_system.get_wallet_balance(tax_system.exit_pool)
        nodes.append({
            "id": "exit_pool",
            "name": "Exit Pool",
            "balance": exit_balance,
            "totalSent": 0,
            "totalReceived": 0
        })
        
        # Add department wallets
        for dept_id, wallet in tax_system.department_wallets.items():
            balance = tax_system.get_wallet_balance(wallet)
            nodes.append({
                "id": dept_id,
                "name": dept_id.replace('_', ' ').title(),
                "balance": balance,
                "totalSent": 0,
                "totalReceived": 0
            })
            
        # Get all transactions
        transactions = tax_system.get_transactions()
        
        # Create links and update totals
        links = []
        for tx in transactions:
            # Update node totals
            for node in nodes:
                if node["id"] == tx["sender"]:
                    node["totalSent"] += float(tx["amount_xrp"])
                if node["id"] == tx["receiver"]:
                    node["totalReceived"] += float(tx["amount_xrp"])
            
            # Add link with transaction details
            links.append({
                "source": tx["sender"],
                "target": tx["receiver"],
                "value": float(tx["amount_xrp"]),
                "timestamp": tx["timestamp"],
                "tx_hash": tx["tx_hash"]
            })
        
        # Create hierarchical structure
        tree_data = {
            "root": {
                "name": "Transaction System",
                "children": nodes
            },
            "links": links
        }
        
        # Debug print
        print("Tree data structure:")
        print(json.dumps(tree_data, indent=2))
        
        return jsonify({
            "success": True,
            "data": tree_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

# ------------------- MAIN ENTRY POINT -------------------
if __name__ == '__main__':
    # Print out our wallets
    print("\n-- Government Wallet --")
    print(f"  Seed: {tax_system.gov_wallet.seed}")
    print(f"  Address: {tax_system.gov_wallet.classic_address}")

    print("\n-- Department Wallets --")
    for dept_name, wallet_obj in tax_system.department_wallets.items():
        print(f"  {dept_name} Seed: {wallet_obj.seed}")
        print(f"  {dept_name} Address: {wallet_obj.classic_address}")

    # Print initial balances
    print("\n-- Initial Balances --")
    print(tax_system.get_all_balances())

    # Start Flask server
    app.run(debug=False, port=80, host='0.0.0.0')
