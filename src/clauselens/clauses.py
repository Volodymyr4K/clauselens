"""Registry of clause types ClauseLens extracts.

14 of CUAD's 41 categories, selected for (a) enough annotated examples in the
dataset for statistically meaningful per-type metrics (rarest kept type:
Non-Compete, 119 contracts; rarest dropped: Source Code Escrow, 13) and
(b) business value for risk review. Descriptions are the official CUAD
annotation guidelines, so the model is asked the same question the human
annotators answered.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClauseType:
    key: str            # stable snake_case id used in code, prompts and eval
    cuad_name: str      # exact category name in CUAD question text
    description: str    # official CUAD annotation guideline
    risk: bool          # surfaced in the risk-flagging report
    # metadata clauses live in the preamble and signature block; extracting
    # them from every chunk floods precision with references like "Company"
    header: bool = False
    # extraction hint appended to the CUAD description where the guideline
    # alone systematically misleads the model (diagnosed on train misses)
    hint: str = ""


CLAUSE_TYPES: list[ClauseType] = [
    ClauseType(
        "document_name", "Document Name",
        "The name of the contract", risk=False, header=True,
        hint="Quote the title as stated at the top of the document, not later "
             "references like \"this Agreement\"."),
    ClauseType(
        "parties", "Parties",
        "The two or more parties who signed the contract", risk=False, header=True,
        hint="Quote the legal entity names and their defined aliases from the "
             "preamble or signature block only — not later references to a party "
             "by its alias."),
    ClauseType(
        "agreement_date", "Agreement Date",
        "The date of the contract", risk=False, header=True),
    ClauseType(
        "governing_law", "Governing Law",
        "Which state/country's law governs the interpretation of the contract?",
        risk=False),
    ClauseType(
        "expiration_date", "Expiration Date",
        "On what date will the contract's initial term expire?", risk=False,
        hint="Term/duration provisions count even when no calendar date is "
             "given, e.g. \"an initial term of five (5) years\"."),
    ClauseType(
        "anti_assignment", "Anti-Assignment",
        "Is consent or notice required of a party if the contract is assigned to "
        "a third party?", risk=True),
    ClauseType(
        "cap_on_liability", "Cap On Liability",
        "Does the contract include a cap on liability upon the breach of a party's "
        "obligation? This includes time limitation for the counterparty to bring "
        "claims or maximum amount for recovery.", risk=True),
    ClauseType(
        "uncapped_liability", "Uncapped Liability",
        "Is a party's liability uncapped upon the breach of its obligation in the "
        "contract? This also includes uncap liability for a particular type of "
        "breach such as IP infringement or breach of confidentiality obligation.",
        risk=True),
    ClauseType(
        "license_grant", "License Grant",
        "Does the contract contain a license granted by one party to its "
        "counterparty?", risk=True),
    ClauseType(
        "audit_rights", "Audit Rights",
        "Does a party have the right to audit the books, records, or physical "
        "locations of the counterparty to ensure compliance with the contract?",
        risk=True),
    ClauseType(
        "termination_for_convenience", "Termination For Convenience",
        "Can a party terminate this contract without cause (solely by giving a "
        "notice and allowing a waiting period to expire)?", risk=True),
    ClauseType(
        "exclusivity", "Exclusivity",
        "Is there an exclusive dealing commitment with the counterparty? This "
        "includes a commitment to procure all \"requirements\" from one party of "
        "certain technology, goods, or services or a prohibition on licensing or "
        "selling technology, goods or services to third parties, or a prohibition "
        "on collaborating or working with other parties), whether during the "
        "contract or after the contract ends (or both).", risk=True),
    ClauseType(
        "renewal_term", "Renewal Term",
        "What is the renewal term after the initial term expires? This includes "
        "automatic extensions and unilateral extensions with prior notice.",
        risk=True),
    ClauseType(
        "non_compete", "Non-Compete",
        "Is there a restriction on the ability of a party to compete with the "
        "counterparty or operate in a certain geography or business or technology "
        "sector?", risk=True),
]

BY_KEY: dict[str, ClauseType] = {c.key: c for c in CLAUSE_TYPES}
BY_CUAD_NAME: dict[str, ClauseType] = {c.cuad_name: c for c in CLAUSE_TYPES}
