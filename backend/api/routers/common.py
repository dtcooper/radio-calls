from pydantic.alias_generators import to_camel

from ninja import Schema as BaseSchema


class Schema(BaseSchema):
    class Config(BaseSchema.Config):
        alias_generator = to_camel
        populate_by_name = True


class BaseOut(Schema):
    success: bool = True
