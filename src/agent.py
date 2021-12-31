import asyncio
import json
import forta_agent
from forta_agent import get_json_rpc_url
from web3 import Web3
from src.const import UNISWAP_CONTRACT_ADDRESS, GOVERNOR_BRAVO_CONTRACT_ADDRESS
from src.db.config import config
from src.db.controller import init_async_db
from src.utils import extract_argument
from src.config import BLOCKS_LEADING_UP_TO_THE_PROPOSAL, BLOCKS_AFTER_VOTE_CAST, VOTING_POWER_TH
from src.findings import InfluencingGovernanceProposalsFindings

inited = False  # Initialization Pattern
web3 = Web3(Web3.HTTPProvider(get_json_rpc_url()))
with open("./src/ABI/governor_bravo_abi.json", 'r') as abi_file:  # get abi from the file
    governor_bravo_abi = json.load(abi_file)

with open("./src/ABI/uniswap_abi.json", 'r') as abi_file:  # get abi from the file
    uniswap_abi = json.load(abi_file)

# "event VoteCast(address indexed voter, uint proposalId, uint8 support, uint votes, string reason)" in the json format
vote_cast_abi = next((x for x in governor_bravo_abi if x.get('name', "") == "VoteCast"), None)
# "event ProposalCreated(uint id, address proposer, address[] targets, uint[] values, string[] signatures,
# bytes[] calldatas, uint startBlock, uint endBlock, string description)" in the json format
proposal_created_abi = next((x for x in governor_bravo_abi if x.get('name', "") == "ProposalCreated"), None)
# "function checkpoints(address account, uint32 index) external view returns (uint32, uint96)" in the json format
checkpoints_abi = next((x for x in uniswap_abi if x.get('name', "") == "checkpoints"), None)
# "function numCheckpoints(address account) external view returns (uint32)" in the json format
num_checkpoints_abi = next((x for x in uniswap_abi if x.get('name', "") == "numCheckpoints"), None)
# "event DelegateVotesChanged(address indexed delegate, uint previousBalance, uint newBalance)" in the json format
delegate_votes_changed_abi = next((x for x in uniswap_abi if x.get('name', "") == "DelegateVotesChanged"), None)


async def detect_proposal_initialization(transaction_event: forta_agent.transaction_event.TransactionEvent):
    """
    This function detects when a new proposal was created.
    :param transaction_event: forta_agent.transaction_event.TransactionEvent
    :return: findings: list
    """
    findings = []
    proposals = config.get_proposals()  # get proposals table from the db
    # get all proposal created events from the log
    for event in transaction_event.filter_log(json.dumps(proposal_created_abi), GOVERNOR_BRAVO_CONTRACT_ADDRESS):
        id_ = extract_argument(event, 'id')
        start = extract_argument(event, 'startBlock')
        end = extract_argument(event, 'endBlock')
        # add the proposal to the db
        await proposals.paste_row({
            'proposal_id': id_, 'start_block': start, 'end_block': end,
        })
        findings.append(InfluencingGovernanceProposalsFindings.new_proposal(id_))
    await proposals.commit()
    return findings


async def detect_cast_vote(transaction_event: forta_agent.transaction_event.TransactionEvent, w3):
    """
    This function detects CastVote events in the logs and emit an alert if there is an influencing before
    :param transaction_event: forta_agent.transaction_event.TransactionEvent
    :param w3: web3 object, it was added here to be able to insert web3 mock and test the function
    :return: findings: list
    """
    findings = []
    proposals = config.get_proposals()  # get proposals table from the db
    votes = config.get_votes()  # get votes table from the db
    contract = w3.eth.contract(address=Web3.toChecksumAddress(UNISWAP_CONTRACT_ADDRESS),
                               abi=[checkpoints_abi, num_checkpoints_abi])
    # get all CastVote events from the log
    for event in transaction_event.filter_log(json.dumps(vote_cast_abi), GOVERNOR_BRAVO_CONTRACT_ADDRESS):
        voter = extract_argument(event, "voter")
        proposal_id = extract_argument(event, "proposalId")
        support = extract_argument(event, "support")
        votes_ = extract_argument(event, "votes")
        reason = extract_argument(event, "reason")

        # add this vote to the db
        await votes.paste_row(
            {'voter': voter, 'block_number': transaction_event.block_number, 'proposal_id': proposal_id,
             'support': support, 'votes': votes_, 'reason': reason})
        await votes.commit()

        # get the amount of checkpoints of the current voter
        num_checkpoints = contract.functions.numCheckpoints(account=voter).call(transaction_event.block_number)
        if num_checkpoints == 0 or not num_checkpoints:
            continue

        # get his last voting power
        last_check_block, current_voting_power = contract.functions.checkpoints(account=voter,
                                                                                index=(num_checkpoints - 1)).call(
            transaction_event.block_number)

        # get information about this proposal from the db
        proposal = await proposals.get_row_by_criteria({'proposal_id': proposal_id})
        if not proposal:
            continue  # skip if it is unknown

        proposal_start_block = proposal.start_block

        if last_check_block < proposal_start_block - BLOCKS_LEADING_UP_TO_THE_PROPOSAL:
            continue  # skip if last checkpoint is too old

        target_block = proposal_start_block - BLOCKS_LEADING_UP_TO_THE_PROPOSAL  # get the minimal block to check

        # check all checkpoints which is bigger than minimal block
        for i in range(num_checkpoints - 1, 0, -1):
            block_at_i, voting_power_at_i = \
                contract.functions.checkpoints(account=voter,
                                               index=i).call(transaction_event.block_number)
            if block_at_i < target_block:
                break
            # emit an alert if difference is bigger than th
            if current_voting_power - voting_power_at_i > VOTING_POWER_TH:
                findings.append(InfluencingGovernanceProposalsFindings.influencing_before_voting(proposal_id, voter))
                break

    return findings


async def detect_voting_power_decrease_after_cast(transaction_event: forta_agent.transaction_event.TransactionEvent):
    """
    This function detects voting power decreasing after the VoteCast and emit an alert if there is an influencing
    :param transaction_event: forta_agent.transaction_event.TransactionEvent
    :return: findings: list
    """
    findings = []
    votes = config.get_votes()  # get votes from the db

    # get all DelegateVotesChanged events from the log
    for event in transaction_event.filter_log(json.dumps(delegate_votes_changed_abi), UNISWAP_CONTRACT_ADDRESS):
        delegate = extract_argument(event, "delegate")  # delegate is an address whose balance has been changed
        new_balance = extract_argument(event, "newBalance")
        known_votes = await votes.get_all_rows()

        # check if this address exist in our db
        if delegate in [ended_vote.voter for ended_vote in known_votes]:
            vote = await votes.get_row_by_criteria({'voter': delegate})

            # compare his voting power in the moment of the cast and current; emit an alert if the difference is bigger
            # than th
            if (vote.votes - new_balance) > VOTING_POWER_TH:
                findings.append(
                    InfluencingGovernanceProposalsFindings.influencing_after_voting(vote.proposal_id, delegate))

    return findings


async def clear_db(transaction_event: forta_agent.transaction_event.TransactionEvent):
    """
    This function deletes old proposal and votes from the db
    :param transaction_event: forta_agent.transaction_event.TransactionEvent
    :return: []
    """
    votes = config.get_votes()
    proposals = config.get_proposals()
    await votes.delete_old_votes(transaction_event.block_number, BLOCKS_AFTER_VOTE_CAST)
    await proposals.delete_old_proposals(transaction_event.block_number, BLOCKS_AFTER_VOTE_CAST)
    await votes.commit()
    await proposals.commit()
    return []


async def main(transaction_event: forta_agent.transaction_event.TransactionEvent, w3):
    """
    This function is used to start detect-functions in the different threads and then gather the findings
    """
    global inited
    if not inited:
        proposals_table, votes_table = await init_async_db()
        config.set_tables(proposals_table, votes_table)
        inited = True

    return await asyncio.gather(
        detect_proposal_initialization(transaction_event),
        detect_cast_vote(transaction_event, w3),
        detect_voting_power_decrease_after_cast(transaction_event),
        clear_db(transaction_event)
    )


def provide_handle_transaction(w3):
    def handle_transaction(transaction_event: forta_agent.transaction_event.TransactionEvent) -> list:
        return [finding for findings in asyncio.run(main(transaction_event, w3)) for finding in findings]

    return handle_transaction


real_handle_transaction = provide_handle_transaction(web3)


def handle_transaction(transaction_event: forta_agent.transaction_event.TransactionEvent):
    return real_handle_transaction(transaction_event)
