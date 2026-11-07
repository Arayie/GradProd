# Classification & Enrichment Prompt: Investor Experience Discovery

You will analyze the customer review provided inside the `<REVIEW_DATA>` tags.
Classify the review into the structured research taxonomy below and extract exact verbatim text spans supporting each prediction.

## Research Taxonomy

### 1. Primary Research Relevance
- DIRECT_SIP_RELEVANT: Explicitly discusses Systematic Investment Plans (SIP), autopay, recurring deductions, mandates, instalments.
- INDIRECT_SIP_RELEVANT: Discusses mutual funds, NAV, unit allotments, AMC transactions, or long-term regular investments where SIP context is clearly implied.
- GENERAL_INVESTMENT_RELEVANT: Discusses mutual funds, stocks, IPOs, or trading in general without SIP specificity.
- GENERAL_APP_FEEDBACK: General app UI, login, crashes, or customer service without investment specificity.
- IRRELEVANT: Spam, random text, non-financial comments.

### 2. SIP Lifecycle Stage (Primary & Secondary)
Allowed codes:
- S0_DISCOVERY: Browsing funds, onboarding, opening account, choosing between apps.
- S1_SETUP: Creating first SIP, setting up UPI Autopay, bank mandate, KYC approval.
- S2_EARLY: First instalment deducted, waiting for unit allotment, initial NAV calculation.
- S3_HABIT: Regular monthly deductions, continuous investing, portfolio monitoring.
- S4_REVIEW: Step-up SIP, adding more funds, increasing amount, rebalancing.
- S5_FRICTION: Encountering payment failure, changing dates, attempting to pause.
- S6_PAUSE_STOP: Cancelling SIP, stopping autopay, redeeming funds, switching apps.
- S7_RESTART: Resuming paused SIP, creating new SIP after cancellation.
- GENERAL_INVESTMENT: Non-lifecycle mutual fund/stock feedback.
- UNKNOWN: Cannot determine stage.

### 3. Investor Intent / Motivation (Select all that apply)
- DISCIPLINED_SAVING: To force regular monthly savings habit.
- LONG_TERM_WEALTH_CREATION: Compounding for 5-10+ years, retirement, future security.
- FIRST_TIME_INVESTING: Beginner trying out mutual funds for the first time.
- LEARNING_INVESTMENT: Curious to learn how markets, NAV, and funds work.
- TAX_PLANNING: ELSS investments for Section 80C deductions.
- CONVENIENCE: Digital paperless KYC, 1-click UPI setup.
- FAMILY_INFLUENCE: Recommended by family members or relatives.
- PEER_INFLUENCE: Recommended by friends or colleagues.
- CREATOR_ADVISER_INFLUENCE: Influenced by YouTube finfluencer, social media, or advisor.
- HIGH_RETURNS_EXPECTATION: Expecting fast high returns.
- EMERGENCY_FUND: Building liquid savings.
- OTHER_INTENT: Explicit other motivation.
- UNKNOWN: No explicit motivation stated.

### 4. Expectations (Select all that apply)
- EFFORTLESS_AUTOMATION: Expecting smooth automatic debits without manual intervention.
- HIGH_GROWTH: Expecting strong capital appreciation.
- CAPITAL_SAFETY: Expecting safe, risk-free savings.
- TIMELY_SUPPORT: Expecting quick human help when problems occur.
- INSTANT_WITHDRAWAL: Expecting immediate bank credit on redemption.
- CLEAR_NAV_REPORTING: Expecting accurate, timely NAV and return figures.
- PREDICTABLE_DEDUCTIONS: Expecting debits strictly on selected dates.
- LOW_CHARGES: Zero commission, no hidden fees.
- SEAMLESS_KYC: Instant hassle-free KYC verification.
- OTHER_EXPECTATION: Explicit other expectation.
- NOT_STATED: No specific expectation stated.

### 5. Investor Behaviour (Select all that apply)
- STARTED_SIP, SET_UP_MANDATE, ATTEMPTED_MANDATE_SETUP, CHECKED_PAYMENT_STATUS,
- TRACKED_RETURNS, MONITORED_NAV, MODIFIED_SIP_AMOUNT, SKIPPED_INSTALMENT,
- PAUSED_SIP, ATTEMPTED_SIP_PAUSE, CANCELLED_SIP, ATTEMPTED_SIP_CANCELLATION,
- REDEEMED_FUNDS, SWITCHED_APPLICATION, CONTACTED_SUPPORT, UNINSTALLED_APP,
- OTHER_BEHAVIOUR, NOT_STATED.

### 6. Pain Points (Select all that apply)
- MANDATE_REGISTRATION_FAILURE: Mandate rejected, bank verification failed, NACH error.
- AUTOPAY_SETUP_ERROR: UPI autopay setup failed or timed out.
- BANK_VERIFICATION_FAILURE: Penny drop or account verification failed.
- KYC_REJECTION_OR_DELAY: Verification stuck, Aadhaar/PAN rejected.
- MANDATE_APPROVAL_DELAY: Mandate pending for days/weeks.
- DOUBLE_DEBIT: Same instalment deducted twice.
- MONEY_DEDUCTED_NOT_REFLECTED: Bank debited but money not shown in app.
- AUTOPAY_EXECUTION_FAILURE: Autopay failed on due date, missed instalment.
- PAYMENT_GATEWAY_TIMEOUT: UPI or netbanking timed out during payment.
- LATE_INVESTMENT_EXECUTION: Days elapsed between deduction and order placement.
- NAV_ALLOCATION_DELAY: NAV date delayed, units allotted late.
- NAV_CALCULATION_CONFUSION: Confusion regarding NAV price or cutoff timing.
- RETURN_REPORTING_DISCREPANCY: Discrepancy in returns, XIRR, or profit calculations.
- PORTFOLIO_UPDATE_DELAY: App portfolio not updating balance.
- UNITS_NOT_ALLOTTED: Deducted funds received zero unit allocation.
- SIP_PAUSE_DIFFICULTY: Could not pause SIP, feature missing or broken.
- SIP_CANCELLATION_DIFFICULTY: Could not stop SIP, continued debits after cancellation.
- DATE_MODIFICATION_FAILURE: Unable to change SIP instalment date.
- STEP_UP_ERROR: Issues with step-up configuration.
- UNWANTED_AUTO_DEBIT: Deduction happened after cancellation/pause.
- REDEMPTION_DELAY: Withdrawal took unusually long time.
- WITHDRAWAL_FAILURE: Withdrawal failed or rejected.
- BANK_ACCOUNT_MISMATCH: Redemption credited to wrong account.
- EXIT_LOAD_CONFUSION: Confusion or anger over exit loads or taxes.
- CUSTOMER_SUPPORT_UNRESPONSIVE: No response, ticket closed without resolution.
- GENERIC_BOT_RESPONSES: Stuck in repetitive bot loops.
- UNRESOLVED_COMPLAINT: Issue unresolved for extended duration.
- LACK_OF_CLEAR_EXPLANATION: Cryptic error message with no guidance.
- NO_PAIN_POINT_STATED: Positive feedback with no issues reported.

### 7. Triggers
- PAYMENT_FAILURE, MANDATE_FAILURE, MARKET_CORRECTION, NEGATIVE_RETURN_PERCEPTION,
- UNEXPECTED_CHARGE, UNHELPFUL_SUPPORT_RESPONSE, APP_UPDATE_GLITCH,
- PERSONAL_CASH_CRUNCH, OTHER_TRIGGER, NOT_STATED.

### 8. Outside-App Coping Workarounds
- CONTACTED_BANK, CONTACTED_AMC, CONTACTED_CUSTOMER_SUPPORT, CHECKED_BANK_STATEMENT,
- WATCHED_YOUTUBE_OR_TUTORIAL, ASKED_FRIEND_OR_FAMILY, COMPLAINED_ON_SOCIAL_MEDIA,
- SWITCHED_TO_ANOTHER_APP, UNINSTALLED_APP, OTHER_WORKAROUND, NOT_STATED.

### 9. Reported Outcome
- CONTINUED_SIP, PAUSED_SIP, STOPPED_SIP, SWITCHED_PLATFORM, LOST_MONEY_PERCEPTION,
- RESOLVED_AFTER_DELAY, UNRESOLVED, SATISFIED, CHURNED, NOT_STATED.

## Required JSON Output Schema
Respond ONLY with a valid JSON object matching this schema:
```json
{
  "evidence_id": "string",
  "primary_research_relevance": "DIRECT_SIP_RELEVANT | INDIRECT_SIP_RELEVANT | GENERAL_INVESTMENT_RELEVANT | GENERAL_APP_FEEDBACK | IRRELEVANT",
  "lifecycle_stage": "S0_DISCOVERY | S1_SETUP | S2_EARLY | S3_HABIT | S4_REVIEW | S5_FRICTION | S6_PAUSE_STOP | S7_RESTART | GENERAL_INVESTMENT | UNKNOWN",
  "secondary_lifecycle_stages": ["string"],
  "investor_intent": ["string"],
  "expectations": ["string"],
  "behaviour": ["string"],
  "pain_points": ["string"],
  "triggers": ["string"],
  "outside_app_actions": ["string"],
  "reported_outcome": "string",
  "disclosed_context": {
    "age_band": "UNKNOWN",
    "investment_experience": "FIRST_TIME | EXPERIENCED | UNKNOWN",
    "income_stability": "UNKNOWN"
  },
  "confidence_scores": {
    "overall": 0.95,
    "lifecycle_stage": 0.95,
    "investor_intent": 0.85,
    "pain_points": 0.95,
    "reported_outcome": 0.90
  },
  "evidence_spans": {
    "LABEL_NAME": "Exact verbatim excerpt from review text supporting this label"
  },
  "reasoning_summary": "Brief 1-2 sentence explanation of the classification"
}
```

## Review to Classify
<REVIEW_DATA>
Evidence ID: {{evidence_id}}
App: {{app_name}}
Rating: {{star_rating}} Stars
Text:
{{review_text}}
</REVIEW_DATA>
