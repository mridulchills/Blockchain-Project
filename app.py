from flask import Flask, jsonify, request, render_template
import hashlib
import time
from typing import List, Dict

app = Flask(__name__)

# Custom exceptions
class BlockchainException(Exception):
    pass

class InvalidTransactionError(BlockchainException):
    pass

class InvalidBlockError(BlockchainException):
    pass

class InsufficientAssetsError(BlockchainException):
    pass

# Block class representing each block in the blockchain
class Block:
    def __init__(self, index: int, previous_hash: str, timestamp: float, data: str):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{self.data}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"Block({self.index}, {self.data[:20]}..., {self.hash[:10]}...)"

# NFT representing property ownership
class PropertyNFT:
    def __init__(self, property_id: int, owner_name: str, property_value: float, property_location: str):
        self.property_id = property_id
        self.owner_name = owner_name
        self.property_value = property_value
        self.property_location = property_location
        self.is_for_sale = False  # Property is not listed for sale initially

    def __str__(self):
        status = "For Sale" if self.is_for_sale else "Not For Sale"
        return f"Property NFT - ID: {self.property_id}, Owner: {self.owner_name}, Value: {self.property_value}, Location: {self.property_location}, Status: {status}"

# Blockchain wallet to store NFTs
class Wallet:
    def __init__(self, owner: str):
        self.owner = owner
        self.nfts: List[PropertyNFT] = []  # List of NFTs (properties owned)

    def add_nft(self, nft: PropertyNFT):
        self.nfts.append(nft)

    def remove_nft(self, property_id: int) -> PropertyNFT:
        for nft in self.nfts:
            if nft.property_id == property_id:
                self.nfts.remove(nft)
                return nft
        raise InsufficientAssetsError(f"Property ID {property_id} not found in {self.owner}'s wallet.")

    def list_property_for_sale(self, property_id: int):
        for nft in self.nfts:
            if nft.property_id == property_id:
                nft.is_for_sale = True
                return nft
        raise InsufficientAssetsError(f"Property ID {property_id} not found in {self.owner}'s wallet.")

    def __str__(self):
        return f"{self.owner}'s Wallet: {[str(nft) for nft in self.nfts]}"

# Blockchain class for managing the chain of blocks and transactions
class Blockchain:
    def __init__(self):
        self.chain: List[Block] = [self.create_genesis_block()]
        self.pending_transactions: List[str] = []  # To hold pending transactions before mining
        self.wallets: Dict[str, Wallet] = {}  # Dictionary to store wallets of all users

    def create_genesis_block(self) -> Block:
        return Block(0, "0", time.time(), "Genesis Block")

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, block: Block):
        if not self.is_valid_new_block(block, self.get_latest_block()):
            raise InvalidBlockError("Attempted to add an invalid block to the chain")
        self.chain.append(block)

    def is_valid_new_block(self, new_block: Block, previous_block: Block) -> bool:
        if new_block.previous_hash != previous_block.hash:
            print(f"Invalid previous hash: {new_block.previous_hash} vs {previous_block.hash}")
            return False
        if new_block.hash != new_block.calculate_hash():
            print(f"Invalid hash calculation: {new_block.hash} vs {new_block.calculate_hash()}")
            return False
        return True

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            if not self.is_valid_new_block(current_block, previous_block):
                return False
        return True

    def create_wallet(self, owner: str):
        if owner in self.wallets:
            raise BlockchainException(f"Wallet for {owner} already exists.")
        self.wallets[owner] = Wallet(owner)

    def mint_property_nft(self, owner: str, property_id: int, property_value: float, property_location: str):
        if owner not in self.wallets:
            raise BlockchainException(f"Wallet for {owner} does not exist.")
        
        new_nft = PropertyNFT(property_id, owner, property_value, property_location)
        self.wallets[owner].add_nft(new_nft)
        self.pending_transactions.append(f"Minted property NFT {property_id} for {owner}")

    def transfer_property(self, from_owner: str, to_owner: str, property_id: int):
        if from_owner not in self.wallets or to_owner not in self.wallets:
            raise BlockchainException(f"Wallet for either {from_owner} or {to_owner} does not exist.")
        
        nft = self.wallets[from_owner].remove_nft(property_id)
        nft.owner_name = to_owner  # Update the NFT's owner
        nft.is_for_sale = False  # Mark as not for sale after transfer
        self.wallets[to_owner].add_nft(nft)

        self.pending_transactions.append(f"Transferred property NFT {property_id} from {from_owner} to {to_owner}")

    def list_property_for_sale(self, owner: str, property_id: int):
        if owner not in self.wallets:
            raise BlockchainException(f"Wallet for {owner} does not exist.")
        
        nft = self.wallets[owner].list_property_for_sale(property_id)
        self.pending_transactions.append(f"Listed property NFT {property_id} for sale by {owner}")

    def mine_pending_transactions(self):
        if not self.pending_transactions:
            raise BlockchainException("No transactions to mine")
        
        latest_block = self.get_latest_block()
        new_block_data = "\n".join(self.pending_transactions)
        new_block = Block(len(self.chain), latest_block.hash, time.time(), new_block_data)

        self.add_block(new_block)
        self.pending_transactions = []

    def print_chain(self):
        for block in self.chain:
            print(f"Block {block.index}: {block.data}, Hash: {block.hash}, Previous Hash: {block.previous_hash}")

    def print_wallets(self):
        for wallet in self.wallets.values():
            print(wallet)

    def print_properties_for_sale(self):
        print("\nProperties for Sale:")
        for wallet in self.wallets.values():
            for nft in wallet.nfts:
                if nft.is_for_sale:
                    print(nft)

# Blockchain instance for the app
land_registry = Blockchain()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    owner = request.form['owner']
    try:
        land_registry.create_wallet(owner)
        return jsonify({'status': 'success', 'message': f'Wallet for {owner} created.'})
    except BlockchainException as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/mint_property', methods=['POST'])
def mint_property():
    owner = request.form['owner']
    property_id = int(request.form['property_id'])
    property_value = float(request.form['property_value'])
    property_location = request.form['property_location']
    try:
        land_registry.mint_property_nft(owner, property_id, property_value, property_location)
        land_registry.mine_pending_transactions()
        return jsonify({'status': 'success', 'message': f'Property NFT {property_id} minted for {owner}.'})
    except BlockchainException as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/list_property_for_sale', methods=['POST'])
def list_property_for_sale():
    owner = request.form['owner']
    property_id = int(request.form['property_id'])
    try:
        land_registry.list_property_for_sale(owner, property_id)
        land_registry.mine_pending_transactions()
        return jsonify({'status': 'success', 'message': f'Property {property_id} listed for sale.'})
    except BlockchainException as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/transfer_property', methods=['POST'])
def transfer_property():
    from_owner = request.form['from_owner']
    to_owner = request.form['to_owner']
    property_id = int(request.form['property_id'])
    try:
        land_registry.transfer_property(from_owner, to_owner, property_id)
        land_registry.mine_pending_transactions()
        return jsonify({'status': 'success', 'message': f'Property {property_id} transferred from {from_owner} to {to_owner}.'})
    except BlockchainException as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_chain', methods=['GET'])
def get_chain():
    chain_data = [{'index': block.index, 'data': block.data, 'hash': block.hash, 'previous_hash': block.previous_hash} for block in land_registry.chain]
    return jsonify({'chain': chain_data})

@app.route('/get_wallets', methods=['GET'])
def get_wallets():
    wallets = {}
    for owner, wallet in land_registry.wallets.items():
        wallets[owner] = [str(nft) for nft in wallet.nfts]
    return jsonify(wallets)

if __name__ == '__main__':
    app.run(debug=True)
