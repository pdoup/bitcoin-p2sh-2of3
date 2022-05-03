import argparse
import logging

from bitcoinutils.setup import setup
from bitcoinutils.utils import to_satoshis
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2pkhAddress, P2shAddress, PrivateKey, PublicKey
from bitcoinutils.script import Script
from bitcoinutils.proxy import NodeProxy
from enum import Enum

MIN_CONF = 0


class InvalidTransactionError(Exception):
    __module__ = Exception.__module__


class FeeRate(Enum):
    '''
    Testnet fee rates (as of 03/05/22) from : https://live.blockcypher.com/btc-testnet/ 
    each value is the BTC amount per KB        
    '''
    HIGH = 0.00078   # high priority (1-2 blocks)
    MEDIUM = 0.00052  # medium priority (3-6 blocks)
    LOW = 0.00029    # low priority (7+ blocks)


def main():
    setup('regtest')

    logging.basicConfig(
        format='[%(levelname)s] %(asctime)s : %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description='Spend all funds from a 2-of-3 P2SH address to P2PKH address',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35))

    parser.add_argument('-sk1', type=str, metavar='Private_Key_#1',
                        required=True, help='First private key')
    parser.add_argument('-sk2', type=str, metavar='Private_Key_#2',
                        required=True, help='Second private key')
    parser.add_argument('-pk', type=str, metavar='Public_Key',
                        required=True, help='Public key')
    parser.add_argument('-p2pkh_address', type=str, metavar='P2PKH_Address',
                        required=True, help='Valid P2PKH address to send the funds to')
    parser.add_argument('-p2sh_address', type=str, metavar='P2SH_Address',
                        required=True, help='Valid P2SH address')
    parser.add_argument('-rpcuser', type=str, metavar='RPC_username',
                        required=True, help='RPC username as defined in the .conf file')
    parser.add_argument('-rpcpass', type=str, metavar='RPC_password',
                        required=True, help='RPC password as defined in the .conf file')
    parser.add_argument('--log-level', type=str, metavar='log_level', nargs='?',
                        default='INFO', choices=('DEBUG', 'INFO', 'WARN', 'ERROR'),
                        required=False, help='Sets the log level {}'.format({'DEBUG', 'INFO', 'WARN', 'ERROR'}), 
                        dest='log_level')
    
    args = parser.parse_args()

    logger.setLevel(args.log_level)

    # initialize proxy - we'll be needing this to query our local bitcoin node
    proxy = NodeProxy(args.rpcuser, args.rpcpass).get_proxy()

    # accept 2 private keys
    sk1 = PrivateKey(args.sk1)
    sk2 = PrivateKey(args.sk2)

    # accept 1 public key
    pk = PublicKey(args.pk)

    # recrate the redeem script
    redeem_script = Script(['OP_2', sk1.get_public_key().to_hex(), sk2.get_public_key().to_hex(),
                            pk.to_hex(), 'OP_3', 'OP_CHECKMULTISIG'])

    # accept p2sh address
    p2sh_addr = P2shAddress(args.p2sh_address)

    # check if there is a mismatch between the P2SH address provided and the one we can recreate based on the user's input
    if p2sh_addr.to_string() != P2shAddress.from_script(redeem_script).to_string():
        raise ValueError(
            'P2SH address provided cannot be derived from the public keys provided')

    # accept a p2pkh address to send funds to
    p2pkh_addr = P2pkhAddress(args.p2pkh_address)

    # determine the total amount of blocks in the chain
    n_blocks = proxy.getblockcount()
    
    # also probe the mempool to check for any txs not in blocks yet
    n_mempool = proxy.getmempoolinfo()['size']
    
    # now we can retrieve the total number of transactions in the blockchain + mempool
    total_txs = sum([proxy.getblockstats(block, ['txs'])['txs']
                    for block in range(1, n_blocks)])
    logger.info(
        'Found {} transactions in the blockchain'.format(total_txs))
    
    logger.info('Found %ld transactions in the mempool', n_mempool)
    
    # list all transactions in the blockchain
    all_txs = proxy.listtransactions('*', total_txs + n_mempool, 0, True)

    # filter all of the txs above to keep just the ones that involve the P2SH address
    p2sh_txs = [*filter(lambda tx: tx['address'] ==
                        p2sh_addr.to_string(), all_txs)]

    logger.info(
        '{} transactions concerning the given P2SH address'.format(len(p2sh_txs)))

    p2sh_utxo = []
    amount_to_send = 0.

    '''
    Iterate over all p2sh_txs and add them as inputs to the tx we'll construct later.
    Also make sure that these txs are incoming to that address and have at least MIN_CONF confirmations.
    For the sake of this assignment we'll accept them even if they have 0 confirmations (at least in mempool).
    '''
    for tx in p2sh_txs:
        # sanity check to make sure that the tx is not already spent
        if not proxy.gettxout(tx['txid'], tx['vout']):
            logger.warning('tx [{}] already spent'.format(tx['txid']))
            continue
        if int(tx['confirmations']) >= MIN_CONF and tx['category'] == 'send':
            tx_in = TxInput(tx['txid'], tx['vout'])
            logger.info(
                '*Found UTXO with {0:.8f} tBTC, TXID : [{1}]'.format(abs(tx['amount']), tx['txid']))

            p2sh_utxo += [tx_in]
            amount_to_send += abs(float(tx['amount']))

    if not p2sh_utxo:
        raise RuntimeError(
            'No UTXO\'s currently associated with that P2SH address')

    # say we want our transaction to have a high priority
    fee_rate = FeeRate.HIGH
    PRICE_PER_BYTE = fee_rate.value / 1024

    # calculate fees using this formula : (n_inputs * 148 + n_outputs * 34 + 10) * price_per_byte
    tx_fee = (len(p2sh_utxo) * 148 + 1 * 34 + 10) * PRICE_PER_BYTE

    logger.info('Total spendable amount aggregated from {0} UTXO(s) associated with P2SH address: {1:.8f} tBTC'.format(
        len(p2sh_utxo), amount_to_send))
    logger.info('TX fee in satoshis: {0} (Fee Rate is {1:.8f} tBTC/KB)'.format(
        to_satoshis(tx_fee), fee_rate.value))

    '''
    Deduct calculated fees from our initial amount.
    Difference between (total_inputs - total_outputs) is the fee since all inputs must be spent completely.
    '''
    amount_to_send -= tx_fee

    logger.info('Sending {0} satoshis ({1:.8f} BTC) to P2PKH address [{2}]'.format(
        to_satoshis(amount_to_send), amount_to_send, p2pkh_addr.to_string()))

    # construct the tx output by specifying the amount to send and locking them to the P2PKH address provided
    txout = TxOutput(to_satoshis(amount_to_send),
                     p2pkh_addr.to_script_pub_key())

    # construct the transaction with N inputs (N >= 1) and 1 output
    tx = Transaction(inputs=p2sh_utxo, outputs=[txout])

    unsigned_raw_tx = tx.serialize()
    print("=" * 60)
    print('\nRaw unsigned transaction: %s\n' % unsigned_raw_tx)
    print("=" * 60)

    # sign each of the inputs using the 2 private private keys
    # we need at least 2 of the 3 parties to sign the inputs otherwise the funds cannot be transferred
    for tx_idx, txin in enumerate(p2sh_utxo):
        sig1 = sk1.sign_input(tx, tx_idx, redeem_script)
        sig2 = sk2.sign_input(tx, tx_idx, redeem_script)

        # add OP_0 in unlocking script due to a bug in multisig scripts
        txin.script_sig = Script(['OP_0', sig1, sig2, redeem_script.to_hex()])

    final_signed_tx = tx.serialize()

    # display raw signed transaction ready to be broadcasted
    print("\nRaw signed transaction: %s\n" % final_signed_tx)
    print("=" * 71)

    # display the transaction id
    print("Tx ID: %s" % tx.get_txid())
    print("=" * 71)

    # confirm the validity of the transaction by performing a mempool acceptance test
    response_status = proxy.testmempoolaccept([final_signed_tx])[0]

    if response_status['allowed']:
        logger.info('Transaction is valid, ready to be broadcasted')
    else:
        raise InvalidTransactionError('Transaction is not valid therefore it won\'t be broadcasted : {}'.format(
            response_status["reject-reason"]))

    # broadcast tx once we established its validity
    tx_sent = proxy.sendrawtransaction(final_signed_tx)
    if tx_sent:
        logger.info('Transaction sent to the blockchain')
    else:
        logger.error('Transaction couldn\'t be broadcasted')


if __name__ == '__main__':
    main()
