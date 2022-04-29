import argparse

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2pkhAddress, P2shAddress, PrivateKey, PublicKey
from bitcoinutils.script import Script
from bitcoinutils.proxy import NodeProxy

FEE = 2

class InvalidTransactionError(Exception): 
    __module__ = Exception.__module__


def main():
    setup('regtest')

    # proxy.loadwallet('my_wallet')
    
    parser = argparse.ArgumentParser(description='Spend all funds from P2SH address to P2PKH address',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35))

    parser.add_argument('-sk1', type=str, metavar='Private_Key_#1', required=True, help='First private key')
    parser.add_argument('-sk2', type=str, metavar='Private_Key_#2', required=True, help='Second private key')
    parser.add_argument('-pk', type=str, metavar='Public_Key', required=True, help='Public key')
    parser.add_argument('-p2pkh_address', type=str, metavar='P2PKH_Address', required=True, help='Valid P2PKH address to send the funds to')
    parser.add_argument('-p2sh_address', type=str, metavar='P2SH_Address', required=True, help='Valid P2SH address')

    parser.add_argument('-rpcuser', type=str, metavar='RPC_username', required=True, help='RPC username as defined in the .conf file')
    parser.add_argument('-rpcpass', type=str, metavar='RPC_password', required=True, help='RPC password as defined in the .conf file')

    args = parser.parse_args()

    proxy = NodeProxy(args.rpcuser, args.rpcpass).get_proxy() # lofos, 1234

    # Accept 2 private keys
    sk1 = PrivateKey(args.sk1) #('cQq6hbURR3KePybs6h9BjVXa9kLjd7QJiYwm3cLs6QXxaAveLHtA')
    sk2 = PrivateKey(args.sk2) #('cSK92CY29wDni3V7gT4kQLDqsy1FmRXEEt3kHtzGM5Puf2iSbpxC')

    # Accept 1 public key
    pk = PublicKey(args.pk) #('02d21464d7339e58526680f8c7c20fd6946f72fd4717c82214b6d9ea9422d08287')

    # recrate the redeem script
    redeem_script = Script(['OP_2', sk1.get_public_key().to_hex(), sk2.get_public_key().to_hex(),
                            pk.to_hex(), 'OP_3', 'OP_CHECKMULTISIG'])

    # accept p2sh address
    p2sh_addr = P2shAddress(args.p2sh_address) #('2MvrsM64GkuhAvFaxbrR25omMwdBko38GyH')

    # accept a p2pkh address to send funds to
    p2pkh_addr = P2pkhAddress(args.p2pkh_address) #('n1MUmxZihh16dcLHD4ZupPEaUVUTj99XoM')
    
    p2sh_unspent = proxy.listunspent(0, 0, [p2sh_addr.to_string()])

    if not p2sh_unspent:
        raise RuntimeError('There are no UTXO\'s currently associated with this P2SH address')

    print('=' * 60)
    utxo = list()
    for i, tx in enumerate(p2sh_unspent):
        # print(tx)
        if tx['amount'] > 0 and tx['safe']:
            utxo += [tx]
            print('%d. Found UTXO from P2SH address to spend funds with txid : %s (Amount=%.7f BTC)' %(i+1, tx['txid'], tx['amount']))
        else:
            raise RuntimeError('No UTXO\'s associated with that P2SH address')


    # calculate the fees and the amount to send
    tx_fee, amount_to_send = 0, 0
    txin = []
    for tx in utxo:
        raw_tx = proxy.decoderawtransaction(proxy.getrawtransaction(tx['txid']))
        tx_fee += raw_tx['size'] * FEE

        txin += [TxInput(tx['txid'], tx['vout'])]
        amount_to_send += to_satoshis(tx['amount'])

    print("=" * 60)  

    print('Total spendable amount aggregated from %d UTXO(s) associated with P2SH address: %.7f BTC' % (len(p2sh_unspent), amount_to_send/10e7))
    print('TX fee in satoshis: %.1f (%d sats/byte)' % (tx_fee, FEE))

    amount_to_send -= tx_fee
    
    print("=" * 60)
    print('Sending %ld satoshis (%.10f BTC) to P2PKH address (%s).Transaction fees amount to %d satoshis' 
                % (amount_to_send, amount_to_send/10e7, p2pkh_addr.to_string(), tx_fee))
    print("=" * 60)

    txout = TxOutput(amount_to_send, p2pkh_addr.to_script_pub_key())

    tx = Transaction(inputs=txin, outputs=[txout])

    unsigned_raw_tx = tx.serialize()
    print('\nRaw unsigned transaction: %s\n' % unsigned_raw_tx)
    print("=" * 60)

    sigs_1 = [sk1.sign_input(tx, i, redeem_script) for i in range(len(txin))]

    for sig, t in zip(sigs_1, tx.inputs):
        t.script_sig = Script([sig, redeem_script.to_hex()])
    
    part_signed_tx = tx.serialize()
    
    # print raw partially signed transaction 
    print("\nRaw partially signed transactions: %s\n" % part_signed_tx)
    print("=" * 60)

    signed_tx_2 = Transaction.from_raw(part_signed_tx)

    sigs_2 = [sk2.sign_input(signed_tx_2, i, redeem_script) for i in range(len(txin))]

    for sig1, sig2, t in zip(sigs_1, sigs_2, signed_tx_2.inputs):
        t.script_sig = Script(['OP_0', sig1, sig2, redeem_script.to_hex()])

    final_signed_tx = signed_tx_2.serialize()
    
    # print raw signed transaction ready to be broadcasted
    print("\nFinal raw signed transactions: %s\n" % final_signed_tx)
    print("=" * 71)

    print("Tx Id: %s" % signed_tx_2.get_txid())
    print("=" * 71)

    # confirm the validity of the transaction by performing a mempool acceptance test
    accepted = proxy.testmempoolaccept([final_signed_tx])[0]

    is_valid = False

    if accepted['allowed']:
        is_valid = True
        print()
        print("=" * 45)
        print('Transaction is valid, ready to be broadcasted', end='\n')
        print("=" * 45)
    else:
        raise InvalidTransactionError('Transaction is not valid therefore it won\'t be broadcasted')

    # broadcast tx 
    if is_valid:
        print()
        print("=" * 45)
        print('Transaction sent to the blockchain', end='\n')
        print("=" * 45)
        proxy.sendrawtransaction(final_signed_tx)


if __name__ == '__main__':
    main()
    
