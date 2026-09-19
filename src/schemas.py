#  Defines the data contract between every stage of the pipeline 
# using Pydantic, guaranteeing the final JSON payload strictly 
# matches the format expected by the scoring server.


from pydantic import BaseModel, Field
from typing import Optional, List

# The Data Contract for document extraction
class ShippingDetails(BaseModel):
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    notify_party: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    container_count: Optional[int] = None      # Must parse to int
    gross_weight_kg: Optional[float] = None    # Must parse to float