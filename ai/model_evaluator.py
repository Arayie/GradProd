"""
Model Evaluation Engine
Calculates Precision, Recall, Macro F1, Cohen's Kappa, and Grounding Rates against human gold sets.
Generates comprehensive evaluation metrics, confusion matrices, and language breakdowns.
"""

from typing import List, Dict, Any, Tuple, Optional
import math
from collections import defaultdict, Counter
import pandas as pd
import json

class ModelEvaluator:
    """Evaluates classification performance against human gold-standard ground truth."""

    @staticmethod
    def calculate_metrics(
        y_true: List[str], y_pred: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate precision, recall, and F1 per class and macro average.
        """
        classes = sorted(list(set(y_true + y_pred)))
        tp = defaultdict(int)
        fp = defaultdict(int)
        fn = defaultdict(int)

        for true_label, pred_label in zip(y_true, y_pred):
            if true_label == pred_label:
                tp[true_label] += 1
            else:
                fp[pred_label] += 1
                fn[true_label] += 1

        per_class = {}
        precisions = []
        recalls = []
        f1s = []

        for c in classes:
            c_tp = tp[c]
            c_fp = fp[c]
            c_fn = fn[c]

            prec = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
            rec = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            per_class[c] = {
                "support": c_tp + c_fn,
                "precision": round(prec, 3),
                "recall": round(rec, 3),
                "f1_score": round(f1, 3),
            }
            precisions.append(prec)
            recalls.append(rec)
            f1s.append(f1)

        macro_prec = sum(precisions) / len(precisions) if precisions else 0.0
        macro_rec = sum(recalls) / len(recalls) if recalls else 0.0
        macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

        total_correct = sum(tp.values())
        accuracy = total_correct / len(y_true) if y_true else 0.0

        return {
            "accuracy": round(accuracy, 3),
            "macro_precision": round(macro_prec, 3),
            "macro_recall": round(macro_rec, 3),
            "macro_f1": round(macro_f1, 3),
            "per_class": per_class,
            "classes": classes,
        }

    @staticmethod
    def calculate_cohens_kappa(y_true: List[str], y_pred: List[str]) -> float:
        """
        Calculate Cohen's Kappa score for inter-rater agreement.
        kappa = (Po - Pe) / (1 - Pe)
        """
        if not y_true or len(y_true) != len(y_pred):
            return 0.0

        n = len(y_true)
        # Observed agreement Po
        po = sum(1 for t, p in zip(y_true, y_pred) if t == p) / n

        # Expected agreement Pe
        true_counts = Counter(y_true)
        pred_counts = Counter(y_pred)
        all_labels = set(true_counts.keys()).union(set(pred_counts.keys()))

        pe = sum((true_counts[l] / n) * (pred_counts[l] / n) for l in all_labels)

        if pe >= 1.0:
            return 1.0
        kappa = (po - pe) / (1.0 - pe)
        return round(kappa, 3)

    @classmethod
    def evaluate_gold_set(
        cls,
        eval_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Full evaluation against gold-set records containing:
        - evidence_id
        - language
        - app_name
        - true_lifecycle_stage, pred_lifecycle_stage
        - true_pain_point, pred_pain_point
        - true_intent, pred_intent
        - evidence_grounding_status
        """
        if not eval_records:
            return {}

        y_true_life = [r.get("true_lifecycle_stage", "UNKNOWN") for r in eval_records]
        y_pred_life = [r.get("pred_lifecycle_stage", "UNKNOWN") for r in eval_records]

        y_true_pain = [r.get("true_pain_point", "NO_PAIN_POINT_STATED") for r in eval_records]
        y_pred_pain = [r.get("pred_pain_point", "NO_PAIN_POINT_STATED") for r in eval_records]

        lifecycle_metrics = cls.calculate_metrics(y_true_life, y_pred_life)
        pain_metrics = cls.calculate_metrics(y_true_pain, y_pred_pain)

        kappa_life = cls.calculate_cohens_kappa(y_true_life, y_pred_life)
        kappa_pain = cls.calculate_cohens_kappa(y_true_pain, y_pred_pain)

        # Grounding rate
        grounded_count = sum(
            1 for r in eval_records if r.get("evidence_grounding_status") in ("FULLY_GROUNDED", "NO_EVIDENCE_STATED")
        )
        grounding_rate = round(grounded_count / len(eval_records), 3)

        # Breakdown by Language
        lang_groups = defaultdict(list)
        for r in eval_records:
            lang = r.get("language", "en")
            group = "en" if lang == "en" else "hindi_hinglish"
            lang_groups[group].append(r)

        lang_breakdown = {}
        for group, recs in lang_groups.items():
            t_pain = [r.get("true_pain_point", "NO_PAIN_POINT_STATED") for r in recs]
            p_pain = [r.get("pred_pain_point", "NO_PAIN_POINT_STATED") for r in recs]
            m = cls.calculate_metrics(t_pain, p_pain)
            k = cls.calculate_cohens_kappa(t_pain, p_pain)
            lang_breakdown[group] = {
                "sample_size": len(recs),
                "macro_f1": m["macro_f1"],
                "macro_precision": m["macro_precision"],
                "macro_recall": m["macro_recall"],
                "cohens_kappa": k,
            }

        # Breakdown by App
        app_groups = defaultdict(list)
        for r in eval_records:
            app = r.get("app_name", "groww")
            app_groups[app].append(r)

        app_breakdown = {}
        for app, recs in app_groups.items():
            t_pain = [r.get("true_pain_point", "NO_PAIN_POINT_STATED") for r in recs]
            p_pain = [r.get("pred_pain_point", "NO_PAIN_POINT_STATED") for r in recs]
            m = cls.calculate_metrics(t_pain, p_pain)
            app_breakdown[app] = {
                "sample_size": len(recs),
                "macro_f1": m["macro_f1"],
                "accuracy": m["accuracy"],
            }

        # Identify Errors
        errors = []
        for r in eval_records:
            t_pain = r.get("true_pain_point")
            p_pain = r.get("pred_pain_point")
            t_life = r.get("true_lifecycle_stage")
            p_life = r.get("pred_lifecycle_stage")

            if t_pain != p_pain or t_life != p_life:
                errors.append({
                    "evidence_id": r.get("evidence_id"),
                    "review_text": r.get("review_text", "")[:100],
                    "app_name": r.get("app_name"),
                    "language": r.get("language"),
                    "true_lifecycle": t_life,
                    "pred_lifecycle": p_life,
                    "true_pain_point": t_pain,
                    "pred_pain_point": p_pain,
                    "error_type": "PAIN_POINT_MISMATCH" if t_pain != p_pain else "LIFECYCLE_MISMATCH",
                })

        return {
            "total_evaluated": len(eval_records),
            "lifecycle_evaluation": {
                **lifecycle_metrics,
                "cohens_kappa": kappa_life,
            },
            "pain_point_evaluation": {
                **pain_metrics,
                "cohens_kappa": kappa_pain,
            },
            "evidence_grounding_rate": grounding_rate,
            "language_breakdown": lang_breakdown,
            "app_breakdown": app_breakdown,
            "error_count": len(errors),
            "classification_errors": errors,
        }
