# **Influencing Governance Proposals Agent**

---

## Description

Governance proposals allow protocols to change to meet the evolving requirements of the DeFi ecosystem. Voting on these proposals occurs over a limited period of time when only those accounts that have been delegated votes may cast those votes in favor of or against the proposal. There is also a check to determine whether the delegated votes existed in the block number when the proposal was submitted.

This agent monitors proposals to the Uniswap Governance and the votes cast on those proposals. A finding is created if an address casting a vote had a significant change in UNI balance in the N blocks leading up to the proposal starting block number.
It also tracks balances in the M blocks after the vote is cast and creating a finding if the balance decreases.

## Setup

You can specify your own values in the `config.py`:

```python
BLOCKS_LEADING_UP_TO_THE_PROPOSAL = 44800
BLOCKS_AFTER_VOTE_CAST = 44800
VOTING_POWER_TH = 10000
```

---

Due to the need to store information for a long time the agent uses asynchronous database.
This gives the advantage that even a restart or crash of the agent will not prevent him from discovering the vulnerability.
However, multiple repetitions of the tests will provoke a key uniqueness error. So in the development mode to prevent
this you need to uncomment the line number 24 in the `src/db/controller.py`:
```python
await conn.run_sync(base.metadata.drop_all)
```
Note that you should disable this line for the production

## Supported Chains

- Ethereum

## Alerts

- `UNI-GOV-1`
  - Fired when a there is a significant change in UNI balance in the `N` blocks leading up to the proposal starting block number
  - Severity is always set to `High`
  - Type is always set to `Suspicious`
  - Metadata:
    - `proposalId` - the id of the proposal
    - `voter` - the address of the voter

- `UNI-GOV-2`
  - Fired when a there is a significant change in UNI balance in the `M` blocks after the cast of the vote
  - Severity is always set to `High`
  - Type is always set to `Suspicious`
  - Metadata:
    - `proposalId` - the id of the proposal
    - `voter` - the address of the voter

- `UNI-GOV-3`
  - Fired when a new proposal was created
  - Severity is always set to `Low`
  - Type is always set to `Info`
  - Metadata:
    - `proposalId` - the id of the proposal

## Tests

There are 4 test that should pass:

- `test_returns_influencing_before_finding()`
- `test_returns_influencing_after_finding()`
- `test_returns_zero_findings_if_voting_power_was_not_increased_before()`
- `test_returns_zero_findings_if_voting_power_was_not_decreased_after()`
