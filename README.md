# **Influencing Governance Proposals Agent**

---

## Description

Governance proposals allow protocols to change to meet the evolving requirements of the DeFi ecosystem. Voting on these proposals occurs over a limited period of time when only those accounts that have been delegated votes may cast those votes in favor of or against the proposal. There is also a check to determine whether the delegated votes existed in the block number when the proposal was submitted.

This agent monitors proposals to the Uniswap Governance and the votes cast on those proposals. A finding is created if an address casting a vote had a significant change in UNI balance in the N blocks leading up to the proposal starting block number.
It also tracks balances in the M blocks after the vote is cast and creating a finding if the balance decreases.

The agent is separated into four threads:

1. First thread detects the `ProposalCreated(uint256,address,address[],uint256[],string[],bytes[],uint256,uint256,string)`
   events, add them to the database and emit an info-alert, that proposal was created.
2. Second thread detects `VoteCast(address,uint256,uint8,uint256,string)` events in the logs and emit an alert if there is an influencing before.
3. Third thread detects voting power decreasing through `DelegateVotesChanged(address,uint256,uint256)` events after the VoteCast and emit an alert if there is an influencing.
4. Fourth thread removes obsolete data from the database.

## Agent Flow
![Influencing-Agent-Flow.png](https://github.com/VVlovsky/Influencing-Governance-Proposals-Agent/blob/master/Influencing-Agent-Flow.png)

## Setup

You can specify your own values in the `config.py`:

```python
BLOCKS_LEADING_UP_TO_THE_PROPOSAL = 100
BLOCKS_AFTER_VOTE_CAST = 100
VOTING_POWER_TH_HIGH = 10000
VOTING_POWER_TH_MEDIUM = 5000
VOTING_POWER_TH_LOW = 1000
```

---

Due to the need to store information for a long time the agent uses asynchronous database.
This gives the advantage that even a restart or crash of the agent will not prevent him from discovering the vulnerability.
However, checking the same transactions multiple times in a row can cause a uniqueness error in the database. To get around this 
you need to remove the unique flag in `src/db/models.py` or add force drop_all in `src/db/controller.py`:
```python
await conn.run_sync(base.metadata.drop_all)
```

## Supported Chains

- Ethereum

## Alerts

- `UNI-GOV-INC`
  - Fired when a there is a significant change in UNI balance in the `N` blocks leading up to the proposal starting block number
  - Severity depends on the difference in UNI balance:
    - `Low` if difference is > 1k and < 5k 
    - `Medium` if difference is < 10k
    - `High` if difference is >= 10k
  - Type is always set to `Suspicious`
  - Metadata:
    - `proposalId` - the id of the proposal
    - `voter` - the address of the voter
    - `support` - the decision of the vote
    - `votes` - number of votes
    - `reason` - the reason
    - `difference` - change in UNI balance 

- `UNI-GOV-DEC`
  - Fired when a there is a significant change in UNI balance in the `M` blocks after the cast of the vote
  - Severity depends on the difference in UNI balance:
    - `Low` if difference is > 1k and < 5k 
    - `Medium` if difference is < 10k
    - `High` if difference is >= 10k
  - Type is always set to `Suspicious`
  - Metadata:
    - `proposalId` - the id of the proposal
    - `voter` - the address of the voter
    - `support` - the decision of the vote
    - `votes` - number of votes
    - `reason` - the reason
    - `difference` - change in UNI balance 

- `UNI-GOV-FULL`
  - Fired when a there is a significant change in UNI balance in the `N` blocks leading up to the proposal starting block number and `M` blocks after the cast of the vote
  - Severity is always set to `Critical`
  - Type is always set to `Suspicious`
  - Metadata:
    - `proposalId` - the id of the proposal
    - `voter` - the address of the voter
    - `support` - the decision of the vote
    - `votes` - number of votes
    - `reason` - the reason
    - `difference` - change in UNI balance 

- `UNI-GOV-INFO`
  - Fired when a new proposal was created
  - Severity is always set to `Low`
  - Type is always set to `Info`
  - Metadata:
    - `proposalId` - the id of the proposal

## Tests

There are 7 tests that should pass:

- `test_returns_influencing_before_finding()`
- `test_returns_zero_findings_if_voting_power_was_not_increased_before()`
- `test_returns_influencing_after_finding()`
- `test_returns_full_influencing_after_finding()`
- `test_returns_zero_findings_if_voting_power_was_not_decreased_after_and_increased_before()`
- `test_returns_zero_findings_if_address_is_wrong()`
- `test_returns_zero_findings_if_changes_are_out_of_the_check_range()`
