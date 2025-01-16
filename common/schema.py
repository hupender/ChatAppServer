from marshmallow import EXCLUDE, Schema


class ModelSchema(Schema):

    class Meta:
        unknown = EXCLUDE