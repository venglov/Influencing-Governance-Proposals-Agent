from forta_agent import Finding, FindingType, FindingSeverity
from src.config import BLOCKS_LEADING_UP_TO_THE_PROPOSAL, BLOCKS_AFTER_VOTE_CAST, VOTING_POWER_TH_HIGH, \
    VOTING_POWER_TH_MEDIUM


def get_severity(dif):
    if dif < VOTING_POWER_TH_MEDIUM:
        return FindingSeverity.Low
    elif dif < VOTING_POWER_TH_HIGH:
        return FindingSeverity.Medium
    else:
        return FindingSeverity.High


class InfluencingGovernanceProposalsFindings:

    @staticmethod
    def influencing_before_voting(proposal_id: str, voter: str, support, votes_, reason, dif) -> Finding:
        return Finding({
            'name': 'Uniswap Influencing Governance Proposals Alert',
            'description': f'Address {voter} casting a vote had a significant change in UNI balance '
                           f'in the {BLOCKS_LEADING_UP_TO_THE_PROPOSAL} blocks leading up '
                           f'to the proposal starting block number',
            'alert_id': 'UNI-GOV-INC',
            'type': FindingType.Suspicious,
            'severity': get_severity(dif),
            'metadata': {
                'proposalId': proposal_id,
                'voter': voter,
                'support': support,
                'votes': votes_,
                'reason': reason,
                'difference': dif
            }
        })

    @staticmethod
    def influencing_after_voting(proposal_id: str, voter: str, support, votes_, reason, dif) -> Finding:
        return Finding({
            'name': 'Uniswap Influencing Governance Proposals Alert',
            'description': f'Address {voter} casting a vote had a significant change in UNI balance '
                           f'in the {BLOCKS_AFTER_VOTE_CAST} blocks after the vote is cast',
            'alert_id': 'UNI-GOV-DEC',
            'type': FindingType.Suspicious,
            'severity': get_severity(dif),
            'metadata': {
                'proposalId': proposal_id,
                'voter': voter,
                'support': support,
                'votes': votes_,
                'reason': reason,
                'difference': dif
            }
        })

    @staticmethod
    def influencing_full(proposal_id: str, voter: str, support, votes_, reason, dif) -> Finding:
        return Finding({
            'name': 'Uniswap Influencing Governance Proposals Alert',
            'description': f'Address {voter} casting a vote had a significant increase in UNI balance '
                           f'in the {BLOCKS_AFTER_VOTE_CAST} blocks after the vote is cast and significant decrease '
                           f'after',
            'alert_id': 'UNI-GOV-FULL',
            'type': FindingType.Suspicious,
            'severity': FindingSeverity.Critical,
            'metadata': {
                'proposalId': proposal_id,
                'voter': voter,
                'support': support,
                'votes': votes_,
                'reason': reason,
                'difference': dif
            }
        })

    @staticmethod
    def new_proposal(proposal_id: str) -> Finding:
        return Finding({
            'name': 'Uniswap Proposal Created',
            'description': f'A new proposal with the id {proposal_id} was created.',
            'alert_id': 'UNI-GOV-INFO',
            'type': FindingType.Info,
            'severity': FindingSeverity.Low,
            'metadata': {
                'proposalId': proposal_id,
            }
        })
