from __future__ import annotations

KEYWORD_FIELDS = [
    "gd_identity",
    "province",
    "province_name",
    "csp_id",
    "csp_name",
    "csp_prov_id",
    "csp_prov_name",
    "month",
    "time_period",
    "label_group",
    "primary_labels",
    "secondary_labels",
    "tertiary_labels",
    "scene_event",
    "scene_emotion",
    "scene_service_type",
    "insight_dimension",
    "customer_keywords",
    "cs_keywords",
    "biz_type",
    "operation_action",
    "biz_member_cluster",
    "marketing_activity_page",
    "marketing_activity_match_status",
    "marketing_activity_match_keywords",
    "gender",
    "match_label",
    "has_refund_demand",
    "has_escalation",
    "session_id",
    "phone_number",
    "product_name",
    "message_subtype",
    "message_type",
    "channel_id",
    "channel_name",
    "user_identity",
    "four_product_level",
    "four_operation",
]

TEXT_FIELDS = [
    "content",
    "cs_reply",
    "feedback_thought",
    "complaint_content",
    "customer_key_appeal",
    "cs_key_action",
    "model_reasoning",
    "latent_need",
    "latent_need_reason",
    "match_info",
]

DATE_FIELDS = ["service_time", "end_time"]

NUMERIC_FIELDS = {
    "duration_hours": "float",
    "duration_minutes": "float",
    "day": "integer",
    "hour": "integer",
    "age": "integer",
}

MULTI_VALUE_FIELDS = {
    "label_group",
    "primary_labels",
    "secondary_labels",
    "tertiary_labels",
    "scene_event",
    "scene_emotion",
    "scene_service_type",
    "insight_dimension",
    "customer_keywords",
    "cs_keywords",
    "biz_type",
    "operation_action",
    "biz_member_cluster",
    "marketing_activity_match_keywords",
    "match_label",
    "four_product_level",
    "four_operation",
}

NEGATIVE_EMOTIONS = ["愤怒", "厌恶", "恐惧", "悲伤"]


def index_mapping() -> dict:
    from .mapping_loader import load_index_mapping

    return load_index_mapping()
