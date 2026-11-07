"""
Sample Data Generator and Demo Mode Manager for Growww Discovery Engine.
Generates 35+ realistic synthetic review records covering SIP friction, setup, KYC, and redemption.
All records are strictly tagged as SYNTHETIC_DEMO and quarantined from production analytics.
"""
import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db
from database.repositories import ReviewRepository

SYNTHETIC_REVIEWS: List[Dict[str, Any]] = [
    # --- GROWW (Primary Case Study) ---
    {
        "app_id": "groww",
        "store": "google_play",
        "source_record_id": "demo_groww_01",
        "review_title": "UPI Autopay setup was instant",
        "review_text": "I am a first-time investor and set up a monthly SIP of Rs 1,000 in Parag Parikh Flexi Cap. Autopay via PhonePe worked in 2 minutes without any paperwork.",
        "star_rating": 5,
        "days_ago": 12,
        "app_version": "18.22.0",
        "language_original": "en"
    },
    {
        "app_id": "groww",
        "store": "google_play",
        "source_record_id": "demo_groww_02",
        "review_title": "Money debited but order failed",
        "review_text": "Bank account debited on 5th for SIP installment but app shows transaction failed. Support ticket has been open for 4 days with only automated chatbot replies.",
        "star_rating": 1,
        "days_ago": 15,
        "app_version": "18.21.1",
        "language_original": "en"
    },
    {
        "app_id": "groww",
        "store": "apple_app_store",
        "source_record_id": "demo_groww_03",
        "review_title": "Paisa minus me kyu ja raha hai?",
        "review_text": "3 mahine pehle SIP shuru ki thi savings ke liye par mera portfolio red me hai. Kya yeh safe hai ya mera paisa doob jayega?",
        "star_rating": 2,
        "days_ago": 25,
        "app_version": "18.20.0",
        "language_original": "hi-Latn"
    },
    {
        "app_id": "groww",
        "store": "google_play",
        "source_record_id": "demo_groww_04",
        "review_title": "केवाईसी सत्यापन में बहुत समय लगा",
        "review_text": "डिजिलॉकर से आधार सत्यापन बार-बार विफल हो रहा था। 5 दिन बाद जाकर खाता सक्रिय हुआ लेकिन अब एसआईपी सही चल रही है।",
        "star_rating": 3,
        "days_ago": 40,
        "app_version": "18.19.0",
        "language_original": "hi"
    },
    {
        "app_id": "groww",
        "store": "apple_app_store",
        "source_record_id": "demo_groww_05",
        "review_title": "Smooth 1-year journey",
        "review_text": "Completed 12 months of disciplined monthly investing across 3 index funds. Step-up feature helped me increase amount with my salary hike.",
        "star_rating": 5,
        "days_ago": 5,
        "app_version": "18.22.1",
        "language_original": "en"
    },

    # --- ZERODHA COIN (Mutual Funds) ---
    {
        "app_id": "zerodha_coin",
        "store": "google_play",
        "source_record_id": "demo_coin_01",
        "review_title": "True direct mutual funds without commission",
        "review_text": "Coin is great because units are held in demat mode with zero distributor commission. Clean interface without loan or trading popups.",
        "star_rating": 5,
        "days_ago": 18,
        "app_version": "4.2.0",
        "language_original": "en"
    },
    {
        "app_id": "zerodha_coin",
        "store": "apple_app_store",
        "source_record_id": "demo_coin_02",
        "review_title": "Mandate deduction timing confusion",
        "review_text": "Fund deducted on Friday evening but NAV units allocated at Tuesday NAV price. Very confusing for beginners who expect same day NAV.",
        "star_rating": 2,
        "days_ago": 32,
        "app_version": "4.1.9",
        "language_original": "en"
    },
    {
        "app_id": "zerodha_coin",
        "store": "google_play",
        "source_record_id": "demo_coin_03",
        "review_title": "e-Mandate rejected by bank",
        "review_text": "Net banking mandate failed with error code 102. Had to delete and recreate autopay twice before HDFC accepted it.",
        "star_rating": 3,
        "days_ago": 60,
        "app_version": "4.0.5",
        "language_original": "en"
    },
    {
        "app_id": "zerodha_coin",
        "store": "apple_app_store",
        "source_record_id": "demo_coin_04",
        "review_title": "Redemption takes 3 days",
        "review_text": "Needed emergency funds for medical expense. Liquid fund withdrawal took 3 business days to hit my savings account.",
        "star_rating": 2,
        "days_ago": 45,
        "app_version": "4.1.2",
        "language_original": "en"
    },

    # --- ZERODHA KITE (Ecosystem / Stocks) ---
    {
        "app_id": "zerodha_kite",
        "store": "google_play",
        "source_record_id": "demo_kite_01",
        "review_title": "Fast and clutter-free interface",
        "review_text": "Using Kite alongside Coin. The login biometrics and order execution speed are unmatched in the Indian fintech ecosystem.",
        "star_rating": 5,
        "days_ago": 8,
        "app_version": "3.8.1",
        "language_original": "en"
    },
    {
        "app_id": "zerodha_kite",
        "store": "apple_app_store",
        "source_record_id": "demo_kite_02",
        "review_title": "Server down during budget day",
        "review_text": "App crashed during market opening. Could not modify stop loss or square off positions. Unacceptable for serious traders.",
        "star_rating": 1,
        "days_ago": 90,
        "app_version": "3.7.0",
        "language_original": "en"
    },

    # --- UPSTOX ---
    {
        "app_id": "upstox",
        "store": "google_play",
        "source_record_id": "demo_upstox_01",
        "review_title": "Mutual fund section hard to locate",
        "review_text": "App is primarily built for F&O trading. Had to search multiple tabs just to find my monthly mutual fund SIP schedule.",
        "star_rating": 3,
        "days_ago": 22,
        "app_version": "6.2.0",
        "language_original": "en"
    },
    {
        "app_id": "upstox",
        "store": "apple_app_store",
        "source_record_id": "demo_upstox_02",
        "review_title": "Good portfolio tracker and SIP alerts",
        "review_text": "Upstox sends WhatsApp reminders 2 days prior to SIP debit so I always maintain sufficient balance. Zero bounce charges.",
        "star_rating": 5,
        "days_ago": 14,
        "app_version": "6.1.8",
        "language_original": "en"
    },
    {
        "app_id": "upstox",
        "store": "google_play",
        "source_record_id": "demo_upstox_03",
        "review_title": "खाता खोलने में परेशानी",
        "review_text": "हस्ताक्षर मेल न खाने के कारण 3 बार फॉर्म रिजेक्ट हुआ। ग्राहक सेवा नंबर पर फोन नहीं लगता।",
        "star_rating": 1,
        "days_ago": 50,
        "app_version": "6.0.4",
        "language_original": "hi"
    },

    # --- ANGEL ONE ---
    {
        "app_id": "angel_one",
        "store": "google_play",
        "source_record_id": "demo_angel_01",
        "review_title": "Bank bounce penalty charged",
        "review_text": "No advance notification was sent before mandate deduction. Account had low balance and SBI charged Rs 590 bounce penalty! Horrible.",
        "star_rating": 1,
        "days_ago": 11,
        "app_version": "5.19.2",
        "language_original": "en"
    },
    {
        "app_id": "angel_one",
        "store": "apple_app_store",
        "source_record_id": "demo_angel_02",
        "review_title": "ARQ advisory recommendations helped",
        "review_text": "Beginner friendly recommendations. Started disciplined 2000 per month based on their risk profile quiz.",
        "star_rating": 4,
        "days_ago": 28,
        "app_version": "5.18.0",
        "language_original": "en"
    },
    {
        "app_id": "angel_one",
        "store": "google_play",
        "source_record_id": "demo_angel_03",
        "review_title": "SIP pause option kahan hai?",
        "review_text": "Diwali kharche ke liye 2 mahine SIP pause karni thi par cancel ka hi option dikh raha hai. Temporary stop button hona chahiye.",
        "star_rating": 2,
        "days_ago": 35,
        "app_version": "5.17.5",
        "language_original": "hi-Latn"
    },

    # --- INDMONEY ---
    {
        "app_id": "indmoney",
        "store": "apple_app_store",
        "source_record_id": "demo_ind_01",
        "review_title": "Consolidated net worth and external SIP tracking",
        "review_text": "Love how it automatically tracks external mutual funds from CAMS and KFintech alongside my US stock investments in one clean dashboard.",
        "star_rating": 5,
        "days_ago": 7,
        "app_version": "2.8.4",
        "language_original": "en"
    },
    {
        "app_id": "indmoney",
        "store": "google_play",
        "source_record_id": "demo_ind_02",
        "review_title": "Too much spam notifications",
        "review_text": "App constantly sends credit card offers and loan notifications even after disabling marketing permissions. Distracting from investing.",
        "star_rating": 2,
        "days_ago": 19,
        "app_version": "2.8.1",
        "language_original": "en"
    },
    {
        "app_id": "indmoney",
        "store": "google_play",
        "source_record_id": "demo_ind_03",
        "review_title": "Tax filing 80C receipt ready in seconds",
        "review_text": "Downloaded my capital gains statement and ELSS investment certificates for ITR with single click. Saved a lot of time.",
        "star_rating": 5,
        "days_ago": 75,
        "app_version": "2.6.0",
        "language_original": "en"
    },

    # --- ET MONEY ---
    {
        "app_id": "et_money",
        "store": "google_play",
        "source_record_id": "demo_et_01",
        "review_title": "Genius membership insights are insightful",
        "review_text": "Dynamic asset allocation advice guided me when market reached all-time high. Transferred part of equity SIP to debt fund smoothly.",
        "star_rating": 5,
        "days_ago": 16,
        "app_version": "12.4.0",
        "language_original": "en"
    },
    {
        "app_id": "et_money",
        "store": "apple_app_store",
        "source_record_id": "demo_et_02",
        "review_title": "Mandate cancellation took 2 weeks",
        "review_text": "Cancelled SIP in app but bank still deducted next month instalment because mandate revocation was delayed at NPCI.",
        "star_rating": 2,
        "days_ago": 65,
        "app_version": "12.2.1",
        "language_original": "en"
    },
    {
        "app_id": "et_money",
        "store": "google_play",
        "source_record_id": "demo_et_03",
        "review_title": "रिटायरमेंट प्लानिंग के लिए सर्वश्रेष्ठ",
        "review_text": "हर महीने 5,000 की बचत पिछले 2 साल से बिना रुकावट चल रही है। रिटर्न और एक्सआईआरआर बिल्कुल स्पष्ट दिखाई देता है।",
        "star_rating": 5,
        "days_ago": 80,
        "app_version": "12.0.0",
        "language_original": "hi"
    },

    # --- PAYTM MONEY ---
    {
        "app_id": "paytm_money",
        "store": "google_play",
        "source_record_id": "demo_paytm_01",
        "review_title": "UPI payments are fast",
        "review_text": "Linked with Paytm Payments Bank and UPI autopay. Smooth onboarding and quick SIP setup with zero initial fees.",
        "star_rating": 4,
        "days_ago": 10,
        "app_version": "8.5.0",
        "language_original": "en"
    },
    {
        "app_id": "paytm_money",
        "store": "apple_app_store",
        "source_record_id": "demo_paytm_02",
        "review_title": "Customer care does not exist",
        "review_text": "Payment deducted twice for single SIP date. Ticket closed automatically saying resolved when refund has not arrived.",
        "star_rating": 1,
        "days_ago": 29,
        "app_version": "8.4.2",
        "language_original": "en"
    },
    {
        "app_id": "paytm_money",
        "store": "google_play",
        "source_record_id": "demo_paytm_03",
        "review_title": "Bank change karne me dikkat",
        "review_text": "Naya bank account update nahi ho raha. Old bank account band hone wala hai aur mandate transfer option nahi mil raha.",
        "star_rating": 2,
        "days_ago": 55,
        "app_version": "8.3.0",
        "language_original": "hi-Latn"
    },

    # --- ADDITIONAL DIVERSE RECORDS (Total > 30) ---
    {
        "app_id": "groww",
        "store": "google_play",
        "source_record_id": "demo_groww_06",
        "review_title": "Simple interface beats confusing legacy brokers",
        "review_text": "Clean design for direct mutual funds. No hidden account maintenance fees (AMC) or surprise demat charges.",
        "star_rating": 5,
        "days_ago": 2,
        "app_version": "18.22.1",
        "language_original": "en"
    },
    {
        "app_id": "groww",
        "store": "apple_app_store",
        "source_record_id": "demo_groww_07",
        "review_title": "App keeps crashing during payment confirmation",
        "review_text": "Screen went blank right after entering UPI PIN. Check your order book before paying twice!",
        "star_rating": 2,
        "days_ago": 14,
        "app_version": "18.21.0",
        "language_original": "en"
    },
    {
        "app_id": "zerodha_coin",
        "store": "google_play",
        "source_record_id": "demo_coin_05",
        "review_title": "Demat holding statement received on time",
        "review_text": "All units reflected in NSDL CAS statement. Transparent tracking of NAV and corporate action payouts.",
        "star_rating": 4,
        "days_ago": 21,
        "app_version": "4.2.1",
        "language_original": "en"
    },
    {
        "app_id": "upstox",
        "store": "google_play",
        "source_record_id": "demo_upstox_04",
        "review_title": "Good for beginners who want both stocks and funds",
        "review_text": "Switched from offline broker to Upstox. Saved 1.5% distributor commission every year on my ELSS tax saving funds.",
        "star_rating": 5,
        "days_ago": 38,
        "app_version": "6.1.0",
        "language_original": "en"
    },
    {
        "app_id": "angel_one",
        "store": "google_play",
        "source_record_id": "demo_angel_04",
        "review_title": "गांव के लोगों के लिए अच्छा ऐप",
        "review_text": "हिंदी में सारी जानकारी मिलती है और एसआईपी चालू करना आसान है। मेरे छोटे भाई ने भी 500 रुपये से शुरू किया।",
        "star_rating": 5,
        "days_ago": 48,
        "app_version": "5.18.2",
        "language_original": "hi"
    },
    {
        "app_id": "indmoney",
        "store": "apple_app_store",
        "source_record_id": "demo_ind_04",
        "review_title": "Good SIP calculator",
        "review_text": "Compounding goals projection tool is helpful for planning long term child education milestones.",
        "star_rating": 4,
        "days_ago": 26,
        "app_version": "2.8.2",
        "language_original": "en"
    },
    {
        "app_id": "paytm_money",
        "store": "google_play",
        "source_record_id": "demo_paytm_04",
        "review_title": "Redemption funds credited in 2 days",
        "review_text": "Sold debt fund units on Monday, money received in bank on Wednesday afternoon. Clear transaction timeline.",
        "star_rating": 4,
        "days_ago": 13,
        "app_version": "8.5.1",
        "language_original": "en"
    }
]

class SampleDataManager:
    """Manages loading and safely clearing isolated demo data."""

    def __init__(self, review_repo: ReviewRepository = None):
        self.review_repo = review_repo or ReviewRepository(get_db())

    def load_demo_records(self) -> int:
        """
        Loads 30+ synthetic sample records into the database.
        Every record is stamped with eligibility_status='SYNTHETIC_DEMO'.
        """
        now = datetime.utcnow()
        inserted_count = 0

        for r in SYNTHETIC_REVIEWS:
            created_at = (now - timedelta(days=r["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
            norm_text = " ".join(r["review_text"].lower().split())
            content_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()

            # Skip if already loaded
            if self.review_repo.exists(r["app_id"], r["store"], r["source_record_id"], content_hash):
                continue

            record = {
                "evidence_id": f"DEMO_{r['app_id'][:4].upper()}_{content_hash[:8]}",
                "app_id": r["app_id"],
                "store": r["store"],
                "source_record_id": r["source_record_id"],
                "review_title": r.get("review_title"),
                "review_text": r["review_text"],
                "star_rating": r["star_rating"],
                "review_created_at": created_at,
                "app_version": r.get("app_version"),
                "language_original": r.get("language_original", "en"),
                "content_hash": content_hash,
                "collection_method": "sample_demo_generator",
                "eligibility_status": "SYNTHETIC_DEMO",
                "redaction_status": "CLEAN"
            }
            try:
                self.review_repo.insert_review(record)
                inserted_count += 1
            except Exception:
                pass

        return inserted_count

    def clear_demo_records(self) -> int:
        """Removes all SYNTHETIC_DEMO records without touching real evidence."""
        return self.review_repo.delete_synthetic_demo_data()
