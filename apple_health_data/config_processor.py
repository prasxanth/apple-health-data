import os
import shutil
import logging
import sys
import datetime
import zipfile
import pandas as pd
from dateutil.parser import parse as date_parser
from dateutil.relativedelta import relativedelta
from pathlib import Path
from typing import Dict, Optional, Union, Any, List
from pydantic import TypeAdapter

from apple_health_data.file_operations import (
    remove_filename_extensions,
    create_folder,
    get_last_modified_date,
    copy_file,
    move_file,
    rename_files,
    write_json,
    read_json,
)

from apple_health_data.utils import dict_to_string, save_dataframe

from apple_health_data.core.logger import (
    ExtraInfoFormatter,
    VerbosityLogger,
    VerbosityLoggerConfig,
)
from apple_health_data.core.parser import HealthDataExtractor
from apple_health_data.core.summarizer import DataWrangler, TypeSummary


def process_biodata(
    biodata: Dict[str, Any],
    file_path: Path,
    vlogger: VerbosityLogger = VerbosityLogger(),
    compression_codec: Union[str, None] = None,
) -> None:
    vlogger.info("[START] Process biodata", 0)

    vlogger.info(f"Calculating age from date of birth", 1)

    dob = date_parser(biodata["dob"])
    current_date = datetime.datetime.now()
    age = relativedelta(current_date, dob)
    biodata["age"] = {"years": age.years, "months": age.months, "days": age.days}

    vlogger.info(f"Saving biodata to {file_path}", 1)
    write_json(data=biodata, file_path=file_path, compression_codec=compression_codec)

    vlogger.info("[END] Process biodata", 0)


def setup_file_handler(
    logger: logging.Logger, log_folder: Path, formatter: logging.Formatter
):
    log_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
    log_filename = log_folder / Path(log_filename)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def setup_stream_handler(logger: logging.Logger, formatter: logging.Formatter):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def setup_logger(
    stream_logging: Dict[str, Optional[bool]] = {},
    file_logging: Dict[str, Union[bool, Path, None]] = {},
    log_verbosity: int = 0,
    logger_name: str = "apple-health-data-log",
):
    if file_logging["enabled"] is None and stream_logging["enabled"] is None:
        return VerbosityLogger()

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    formatter = ExtraInfoFormatter(
        "%(asctime)s [%(levelname)s] %(moduleName)s.%(className)s.%(methodName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_logging = {**{"enabled": False, "formatter": None}, **stream_logging}
    file_logging = {
        **{"enabled": False, "folder": None, "formatter": None},
        **file_logging,
    }

    if file_logging["enabled"]:
        if file_logging["folder"] is None:
            file_logging["folder"] = Path(".")
        else:
            file_logging["folder"] = Path(file_logging["folder"])
        if file_logging["formatter"] is None:
            file_logging["formatter"] = formatter
        setup_file_handler(logger, file_logging["folder"], file_logging["formatter"])

    if stream_logging["enabled"]:
        if stream_logging["formatter"] is None:
            stream_logging["formatter"] = formatter
        setup_stream_handler(logger, stream_logging["formatter"])

    vlogger = VerbosityLogger(logger_name=logger_name, verbosity=log_verbosity)

    if file_logging["enabled"]:
        create_folder(file_logging["folder"], vlogger=vlogger)

    return vlogger


def create_folder_tree(
    config_data: Dict,
    export_zip: Path,
    parent_path: Path = Path(),
    vlogger: VerbosityLogger = VerbosityLogger(),
    export_date_log_message: bool = True,
) -> Dict[str, Path]:
    export_date = get_last_modified_date(export_zip)

    if export_date_log_message:
        vlogger.info(f"Last modified date of export.zip: {export_date}", 1)

    folders = {}
    for item in config_data.get("contents", []):
        if item["name"] == "src":
            continue  # Skip the "src" directory

        if item["name"] == "export_date":
            item["name"] = export_date

        folder_path = parent_path / item["name"]

        if item["type"] == "directory":
            if folder_path.exists():
                vlogger.info(f"Folder {folder_path} already exists.", 1)
            else:
                folder_path.mkdir(parents=True, exist_ok=False)
                vlogger.info(f"{folder_path} created successfully.", 1)

            if "contents" in item:
                subfolders = create_folder_tree(
                    item, export_zip, folder_path, vlogger, False
                )
                folders.update(subfolders)

            folders[item["name"]] = Path(folder_path)

    return folders


def move_or_copy_export_zip(
    source_path: Path, destination_path: Path, move: bool = False
) -> None:
    export_zip = destination_path / source_path.name
    if export_zip.is_file():
        export_zip.unlink()

    if move:
        move_file(source_path, destination_path)
    else:
        copy_file(source_path, destination_path)


def extract_export_xml(
    export_zip_file_path: Path,
    target_directory: Path,
    vlogger: VerbosityLogger = VerbosityLogger(),
) -> Union[Path, None]:
    """
    Extract the apple_health_export/export.xml file from a zip file,
    excluding the apple_health_export folder. Delete the apple_health_export folder after extraction.
    """
    xml_file_path = None
    try:
        with zipfile.ZipFile(export_zip_file_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename == "apple_health_export/export.xml":
                    xml_file_path = target_directory / "export.xml"
                    with zip_ref.open(file_info) as source, open(
                        xml_file_path, "wb"
                    ) as target:
                        shutil.copyfileobj(source, target)
                    break
        vlogger.info("Extraction completed successfully.", 1)
    except (zipfile.BadZipFile, FileNotFoundError, OSError) as e:
        vlogger.error(f"Extraction failed: {e}", 1)

    return xml_file_path


def parse_export_xml_parameters(
    export_xml: str, target_directory: str, vlogger: VerbosityLogger = VerbosityLogger()
) -> None:
    vlogger.info("[START] Parse parameters in XML to CSV", 0)
    data = HealthDataExtractor(
        path=export_xml, target_directory=target_directory, vlogger=vlogger
    )
    data.report_stats()
    data.extract()
    vlogger.info("[END] Parse parameters in XML to CSV", 0)

    vlogger.info("Renaming CSV files in parsed folder", 0)
    rename_files(
        source_directory=target_directory, target_extension=".csv", vlogger=vlogger
    )


def wrangle_parsed_data(
    wrangler_kwargs: List[Dict[str, Any]],
    wrangled_folder: Path,
    compression_codec: Union[str, None] = None,
    vlogger: VerbosityLogger = VerbosityLogger(),
) -> Dict[Path, Path]:
    vlogger_config = VerbosityLoggerConfig(
        name=vlogger.logger_name, verbosity=vlogger.verbosity
    )

    vlogger.info(f"[START] Wrangle parsed data", 0)

    wrangled_filemap = {}
    for kwargs in wrangler_kwargs:
        parsed_file = kwargs["file_path"]
        param_name = remove_filename_extensions(parsed_file.name)

        vlogger.info(f"[START] Wrangling parsed data from {parsed_file}", 0)
        wrangled_data = DataWrangler(**kwargs, vlogger_config=vlogger_config)
        vlogger.info(f"[END] Wrangling parsed data from {parsed_file}", 0)

        wrangled_file = write_json(
            data=wrangled_data.model_dump(exclude={"vlogger_config"}),
            file_path=wrangled_folder / param_name,
            compression_codec=compression_codec,
            vlogger=vlogger,
        )

        wrangled_filemap.update({str(parsed_file): str(wrangled_file)})

    vlogger.info(f"[END] Wrangle parsed data", 0)

    return wrangled_filemap


def summarize_parameters(
    wrangled_filemap: Dict[str, str],
    parameters: Dict[str, Dict[str, Any]],
    summarized_folder: Path,
    compression_codec: Union[str, None] = None,
    vlogger: VerbosityLogger = VerbosityLogger(),
) -> Dict[str, TypeSummary]:
    wrangled_filemap = {
        str(Path(k).name): str(v) for k, v in wrangled_filemap.copy().items()
    }

    vlogger_config = VerbosityLoggerConfig(
        name=vlogger.logger_name, verbosity=vlogger.verbosity
    )

    type_summaries = {}
    for param in parameters:
        parsed_csv = Path(param["data_wrangler"]["file_path"]).name
        wrangled_file = Path(wrangled_filemap[parsed_csv])

        vlogger.info(f"Reading wrangled data from {wrangled_file}", 0)
        wrangled_data = read_json(file_path=wrangled_file)
        wrangled_obj = TypeAdapter(DataWrangler).validate_python(wrangled_data)

        param_type = wrangled_data["type"]
        param_name = remove_filename_extensions(wrangled_file.name, remove_all=True)

        try:
            vlogger.info(f"[START] Summarize parameter: {param_type}", 0)

            obj = param["type_summary"]
            if "sweep" in param and param["sweep"] is not None:
                summarized_files = []

                for sweep_vals in param["sweep"]:
                    merged_obj = obj.copy()
                    merged_obj.update(sweep_vals)

                    summary = TypeSummary(
                        wrangled_data=wrangled_obj,
                        vlogger_config=vlogger_config,
                        **merged_obj,
                    )

                    settings_str = dict_to_string(
                        dictionary=sweep_vals, separator="-"
                    ).lower()

                    summarized_json = write_json(
                        data=summary.model_dump(
                            round_trip=True, exclude={"wrangled_data", "vlogger_config"}
                        ),
                        file_path=(
                            summarized_folder / f"{param_name}-{settings_str}.json"
                        ),
                        compression_codec=compression_codec,
                        vlogger=vlogger,
                    )

                    summarized_files.append(str(summarized_json))

                type_summaries[str(wrangled_file)] = summarized_files
            else:
                summary = TypeSummary(
                    wrangled_data=wrangled_obj, vlogger_config=vlogger_config, **obj
                )

                summarized_json = write_json(
                    data=summary.model_dump(
                        round_trip=True, exclude={"wrangled_data", "vlogger_config"}
                    ),
                    file_path=summarized_folder / f"{param_name}.json",
                    compression_codec=compression_codec,
                    vlogger=vlogger,
                )

                type_summaries[wrangled_file] = summarized_json

            vlogger.info(f"[END] Summarize parameter: {param_type}", 0)

        except Exception as e:
            vlogger.error(f"Error summarizing data for parameter {param_type}: {e}", 0)

    return type_summaries


def collate_summaries(
    type_summaries: Dict[str, Any],
    vlogger: Optional[VerbosityLogger] = VerbosityLogger(),
) -> Dict[str, pd.DataFrame]:
    vlogger_config = VerbosityLoggerConfig(
        name=vlogger.logger_name, verbosity=vlogger.verbosity
    )

    vlogger.info("[START] Tabulate summaries", 0)

    tables = {}
    for wrangled_file, files in type_summaries.items():
        dfs = []
        measures = None
        for file in files:
            vlogger.info(f"Tabulating data from {file}", 1)
            ts_adapater = TypeAdapter(TypeSummary)

            vlogger.info(f"Reading summarized data from {file}", 0)
            ts_data = read_json(file_path=Path(file))
            ts_data["vlogger_config"] = vlogger_config
            ts_obj = ts_adapater.validate_python(ts_data)

            if measures is None:
                measures = ts_obj.measures
            else:
                if measures != ts_obj.measures:
                    vlogger.error(
                        f"Cannot collate summaries from {file} as measures are different",
                        0,
                    )

            dfs.append(ts_obj.tabulate())

        vlogger.info(f"Collating sweep summaries", 1)
        key = remove_filename_extensions(Path(wrangled_file).name, remove_all=True)
        tables[key] = pd.concat(dfs, axis=0)

    vlogger.info("[END] Tabulate summaries", 0)

    return tables


def export_collated_summaries(
    summaries: Dict[str, pd.DataFrame],
    summarized_folder: Union[str, Path],
    file_format: str = "csv",
    *args,
    **kwargs,
) -> None:
    for param, summary in summaries.items():
        save_dataframe(
            df=summary,
            file_path=summarized_folder / f"{param}-summary.{file_format}",
            file_format=file_format,
            *args,
            **kwargs,
        )
