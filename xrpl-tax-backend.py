# requirements.txt contents:
# xrpl-py==1.7.0
# flask==2.0.1
# python-dotenv==0.19.0

from flask import Flask, request, jsonify
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.utils import xrp_to_drops
from xrpl.transaction import submit_and_wait, safe_sign_and_submit_transaction
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

class XRPLTaxSystem:
    def __init__(self):
        # Initialize XRPL client
        self.client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
        
        # Load government wallet from environment variables
        self.gov_wallet = Wallet(seed=os.getenv('GOVERNMENT_WALLET_SEED'))
        
        # Initialize department wallets
        self.department_wallets = {
            'dept_a': Wallet(seed=os.getenv('DEPT_A_WALLET_SEED')),
            'dept_b': Wallet(seed=os.getenv('DEPT_B_WALLET_SEED')),
            'dept_c': Wallet(seed=os.getenv('DEPT_C_WALLET_SEED'))
        }
        
    def process_tax_payment(self, amount_xrp, tax_payer_id):
        """Process a tax payment on XRPL"""
        try:
            # Convert XRP to drops
            amount_drops = xrp_to_drops(amount_xrp)
            
            # Create payment transaction
            payment = Payment(
                account=self.gov_wallet.classic_address,
                amount=amount_drops,
                destination=self.gov_wallet.classic_address,
                source_tag=int(tax_payer_id),  # Use source tag to track payer
            )
            
            # Submit transaction
            response = safe_sign_and_submit_transaction(
                payment, self.gov_wallet, self.client
            )
            
            return {
                "success": True,
                "tx_hash": response.result['hash'],
                "tax_payer_id": tax_payer_id,
                "amount": amount_xrp
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def distribute_funds(self, distributions):
        """Distribute funds to department wallets"""
        results = []
        
        for dept, amount in distributions.items():
            if dept not in self.department_wallets:
                continue
                
            try:
                # Convert XRP to drops
                amount_drops = xrp_to_drops(amount)
                
                # Create payment transaction
                payment = Payment(
                    account=self.gov_wallet.classic_address,
                    amount=amount_drops,
                    destination=self.department_wallets[dept].classic_address
                )
                
                # Submit transaction
                response = safe_sign_and_submit_transaction(
                    payment, self.gov_wallet, self.client
                )
                
                results.append({
                    "department": dept,
                    "success": True,
                    "tx_hash": response.result['hash'],
                    "amount": amount
                })
                
            except Exception as e:
                results.append({
                    "department": dept,
                    "success": False,
                    "error": str(e)
                })
                
        return results

# Initialize tax system
tax_system = XRPLTaxSystem()

# API Routes
@app.route('/api/pay-tax', methods=['POST'])
def pay_tax():
    data = request.json
    result = tax_system.process_tax_payment(
        float(data['amount']),
        data['tax_payer_id']
    )
    return jsonify(result)

@app.route('/api/distribute', methods=['POST'])
def distribute():
    distributions = request.json
    result = tax_system.distribute_funds(distributions)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
