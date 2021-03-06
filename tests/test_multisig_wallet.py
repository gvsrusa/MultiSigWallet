# ethereum
from ethereum import tester as t
from ethereum.tester import keys, accounts
from ethereum.tester import TransactionFailed
# standard libraries
from unittest import TestCase


class TestContract(TestCase):
    """
    run test with python -m unittest tests.test_multisig_wallet
    """

    HOMESTEAD_BLOCK = 1150000

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        self.s = t.state()
        self.s.block.number = self.HOMESTEAD_BLOCK
        t.gas_limit = 4712388

    def test(self):
        # Create wallet
        required_accounts = 2
        wa_1 = 1
        wa_2 = 2
        wa_3 = 3
        constructor_parameters = (
            [accounts[wa_1], accounts[wa_2], accounts[wa_3]],
            required_accounts
        )
        self.multisig_wallet = self.s.abi_contract(
            open('contracts/MultiSigWallet.sol').read(),
            language='solidity',
            constructor_parameters=constructor_parameters
        )
        # Validate deployment
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_1]))
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_2]))
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_3]))
        self.assertEqual(self.multisig_wallet.required(), required_accounts)
        # Create ABIs
        multisig_abi = self.multisig_wallet.translator
        # Send money to wallet contract
        deposit = 1000
        self.s.send(keys[wa_1], self.multisig_wallet.address, deposit)
        self.assertEqual(self.s.block.get_balance(self.multisig_wallet.address), 1000)
        # Add owner wa_4
        wa_4 = 4
        add_owner_data = multisig_abi.encode("addOwner", [accounts[wa_4]])
        # A third party cannot submit transactions
        self.assertRaises(TransactionFailed, self.multisig_wallet.submitTransaction, self.multisig_wallet.address, 0,
                          add_owner_data, 0, sender=keys[0])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [])
        # Only a wallet owner (in this case wa_1) can do this. Owner confirms transaction at the same time.
        transaction_hash = self.multisig_wallet.submitTransaction(self.multisig_wallet.address, 0, add_owner_data, 0,
                                                                  sender=keys[wa_1])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [transaction_hash])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [])
        self.assertTrue(self.multisig_wallet.confirmations(transaction_hash, accounts[wa_1]))
        # But owner wa_1 revokes confirmation
        self.multisig_wallet.revokeConfirmation(transaction_hash, sender=keys[wa_1])
        self.assertFalse(self.multisig_wallet.confirmations(transaction_hash, accounts[wa_1]))
        # He changes his mind, confirms again
        self.multisig_wallet.confirmTransaction(transaction_hash, sender=keys[wa_1])
        self.assertTrue(self.multisig_wallet.confirmations(transaction_hash, accounts[wa_1]))
        # Other owner wa_2 confirms and executes transaction at the same time as min sig are available
        self.assertFalse(self.multisig_wallet.transactions(transaction_hash)[4])
        self.multisig_wallet.confirmTransaction(transaction_hash, sender=keys[wa_2])
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_4]))
        # Transaction was executed
        self.assertTrue(self.multisig_wallet.transactions(transaction_hash)[4])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [transaction_hash])
        # Update required to 4
        update_required_data = multisig_abi.encode("updateRequired", [4])
        transaction_hash_2 = self.multisig_wallet.submitTransaction(self.multisig_wallet.address, 0,
                                                                    update_required_data, 0, sender=keys[wa_1])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [transaction_hash_2])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [transaction_hash])
        self.multisig_wallet.confirmTransaction(transaction_hash_2, sender=keys[wa_2])
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_4]))
        self.assertEqual(self.multisig_wallet.required(), required_accounts + 2)
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [transaction_hash, transaction_hash_2])
        # Delete owner wa_3. All parties have to confirm.
        remove_owner_data = multisig_abi.encode("removeOwner", [accounts[wa_3]])
        transaction_hash_3 = self.multisig_wallet.submitTransaction(self.multisig_wallet.address, 0, remove_owner_data,
                                                                    0, sender=keys[wa_1])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [transaction_hash_3])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(), [transaction_hash, transaction_hash_2])
        self.multisig_wallet.confirmTransaction(transaction_hash_3, sender=keys[wa_2])
        self.multisig_wallet.confirmTransaction(transaction_hash_3, sender=keys[wa_3])
        self.multisig_wallet.confirmTransaction(transaction_hash_3, sender=keys[wa_4])
        self.assertEqual(self.multisig_wallet.getPendingTransactions(), [])
        self.assertEqual(self.multisig_wallet.getExecutedTransactions(),
                         [transaction_hash, transaction_hash_2, transaction_hash_3])
        # Transaction was successfully processed
        self.assertEqual(self.multisig_wallet.required(), required_accounts + 1)
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_1]))
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_2]))
        self.assertTrue(self.multisig_wallet.isOwner(accounts[wa_4]))
