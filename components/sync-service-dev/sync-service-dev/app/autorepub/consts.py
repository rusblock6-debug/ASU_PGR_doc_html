# Separator for combining target_topic with message data
# Two null bytes unlikely to appear in topic names or binary data
# PAYLOAD_SEPARATOR = b"\x00\x00"
# ASCII Unit Separator byte
PAYLOAD_SEPARATOR = b"\x1f"
TOTAL_SEPARATORS = 3
DEBUG_PREFIX = "test"
