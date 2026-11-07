"""
Lexical and Thematic Clustering for Review Pain Points
Discovers emergent micro-themes and clusters related investor complaints.
"""

from typing import List, Dict, Any, Tuple
import re
from collections import Counter, defaultdict
import math

class ReviewClusterer:
    """Clusters reviews and pain-point text snippets based on lexical term co-occurrence."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "is", "was", "are", "were", "it", "this", "that", "i", "my", "me", "we",
        "not", "no", "but", "so", "as", "be", "have", "has", "had", "do", "does",
        "did", "you", "your", "app", "groww", "coin", "kite", "very", "good", "worst"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        return [w for w in words if w not in cls.STOPWORDS]

    @classmethod
    def cluster_reviews(
        cls,
        reviews: List[Dict[str, Any]],
        num_clusters: int = 5,
        min_cluster_size: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Group reviews into micro-clusters based on dominant pain point and co-occurring terms.
        """
        if not reviews:
            return []

        # Group primarily by primary pain point or lifecycle stage
        by_pain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in reviews:
            pain = r.get("ai_primary_pain_point") or r.get("pain_point") or "OTHER"
            by_pain[pain].append(r)

        clusters = []
        cluster_id = 1

        for pain_label, items in sorted(by_pain.items(), key=lambda x: len(x[1]), reverse=True):
            if len(items) < min_cluster_size and cluster_id > num_clusters:
                continue

            all_tokens = []
            for item in items:
                text = item.get("review_text", "")
                all_tokens.extend(cls.tokenize(text))

            top_terms = [t for t, _ in Counter(all_tokens).most_common(5)]
            sample = items[0].get("review_text", "")[:120] + "..." if items else ""

            clusters.append({
                "cluster_id": f"CLUST-{cluster_id:02d}",
                "theme_label": pain_label,
                "review_count": len(items),
                "top_keywords": top_terms,
                "representative_snippet": sample,
                "coherence_score": round(min(1.0, len(items) / (len(items) + 5)), 2),
            })
            cluster_id += 1

            if len(clusters) >= num_clusters:
                break

        return clusters
