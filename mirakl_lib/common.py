from pydantic import BaseModel


class QueryParams(BaseModel):

    def to_dict(self):
        return {k: v for k, v in self.model_dump().items() if v is not None}


class PaginationQueryParams(QueryParams):
    offset: int
    max: int
