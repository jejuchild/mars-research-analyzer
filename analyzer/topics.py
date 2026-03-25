"""Topic modeling using BERTopic or fallback TF-IDF + clustering."""

import logging
from collections import Counter

logger = logging.getLogger(__name__)


def _fallback_topic_analysis(texts: list[str], n_topics: int = 10) -> dict:
    """Simple TF-IDF + KMeans clustering when BERTopic is unavailable or data is too small."""
    if len(texts) < 2:
        return {"method": "none", "reason": "insufficient_data", "n_topics": 0, "topics": {}}

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 3),
        min_df=2,
        max_df=0.95,
    )
    tfidf = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    actual_topics = min(n_topics, len(texts) // 5, 20)
    if actual_topics < 2:
        actual_topics = 2

    km = KMeans(n_clusters=actual_topics, random_state=42, n_init=10)
    labels = km.fit_predict(tfidf)

    topics = {}
    for i in range(actual_topics):
        center = km.cluster_centers_[i]
        top_indices = center.argsort()[-10:][::-1]
        top_words = [(feature_names[idx], float(center[idx])) for idx in top_indices]
        count = int((labels == i).sum())
        topics[i] = {
            "words": top_words,
            "count": count,
        }

    return {
        "method": "tfidf_kmeans",
        "n_topics": actual_topics,
        "topics": topics,
        "labels": labels.tolist(),
    }


def analyze_topics(papers: list[dict], min_docs: int = 100) -> dict:
    """Run topic modeling on paper abstracts."""
    texts = []
    valid_papers = []
    for p in papers:
        abstract = p.get("abstract", "")
        if abstract and len(abstract) > 50:
            texts.append(f"{p.get('title', '')}. {abstract}")
            valid_papers.append(p)

    if len(texts) < 10:
        logger.warning(f"Only {len(texts)} papers with abstracts. Skipping topic modeling.")
        return {"method": "none", "reason": "insufficient_data", "n_docs": len(texts)}

    # Try BERTopic first
    if len(texts) >= min_docs:
        try:
            from bertopic import BERTopic

            topic_model = BERTopic(
                language="english",
                min_topic_size=max(5, len(texts) // 50),
                nr_topics="auto",
                verbose=False,
            )
            topics_result, probs = topic_model.fit_transform(texts)

            topic_info = topic_model.get_topic_info()
            topics = {}
            for _, row in topic_info.iterrows():
                tid = row["Topic"]
                if tid == -1:
                    continue
                topic_words = topic_model.get_topic(tid)
                topics[int(tid)] = {
                    "words": [(w, float(s)) for w, s in topic_words[:10]],
                    "count": int(row["Count"]),
                    "name": row.get("Name", f"Topic_{tid}"),
                }

            return {
                "method": "bertopic",
                "n_topics": len(topics),
                "topics": topics,
                "n_docs": len(texts),
            }
        except ImportError:
            logger.info("BERTopic not installed, using fallback TF-IDF + KMeans")
        except Exception as e:
            logger.warning(f"BERTopic failed: {e}, using fallback")

    # Fallback
    return _fallback_topic_analysis(texts)
