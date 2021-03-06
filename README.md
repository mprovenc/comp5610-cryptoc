## Abstract

The goal of this project is to build all the components of a simple cryptocurrency. Similar to the structure of Bitcoin, this cryptocurrency will function in the context of a peer-to-peer network and make use of blockchain technology to track and verify transactions. The goal of the project will be to allow users to join a peer-to-peer network, make secure cryptocurrency transactions between themselves and other nodes within the network, and accurately track the balance of any node within the network.

## Implementation

The implementation of such a cryptocurrency will include the following components:

- **Simple peer-to-peer network.** All transactions between users will take place in the context of a peer-to-peer network. Nodes will be able to join/leave the network. Though communications among nodes will be decentralized as is usual in peer-to-peer communications, a central server will be used for the purpose of tracking which nodes are currently in the network. The central server will also be responsible for distributing this information to other nodes in the network so that they can communicate among each other directly as peers.

- **Secure transactions using PKC.** Each node in the network will have an associated public/private key pair. Each node in the network will also know the public key of every other node in the network (the central server described in the last bullet point will behave like a certificate authority; it will be responsible for the safe, authenticated distribution of public keys in this network). Transactions broadcasted in the network will be encrypted with the private key of the sending node, which can then be decrypted by any other node using the public key of the sending node. This mechanism will be used to verify the identity of the sender.

- **Blockchain transaction capability.** Transactions that occur among nodes in this network will use blockchain technology. When a transaction occurs between two nodes in the network, this transaction will be broadcast to all nodes in the network. Upon being received by a node in the network, this transaction will then be added to a list of “unconfirmed transactions”. To determine when these unconfirmed transactions should be assembled into a block and added to the blockchain, a proof-of-work routine will be executed by each node. The node that completes the routine first will send a broadcast message suggesting that its block be added to the blockchain.

- **Globally distributed ledger.** Each node will store its own ledger with a list of all transactions that occur for each node within the network. As a security measure, transactions will include ledger information about the node from which they originated, to prove that the sending node has enough of a balance to make the transaction. This information will be verified by each node on the P2P network before the transaction is confirmed. 
