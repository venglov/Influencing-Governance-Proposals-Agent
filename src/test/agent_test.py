import eth_abi
from eth_utils import keccak, encode_hex
from forta_agent import create_transaction_event, get_json_rpc_url
from src.agent import provide_handle_transaction
from web3 import Web3
from src.const import GOVERNOR_BRAVO_CONTRACT_ADDRESS, UNISWAP_CONTRACT_ADDRESS
from src.test.web3_mock import Web3Mock

web3 = Web3(Web3.HTTPProvider(get_json_rpc_url()))

VOTE_CAST = "VoteCast(address,uint256,uint8,uint256,string)"
PROPOSAL_CREATED = "ProposalCreated(uint256,address,address[],uint256[],string[],bytes[],uint256,uint256,string)"

CHECKPOINTS = "function checkpoints(address account, uint32 index) external view returns (uint32, uint96)"
NUM_CHECKPOINTS = "function numCheckpoints(address account) external view returns (uint32)"
DELEGATE_VOTES_CHANGED = "DelegateVotesChanged(address,uint256,uint256)"

VOTER = "0x1111111111111111111111111111111111111111"
PROPOSER = "0x2222222222222222222222222222222222222222"
PROPOSAL_ID = 1
checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300)]


# VoteCast(address,uint,uint8,uint,string) #
def vote_cast(id, votes):
    hash = keccak(text=VOTE_CAST)
    data = eth_abi.encode_abi(["uint256", "uint8", "uint256", "string"], [id, 1, votes, ""])
    data = encode_hex(data)
    address = eth_abi.encode_abi(["address"], [VOTER])
    address = encode_hex(address)
    topics = [hash, address]
    return {'topics': topics,
            'data': data,
            'address': GOVERNOR_BRAVO_CONTRACT_ADDRESS}


# ProposalCreated(uint,address,address[],uint[],string[],bytes[],uint,uint,string) #
def proposal_created(start, end, proposal_id):
    hash = keccak(text=PROPOSAL_CREATED)
    data = eth_abi.encode_abi(
        ["uint256", "address", "address[]", "uint256[]", "string[]", "bytes[]", "uint256", "uint256", "string"],
        [proposal_id, PROPOSER, [VOTER, PROPOSER], [1, 2, 3, 4, 5], ["1", "2"], [b'1', b'2'], start, end,
         "description"])
    data = encode_hex(data)
    topics = [hash]
    return {'topics': topics,
            'data': data,
            'address': GOVERNOR_BRAVO_CONTRACT_ADDRESS}


# DelegateVotesChanged(address,uint,uint) #
def delegate_votes_changed(old_power, new_power):
    hash = keccak(text=DELEGATE_VOTES_CHANGED)
    data = eth_abi.encode_abi(["uint256", "uint256"], [old_power, new_power])
    data = encode_hex(data)
    address = eth_abi.encode_abi(["address"], [VOTER])
    address = encode_hex(address)
    topics = [hash, address]
    return {'topics': topics,
            'data': data,
            'address': UNISWAP_CONTRACT_ADDRESS}


class TestInfluencingGovernanceProposals:
    def test_returns_influencing_before_finding(self):
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 150
            },
            'receipt': {
                'logs': [proposal_created(150, 250, 1)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        assert len(findings) == 1

        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 160
            },
            'receipt': {
                'logs': [vote_cast(1, 10300)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-1'), None)
        assert finding

    def test_returns_influencing_after_finding(self):
        checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300), (180, 100)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 180
            },
            'receipt': {
                'logs': [delegate_votes_changed(10300, 100)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-2'), None)
        assert finding

    def test_returns_zero_findings_if_voting_power_was_not_increased_before(self):
        checkpoints = [(100, 100), (120, 100), (140, 300), (160, 100)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 160
            },
            'receipt': {
                'logs': [vote_cast(1, 100)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        assert not findings

    def test_returns_zero_findings_if_voting_power_was_not_decreased_after(self):
        checkpoints = [(50300, 100), (50320, 100), (50340, 100), (50360, 100), (50380, 99)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 50350
            },
            'receipt': {
                'logs': [proposal_created(50350, 50450, 2)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        assert len(findings) == 1
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-3'), None)
        assert finding

        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 50360
            },
            'receipt': {
                'logs': [delegate_votes_changed(100, 99)]}
        })

        findings = provide_handle_transaction(w3)(tx_event)
        assert not findings
