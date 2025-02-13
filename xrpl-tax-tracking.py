from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.utils import xrp_to_drops
from xrpl.transaction import submit_and_wait
from datetime import datetime
import json

class TaxTrackingSystem:
    def __init__(self, network="testnet"):
        # Initialize client based on network
        if network == "testnet":
            self.client = JsonRpcClient("https://s.altnet.rippletest.net:51234")
        else:
            self.client = JsonRpcClient("https://xrplcluster.com")
        
        # Government master wallet - would be set to actual government wallet in production
        self.gov_wallet = Wallet.create()
        
        # Department wallets
        self.department_wallets = {
            "dept_a": Wallet.create(),
            "dept_b": Wallet.create(),
            "dept_c": Wallet.create()
        }
        
        # Transaction records
        self.transactions = []

    def process_tax_payment(self, amount, tax_payer_id):
        """
        Process a tax payment from a user
        """
        try:
            # Create a unique transaction ID
            tx_id = f"TAX-{tax_payer_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Record the payment
            payment_record = {
                "tx_id": tx_id,
                "tax_payer_id": tax_payer_id,
                "amount": amount,
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }
            
            # In production, this would trigger the actual XRPL payment
            # For demo, we're just recording it
            self.transactions.append(payment_record)
            
            return tx_id
            
        except Exception as e:
            raise Exception(f"Failed to process tax payment: {str(e)}")

    def distribute_to_departments(self, distributions):
        """
        Distribute funds to different departments
        distributions = {"dept_a": 1000, "dept_b": 2000, "dept_c": 3000}
        """
        try:
            distribution_record = {
                "tx_id": f"DIST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "distributions": distributions,
                "status": "pending"
            }
            
            # Process each department distribution
            for dept, amount in distributions.items():
                if dept not in self.department_wallets:
                    raise ValueError(f"Invalid department: {dept}")
                
                # In production, this would be actual XRPL transactions
                # For demo, we just record the intended distribution
                tx = {
                    "from_wallet": self.gov_wallet.classic_address,
                    "to_wallet": self.department_wallets[dept].classic_address,
                    "amount": amount
                }
                distribution_record[f"{dept}_tx"] = tx
            
            self.transactions.append(distribution_record)
            return distribution_record["tx_id"]
            
        except Exception as e:
            raise Exception(f"Failed to distribute funds: {str(e)}")

    def get_department_balance(self, department):
        """
        Get the current balance for a department
        """
        if department not in self.department_wallets:
            raise ValueError(f"Invalid department: {department}")
            
        try:
            # In production, this would query actual XRPL balances
            # For demo, we calculate from recorded transactions
            total = 0
            for tx in self.transactions:
                if "distributions" in tx:
                    if department in tx["distributions"]:
                        total += tx["distributions"][department]
            
            return total
            
        except Exception as e:
            raise Exception(f"Failed to get department balance: {str(e)}")

    def generate_dashboard_data(self):
        """
        Generate dashboard data for visualization
        """
        dashboard_data = {
            "total_tax_collected": 0,
            "department_balances": {},
            "recent_transactions": [],
            "distribution_history": []
        }
        
        # Calculate totals and prepare dashboard data
        for tx in self.transactions:
            if "tax_payer_id" in tx:  # Tax payment
                dashboard_data["total_tax_collected"] += tx["amount"]
                dashboard_data["recent_transactions"].append({
                    "type": "tax_payment",
                    "amount": tx["amount"],
                    "timestamp": tx["timestamp"]
                })
            elif "distributions" in tx:  # Distribution
                dashboard_data["distribution_history"].append({
                    "distributions": tx["distributions"],
                    "timestamp": tx["timestamp"]
                })
        
        # Get department balances
        for dept in self.department_wallets.keys():
            dashboard_data["department_balances"][dept] = self.get_department_balance(dept)
        
        return dashboard_data
