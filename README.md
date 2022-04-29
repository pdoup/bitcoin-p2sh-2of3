# bitcoin-p2sh-2of3

### **Data & Web Science MSc Program**
### *Decentralized Technologies Course - Assignment 1, 2022, Bitcoin*

For this assignment you will need to implement two scripts using `Python 3` and any
additional library of your choice (bitcoin-utils is highly recommended though).
The first one will create a `P2SH` Bitcoin address that implements a `MULTISIG` scheme,
where all funds sent to it should be locked until 2 out of 3 potential signers sign a
transaction to move the funds elsewhere.
The second program will allow spending all funds from this `P2SH` address.
Both programs should:
* use regtest/testnet
* assume a local Bitcoin regtest/testnet node is running

### The first program should:

- [ ] accept 3 public keys for the purpose of creating the `P2SH` address that will
- [ ] implement a `2-of-3 MULTISIG` scheme
- [ ] display the `P2SH` address

---

### The second program should:

- [ ] accept 2 private keys (used to sign transactions) and 1 public key (to recreate the
redeem script as above – the other two public keys may be derived from the
provided private keys)
- [ ] accept a `P2SH` address to get the funds from (the one created by the first script)
- [ ] accept a `P2PKH` address to send the funds to
- [ ] check if the `P2SH` address has any `UTXO`s to get funds from
- [ ] calculate the appropriate fees with respect to the size of the transaction
- [ ] send all funds that the `P2SH` address received to the `P2PKH` address provided
- [ ] display the raw unsigned transaction
- [ ] sign the transaction
- [ ] display the raw signed transaction
- [ ] display the transaction id
- [ ] verify that the transaction is valid and will be accepted by the Bitcoin nodes
- [ ] if the transaction is valid, send it to the blockchain

### ***Notes***
1. there is some repetition between the 2 programs; this is fine[^1].
2. you may test your scripts by sending some funds to the P2SH address you created
3. you may query the local Bitcoin testnet/regtest node using the JSON-RPC interface
you may query an external API for the currently accepted fees/byte
4. the P2SH address might have received funds from multiple transactions. Create an
initial version of your script where it handles a single known transaction. Expand it
to using multiple unknown transactions later.
5. when dealing with multiple inputs, you will need to sign all of them
6. try implementing a 1-of-3 MULTISIG scheme as a first step
7. you are expected to manually construct the Bitcoin locking/unlocking script for the
MULTISIG transactions, using the appropriate OP_codes. If the programming
libraries you are using have functionality to automatically create such transactions,
do not use them (it will be penalized)
8. for the sake of simplicity, the 2 required private keys that are needed for signing
the transaction in the second program can be provided at the same time and
transactions can be signed with both signatures within the same program,
although obviously this would never happen in a real world setting
9. you will submit a single compressed file (zip or tar.gz) that contains the Python
source code. It should include a text file with detailed instructions on how to run
your programs
10. Also include a `requirements.txt` file that will specify any extra Python libraries you
have used. You can easily create such a file using the following command in your
Python virtual environment:
```$ pip freeze > requirements.txt```
11. the source code is your main submission and it should contain everything you
want to share. It should include detailed comments and everything else you think
we should be aware of
