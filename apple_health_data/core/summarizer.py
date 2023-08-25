from typing import Dict, Any, List, Optional, Union
import pandas as pd
from inflection import underscore
from unidecode import unidecode
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, computed_field, root_validator
from pint import UnitRegistry
from functools import cached_property, lru_cache

from apple_health_data.core.logger import VerbosityLoggerConfig
from apple_health_data.utils import hash_model, DataFrameModel, get_df_dtypes


def set_private_fields(cls, public_fields: List[str], values: Dict[str, Any]) -> None:
    for field in public_fields:
        if field in values:
            setattr(cls, f"_{field}", values[field])
        else:
            setattr(cls, f"_{field}", None)


class DataWrangler(BaseModel):
    parsed_data: Optional[
        Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]
    ] = Field(default=None)
    file_path: Optional[Path] = Field(default=None)
    filter_sources: Optional[List[str]] = Field(default=None)
    col_types: Optional[dict] = Field(
        default={
            "object": ["sourceName", "sourceVersion", "device", "type", "unit"],
            "float64": ["value"],
            "datetime64[ns]": ["creationDate", "startDate", "endDate"],
        }
    )
    vlogger_config: VerbosityLoggerConfig = Field(default=VerbosityLoggerConfig())

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    @root_validator(pre=True)
    def deserialize_computed_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        "Prevent recomputing for @computed_field when data is deserialized"
        computed_fields = ["sources", "type", "units", "preprocessed_data"]
        set_private_fields(cls=cls, public_fields=computed_fields, values=values)

        return values

    def __init__(self, **data):
        super().__init__(**data)

        if self.file_path is not None:
            object.__setattr__(self, "parsed_data", self.read_csv())

        if self.parsed_data is not None:
            object.__setattr__(
                self,
                "parsed_data",
                DataFrameModel(dataframe=self.parsed_data, dtypes=self.col_types),
            )

        self.preprocess.cache_clear()

    def __hash__(self):
        return hash_model(
            (
                self.parsed_data,
                self.file_path,
                self.filter_sources,
                self.col_types,
            )
        )

    @property
    def vlogger(self):
        return self.vlogger_config.vlogger

    @computed_field
    @cached_property
    def sources(self) -> Union[List[str], None]:
        if self._sources is None and self.parsed_data is not None:
            self._sources = [
                unidecode(x)
                for x in self.parsed_data.dataframe["sourceName"].unique().tolist()
            ]
            self.vlogger.debug(f"Sources identified as {self._sources}", 1)

        return self._sources

    @computed_field
    @cached_property
    def type(self) -> Union[str, None]:
        if self._type is None and self.parsed_data is not None:
            self._type = self.parsed_data.dataframe["type"].values[0]
            self.vlogger.debug(f"Type from first entry in column is {self._type}", 1)

        return self._type

    @computed_field
    @cached_property
    def units(self) -> Union[str, None]:
        if self._units is None and self.parsed_data is not None:
            self._units = unidecode(self.parsed_data.dataframe["unit"].values[0])
            self.vlogger.debug(f"Units from first entry in column are {self._units}", 1)

        return self._units

    def read_csv(self) -> pd.DataFrame:
        self.vlogger.info(f"[START] Read input file {self.file_path}", 0)

        try:
            with open(str(self.file_path), "r") as file:
                data = pd.read_csv(file, header=0, low_memory=False)
        except FileNotFoundError as e:
            self.vlogger.error(str(e), 0)
            raise e
        except Exception as e:
            self.vlogger.error("Failed to read the CSV file", 0)
            self.vlogger.error(str(e), 0)
            raise e
        else:
            self.vlogger.info(f"[END] Read input file {self.file_path}", 0)

        return data

    @computed_field
    @property
    def preprocessed_data(self) -> Union[DataFrameModel, None]:
        if self._preprocessed_data is None and self.parsed_data is not None:
            self._preprocessed_data = {
                "dataframe": self.preprocess(),
                "dtypes": self.col_types,
            }
            return DataFrameModel(**self._preprocessed_data)
        elif self._preprocessed_data is not None:
            return DataFrameModel(**self._preprocessed_data)
        else:
            return self._preprocessed_data

    @lru_cache(maxsize=128)
    def preprocess(self) -> pd.DataFrame:
        parsed_df = self.parsed_data.dataframe
        self.vlogger.info("[START] Preprocess data", 1)

        processed_data = parsed_df.copy().sort_values(by=["startDate", "endDate"])

        self.vlogger.debug(
            "Removing special characters from the 'sourceName' column", 1
        )
        processed_data["sourceName"] = processed_data["sourceName"].replace(
            {r"[^\x00-\x7F]+": ""}, regex=True
        )

        if self.filter_sources is not None:
            self.vlogger.debug(f"Filter {self.filter_sources} sources.", 1)
            processed_data = processed_data.query("sourceName in @filter_sources")

        self.vlogger.info("[END] Preprocess data", 1)

        return processed_data


class TargetConfig(BaseModel):
    interval: str
    value: float
    units: str


class TypeSummaryNormalizer(BaseModel):
    normalization: Optional[float] = Field(default=None)
    target_config: Optional[TargetConfig] = Field(default=None)
    units: Optional[str] = Field(default=None)
    interval: str = Field(default="1H")
    vlogger_config: VerbosityLoggerConfig = Field(default=VerbosityLoggerConfig())

    ureg: UnitRegistry = UnitRegistry()

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    def __init__(self, **data: Any):
        super().__init__(**data)

        if self.target_config is not None:
            object.__setattr__(
                self, "normalization", self.set_normalization_from_target()
            )

    @property
    def vlogger(self):
        return self.vlogger_config.vlogger

    def set_normalization_from_target(self):
        target_interval = self.target_config.interval
        target_value = self.target_config.value
        target_units = self.target_config.units

        normalization = target_value

        if target_interval != self.interval:
            self.ureg.define("week = 7 * day")
            self.ureg.define("month = 30.4375 * day")
            self.ureg.define("year = 365.25 * day")

            time_unit_mapping = {
                "Y": self.ureg.year,
                "M": self.ureg.month,
                "W": self.ureg.week,
                "D": self.ureg.day,
                "H": self.ureg.hour,
            }

            unit_abbreviation = self.interval[-1]
            if unit_abbreviation in time_unit_mapping:
                self_interval = self.ureg.Quantity(
                    float(self.interval[:-1]), time_unit_mapping[unit_abbreviation]
                )
            else:
                raise ValueError(f"Invalid time unit abbreviation: {unit_abbreviation}")

            unit_abbreviation = target_interval[-1]
            if unit_abbreviation in time_unit_mapping:
                target_interval = self.ureg.Quantity(
                    float(target_interval[:-1]), time_unit_mapping[unit_abbreviation]
                )
            else:
                raise ValueError(
                    f"Invalid target interval time unit abbreviation: {unit_abbreviation}"
                )

            normalization *= self_interval.to(target_interval).magnitude

        try:
            if target_units != self.units:
                normalization *= self.ureg(self.units).to(target_units).magnitude
        except Exception:
            self.vlogger.error("No matching unit found in UnitRegistry", 1)

        return normalization

    def normalize(self, summary, measures):
        self.vlogger.debug("[START] Calculate normalized measures", 1)

        normalized_measures = [f"normalized_{meas}" for meas in measures]
        summary[normalized_measures] = summary[measures] / self.normalization

        self.vlogger.debug("[END] Calculate normalized measures", 1)


class TypeSummary(BaseModel):
    wrangled_data: Optional[DataWrangler] = Field(default=DataWrangler())
    measures: Optional[List[str]] = Field(default=["mean"])
    interval: str = Field(default="1H")
    ffill: Optional[bool] = Field(default=False)
    normalization: Optional[float] = Field(default=None)
    target_config: Optional[TargetConfig] = Field(default=None)
    agg_sources: Optional[str] = Field(default="mean")
    units: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    vlogger_config: VerbosityLoggerConfig = Field(default=VerbosityLoggerConfig())

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra="allow")

    @root_validator(pre=True)
    def deserialize_computed_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        "Prevent recomputing for @computed_field when data is deserialized"
        computed_fields = ["sources", "summary"]
        set_private_fields(cls=cls, public_fields=computed_fields, values=values)

        return values

    def __init__(self, **data):
        super().__init__(**data)

        if self.units is None and self.wrangled_data is not None:
            object.__setattr__(self, "units", self.wrangled_data.units)

        if self.type is None and self.wrangled_data is not None:
            object.__setattr__(self, "type", self.wrangled_data.type)

        self._normalizer = TypeSummaryNormalizer(
            normalization=self.normalization,
            target_config=self.target_config,
            units=self.units,
            interval=self.interval,
            vlogger_config=self.vlogger_config,
        )

        if self._normalizer.normalization is not None:
            object.__setattr__(self, "normalization", self._normalizer.normalization)

        self.summarize.cache_clear()

    def __hash__(self):
        return hash_model(
            (
                self.wrangled_data,
                self.measures,
                self.interval,
                self.ffill,
                self.normalization,
                self.target_config,
                self.agg_sources,
                self.units,
            )
        )

    @property
    def vlogger(self):
        return self.vlogger_config.vlogger

    @cached_property
    def normalizer(self) -> TypeSummaryNormalizer:
        return self._normalizer

    @computed_field
    @cached_property
    def sources(self) -> Union[List[str], None]:
        if self._sources is None and self.wrangled_data is not None:
            self._sources = (
                self.wrangled_data.filter_sources or self.wrangled_data.sources
            )

        return self._sources

    @computed_field
    @property
    def summary(self) -> Union[DataFrameModel, None]:
        if self._summary is None and self.wrangled_data is not None:
            df = self.summarize()
            return DataFrameModel(dataframe=df, dtypes=get_df_dtypes(df))
        elif self._summary is not None:
            return DataFrameModel(**self._summary)
        else:
            return self._summary

    @lru_cache(maxsize=128)
    def summarize(self) -> pd.DataFrame:
        preprocessed_data = self.wrangled_data.preprocessed_data.dataframe

        self.vlogger.info("[START] Calculate statistical summary", 0)
        try:
            self.vlogger.debug("Setting 'startDate' as index", 1)
            preprocessed_data.set_index("startDate", inplace=True)

            self.vlogger.debug(
                "Grouping, resampling, and applying aggregation functions", 2
            )
            result = (
                preprocessed_data.groupby("sourceName")["value"]
                .resample(self.interval)
                .apply(self.agg_sources)
                .reset_index()[["startDate", "value"]]
            )

            if self.ffill:
                self.vlogger.debug(
                    "Filling NaN values after resampling using forward fill", 2
                )
                result["value"].fillna(method="ffill", inplace=True)

            self.vlogger.debug(
                "Calculating desired summary measures for each resampled interval",
                1,
            )
            result = result.groupby(["startDate"]).agg(self.measures)

            self.vlogger.debug("Resetting index and flattening multi-index", 2)
            result.reset_index(inplace=True)
            result.columns = result.columns.map(
                lambda x: x[1] if x[1] != "" else underscore(x[0])
            )

            if self.normalizer.normalization is not None:
                self.normalizer.normalize(result, self.measures)

            self.vlogger.info("[END] Calculate statistical summary", 0)

        except Exception as e:
            self.vlogger.error("Failed to calculate statistical summary", 0)
            self.vlogger.error(str(e), 0)
            raise e

        return result

    @lru_cache(maxsize=128)
    def tabulate(self) -> pd.DataFrame:
        self.vlogger.info("[START] Tabulating data to pandas dataframe", 0)

        df_metadata = pd.DataFrame(
            {
                "type": [self.type],
                "sources": [self.sources],
                "units": [self.units],
                "normalization": [self.normalizer.normalization],
                "interval": [self.interval],
            }
        )

        df_summary = self.summary.dataframe
        df_metadata = pd.concat([df_metadata] * len(df_summary), ignore_index=True)
        df = pd.concat([df_metadata, df_summary], axis=1)

        self.vlogger.info("[End] Tabulating data to pandas dataframe", 0)

        return df
