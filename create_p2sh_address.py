import argparse

from bitcoinutils.setup import setup
from bitcoinutils.keys import P2shAddress, PublicKey
from bitcoinutils.script import Script

'''
Mock public keys for testing
----------------------------
Pub Key 1: 03f69a95e6425186fe303b5e2d9cb22dd74747d053babc237f1505e6214d398217
Pub Key 2: 0324507ce2fcdb044cab092c044c63cefa4dff46aa189322f47a923de8f2e8144c
Pub Key 3: 02d21464d7339e58526680f8c7c20fd6946f72fd4717c82214b6d9ea9422d08287
'''

def main():
    setup('regtest')

    parser = argparse.ArgumentParser(description='Create and display a P2SH address consisting of exactly 3 Public Keys',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35))

    parser.add_argument('-pk1', type=str, metavar='Public_Key_#1', required=True, help='First Public key')
    parser.add_argument('-pk2', type=str, metavar='Public_Key_#2', required=True, help='Second Public key')
    parser.add_argument('-pk3', type=str, metavar='Public_Key_#3', required=True, help='Third Public key')

    args = parser.parse_args()

    # specify the 3 public keys
    pk1 = PublicKey.from_hex(args.pk1)
    pk2 = PublicKey.from_hex(args.pk2)
    pk3 = PublicKey.from_hex(args.pk3)

    redeem_script = Script(['OP_2', pk1.to_hex(), pk2.to_hex(), pk3.to_hex(), 'OP_3', 'OP_CHECKMULTISIG'])

    # 20-byte hash value of the redeem script
    p2sh_address = P2shAddress.from_script(redeem_script)
    
    print("\nP2SH address: %s" % p2sh_address.to_string())

    
if __name__ == "__main__":
    main()
    
