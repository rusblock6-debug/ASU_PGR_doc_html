# ruff: noqa: D100, D101, W505, D106
from pydantic import BaseModel, Field


class BaseEkiperEvent(BaseModel):
    class Metadata(BaseModel):
        vehicle_id: str
        sensor_type: str
        timestamp: int

    class Data(BaseModel):
        status: str
        value: int

    data: Data = Field(json_schema_extra={"parquet_flatten_root": True})
    metadata: Metadata = Field(json_schema_extra={"parquet_flatten_root": True})


class BaseEkiperDS(BaseModel):
    class Metadata(BaseModel):
        bort: str
        timestamp: int

    metadata: Metadata = Field(json_schema_extra={"parquet_flatten_root": True})


class EkiperSpeedDS(BaseEkiperDS):
    class Data(BaseModel):
        speed: int

    data: Data = Field(json_schema_extra={"parquet_flatten_root": True})


class EkiperSpeedEvent(BaseEkiperEvent):
    pass


class EkiperWeightDS(BaseModel):
    class Metadata(BaseModel):
        bort: str
        timestamp: int

    class Data(BaseModel):
        weight: int

    data: Data = Field(json_schema_extra={"parquet_flatten_root": True})
    metadata: Metadata = Field(json_schema_extra={"parquet_flatten_root": True})


# Example payload for EkiperWeightEvent:
# {'metadata': {'vehicle_id': 'АС26', 'sensor_type': 'weight', 'timestamp': 1757284285.0},
#  'data': {'status': 'empty', 'value': 0}}
class EkiperWeightEvent(BaseEkiperEvent):
    pass


# Example payload for EkiperGpsDS:
# {'data': {'height': None, 'lat': 58.172065, 'lon': 59.820997},
#  'metadata': {'bort': 'АС26', 'timestamp': 1757284998}}
class EkiperGpsDS(BaseEkiperDS):
    class Data(BaseModel):
        height: float | None
        lat: float | None
        lon: float | None
    data: Data = Field(json_schema_extra={"parquet_flatten_root": True})

class EkiperFuelDS(BaseEkiperDS):
    class Data(BaseModel):
        fuel: float

    data: Data = Field(json_schema_extra={"parquet_flatten_root": True})

class EkiperFuelEvent(BaseEkiperEvent):
    pass


class EkiperVibroEvent(BaseEkiperEvent):
    pass
