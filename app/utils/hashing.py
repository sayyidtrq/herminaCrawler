from hashlib import sha256


def generate_review_hash(review: dict) -> str:
    hash_input = "|".join(
        [
            str(review.get("source") or ""),
            str(review.get("external_place_id") or ""),
            str(review.get("external_review_id") or ""),
            str(review.get("reviewer_name") or ""),
            str(review.get("rating") or ""),
            str(review.get("review_text") or ""),
            str(review.get("review_time") or ""),
        ]
    )
    return sha256(hash_input.encode("utf-8")).hexdigest()


def generate_selenium_review_hash(review: dict) -> str:
    hash_input = "|".join(
        [
            str(review.get("source") or ""),
            str(review.get("location_id") or ""),
            str(review.get("reviewer_name") or ""),
            str(review.get("rating") or ""),
            str(review.get("review_text") or ""),
            str(review.get("review_relative_time") or ""),
            str(review.get("reviewer_profile_url") or ""),
        ]
    )
    return sha256(hash_input.encode("utf-8")).hexdigest()
