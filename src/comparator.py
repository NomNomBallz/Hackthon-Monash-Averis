# MEMBER 4's Code (Barry)
# Compares the extracted SI fields against the draft BL fields, applies domain-specific normalization, detects defects, and routes unresolvable cases.
# Input: si_data: ShippingDetails, bl_data: ShippingDetails, and attachment status.
# Output: Discrepancy status ('OK', 'MISMATCH', or 'NEEDS_REVIEW'), defective field names list, and review reason ('missing_attachment', 'unreadable', 'wrong_doc_type', 'missing_value').
# AI Suggested Strategy: Token fuzzy matching (rapidfuzz) for entity names and ports; numeric tolerances and unit conversion (lbs to kg) for weights; container 
# count integer matching. 
