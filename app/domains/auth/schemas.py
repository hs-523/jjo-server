from pydantic import BaseModel, ConfigDict, StrictBool, Field

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

class GoogleRequest(Input):
    id_token: str = Field(min_length=1)

class Agreements(Input):
    service_terms: StrictBool
    privacy_collection_use: StrictBool
    marketing: StrictBool = False

class SignupRequest(Input):
    signup_token: str = Field(min_length=1)
    agreements: Agreements
