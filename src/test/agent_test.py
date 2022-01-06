import eth_abi
from eth_utils import keccak, encode_hex
from forta_agent import create_transaction_event, get_json_rpc_url
from src.agent import provide_handle_transaction, reset_inited
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


# VoteCast(address,uint,uint8,uint,string) #
def vote_cast(id, votes, address_=GOVERNOR_BRAVO_CONTRACT_ADDRESS):
    hash = keccak(text=VOTE_CAST)
    data = eth_abi.encode_abi(["uint256", "uint8", "uint256", "string"], [id, 1, votes, ""])
    data = encode_hex(data)
    address = eth_abi.encode_abi(["address"], [VOTER])
    address = encode_hex(address)
    topics = [hash, address]
    return {'topics': topics,
            'data': data,
            'address': address_}


# ProposalCreated(uint,address,address[],uint[],string[],bytes[],uint,uint,string) #
def proposal_created(start, end, proposal_id, address_=GOVERNOR_BRAVO_CONTRACT_ADDRESS):
    hash = keccak(text=PROPOSAL_CREATED)
    data = eth_abi.encode_abi(
        ["uint256", "address", "address[]", "uint256[]", "string[]", "bytes[]", "uint256", "uint256", "string"],
        [proposal_id, PROPOSER, [VOTER, PROPOSER], [1, 2, 3, 4, 5], ["1", "2"], [b'1', b'2'], start, end,
         "description"])
    data = encode_hex(data)
    topics = [hash]
    return {'topics': topics,
            'data': data,
            'address': address_}


# DelegateVotesChanged(address,uint,uint) #
def delegate_votes_changed(old_power, new_power, address_=UNISWAP_CONTRACT_ADDRESS):
    hash = keccak(text=DELEGATE_VOTES_CHANGED)
    data = eth_abi.encode_abi(["uint256", "uint256"], [old_power, new_power])
    data = encode_hex(data)
    address = eth_abi.encode_abi(["address"], [VOTER])
    address = encode_hex(address)
    topics = [hash, address]
    return {'topics': topics,
            'data': data,
            'address': address_}


class TestInfluencingGovernanceProposals:
    def test_returns_influencing_before_finding(self):
        reset_inited()
        checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300)]
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

        findings = provide_handle_transaction(w3, test=True)(tx_event)
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

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-INC'), None)
        assert finding

    def test_returns_zero_findings_if_voting_power_was_not_increased_before(self):
        reset_inited()
        checkpoints = [(100, 10300), (120, 10300), (140, 10300), (160, 10300)]
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
        provide_handle_transaction(w3, test=True)(tx_event)

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

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings

    def test_returns_decreasing_influencing_after_finding(self):
        reset_inited()
        self.test_returns_zero_findings_if_voting_power_was_not_increased_before()
        checkpoints = [(100, 10300), (120, 10300), (140, 10300), (160, 10300), (180, 100)]
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

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-DEC'), None)
        assert finding

    def test_returns_full_influencing_after_finding(self):
        reset_inited()
        self.test_returns_influencing_before_finding()
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

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        finding = next((x for x in findings if x.alert_id == 'UNI-GOV-FULL'), None)
        assert finding

    def test_returns_zero_findings_if_voting_power_was_not_decreased_after_and_increased_before(self):
        reset_inited()
        checkpoints = [(100, 10300), (120, 10300), (140, 10300), (160, 10300), (180, 10250)]
        w3 = Web3Mock(checkpoints)
        self.test_returns_zero_findings_if_voting_power_was_not_increased_before()

        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 180
            },
            'receipt': {
                'logs': [delegate_votes_changed(10300, 10250)]}
        })
        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings

    def test_returns_zero_findings_if_address_is_wrong(self):
        reset_inited()
        checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': "0x12345123451234512345",
                'hash': "0"
            },
            'block': {
                'number': 150
            },
            'receipt': {
                'logs': [proposal_created(150, 250, 1, address_="0x12345123451234512345")]}
        })

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings

        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': "0x12345123451234512345",
                'hash': "0"
            },
            'block': {
                'number': 160
            },
            'receipt': {
                'logs': [vote_cast(1, 10300, address_="0x12345123451234512345")]}
        })

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings

    def test_returns_zero_findings_if_changes_are_out_of_the_check_range(self):
        reset_inited()
        checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300), (300, 10300)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 290
            },
            'receipt': {
                'logs': [proposal_created(290, 310, 1)]}
        })

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert len(findings) == 1

        tx_event = create_transaction_event({
            'transaction': {
                'from': VOTER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 300
            },
            'receipt': {
                'logs': [vote_cast(1, 10300)]}
        })

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings

        checkpoints = [(100, 100), (120, 100), (140, 10300), (160, 10300), (300, 10300), (450, 100)]
        w3 = Web3Mock(checkpoints)
        tx_event = create_transaction_event({
            'transaction': {
                'from': PROPOSER,
                'to': UNISWAP_CONTRACT_ADDRESS,
                'hash': "0"
            },
            'block': {
                'number': 450
            },
            'receipt': {
                'logs': [delegate_votes_changed(10300, 100)]}
        })

        findings = provide_handle_transaction(w3, test=True)(tx_event)
        assert not findings
