import pandas as pd
import mmh3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
import pandas as pd
from pathlib import Path
from pydantic import BaseModel, Field, field_serializer, ConfigDict


def hash_model(data_tuple: Tuple[Union[int, str, list, dict, pd.DataFrame]]) -> int:
    hashed_vals = []

    for data in data_tuple:
        if isinstance(data, pd.DataFrame):
            hashed_val = pd.util.hash_pandas_object(data).sum()
        else:
            hashed_val = mmh3.hash(str(data))

        hashed_vals.append(hashed_val)

    combined_hash = mmh3.hash(str(hashed_vals))
    return combined_hash


def get_df_dtypes(df: pd.DataFrame) -> Dict[str, List[str]]:
    col_types = (
        df.dtypes.groupby(df.dtypes.apply(lambda x: str(x)))
        .apply(lambda x: x.index.tolist())
        .to_dict()
    )

    return col_types


class DataFrameModel(BaseModel):
    dataframe: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]
    dtypes: Optional[Dict[str, List[str]]] = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    def __init__(self, **data: Any):
        super().__init__(**data)

        object.__setattr__(self, "dataframe", pd.DataFrame(self.dataframe))

        if self.dtypes is not None:
            self.typecast_cols()

    def __hash__(self):
        return hash_model((self.dataframe, self.dtypes))

    @field_serializer("dataframe")
    def serialize_df(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        return data.to_dict(orient="records")

    def typecast_cols(self):
        for col_type, columns in self.dtypes.items():
            for col in columns:
                if col in self.dataframe.columns:
                    if col_type.startswith("datetime64"):
                        offset = col.find(", ")
                        if offset != -1:
                            tz = col[offset + 2 :]
                            self.dataframe[col] = pd.to_datetime(
                                self.dataframe[col], utc=True, tz=tz
                            )
                        else:
                            self.dataframe[col] = pd.to_datetime(self.dataframe[col])
                    else:
                        self.dataframe[col] = self.dataframe[col].astype(col_type)


def save_dataframe(
    df: pd.DataFrame, file_path: Path, file_format: str = "csv", *args, **kwargs
) -> None:
    getattr(df, f"to_{file_format}")(file_path, *args, **kwargs)


def dict_to_string(dictionary: Dict[str, Any], separator: str) -> str:
    items_as_strings = [f"{key}{separator}{value}" for key, value in dictionary.items()]
    combined_str = separator.join(items_as_strings)
    return combined_str
