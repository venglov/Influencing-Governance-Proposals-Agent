from forta_agent import Finding, FindingType, FindingSeverity
from src.config import BLOCKS_LEADING_UP_TO_THE_PROPOSAL, BLOCKS_AFTER_VOTE_CAST, VOTING_POWER_TH


class InfluencingGovernanceProposalsFindings:

    @staticmethod
    def influencing_before_voting(proposal_id: str, voter: str) -> Finding:
        return Finding({
            'name': 'Uniswap Influencing Governance Proposals Alert',
            'description': f'Address {voter} casting a vote had a significant change in UNI balance '
                           f'in the {BLOCKS_LEADING_UP_TO_THE_PROPOSAL} blocks leading up '
                           f'to the proposal starting block number',
            'alert_id': 'UNI-GOV-1',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.High,
            'metadata': {
                'proposalId': proposal_id,
                'voter': voter
            }
        })

    @staticmethod
    def influencing_after_voting(proposal_id: str, voter: str) -> Finding:
        return Finding({
            'name': 'Uniswap Influencing Governance Proposals Alert',
            'description': f'Address {voter} casting a vote had a significant change in UNI balance '
                           f'in the {BLOCKS_AFTER_VOTE_CAST} blocks after the vote is cast',
            'alert_id': 'UNI-GOV-2',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.High,
            'metadata': {
                'proposalId': proposal_id,
                'voter': voter
            }
        })

    @staticmethod
    def new_proposal(proposal_id: str) -> Finding:
        return Finding({
            'name': 'Uniswap Proposal Created Alert',
            'description': f'A new proposal with the id {proposal_id} was created.',
            'alert_id': 'UNI-GOV-3',
            'type': FindingType.Info,
            'severity': FindingSeverity.Low,
            'metadata': {
                'proposalId': proposal_id,
            }
        })
