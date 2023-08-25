import argparse

from pathlib import Path

from apple_health_data.config_processor import (
    setup_logger,
    create_folder_tree,
    process_biodata,
    move_or_copy_export_zip,
    extract_export_xml,
    parse_export_xml_parameters,
    wrangle_parsed_data,
    summarize_parameters,
    collate_summaries,
    export_collated_summaries
)

from apple_health_data.core.logger import VerbosityLogger
from apple_health_data.file_operations import write_json, read_json
from apple_health_data.utils import save_dataframe


def display_message(
    msg: str = "",
    verbose: bool = True,
    vlogger: VerbosityLogger = VerbosityLogger(),
    level: str = "info",
) -> None:
    if verbose:
        vlogger.log(level, msg, 0)
    else:
        print(msg)


# Main script
if __name__ == "__main__":
    # Load the configuration from config.toml
    config_json = Path("apple_health_data") / Path("config.json")
    config = read_json(config_json)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Script to summarize Apple health data exported from iPhone"
    )
    parser.add_argument("--export-zip", type=str, help="Path to export.zip file")
    parser.add_argument(
        "--move", default=False, help="Move export.zip file instead of copying"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Displays log messages on screen even if logging is disabled",
    )

    parser.add_argument(
        "--compression",
        type=str,
        choices=["zstd", "snappy", "gzip", "lzo"],
        default=None,
        help="Compression codec for JSON data (zstd, snappy, gzip, or lzo). Default is no compression.",
    )

    args = parser.parse_args()

    export_zip = Path(args.export_zip) or Path("export.zip")

    # Initialize logging
    logger_name = "apple-health-data"
    vlogger = setup_logger(
        stream_logging={"enabled": args.verbose},
        file_logging={
            "enabled": config["logging"]["enabled"],
            "folder": config["logging"]["folder"],
        },
        log_verbosity=config["logging"]["verbosity"],
        logger_name=logger_name,
    )
    vlogger.info("Logging initialized.", 0)

    folders = create_folder_tree(
        config["folders"], export_zip=export_zip, vlogger=vlogger
    )

    try:
        display_message(
            msg="Script execution started.", verbose=args.verbose, vlogger=vlogger
        )

        display_message(
            msg=f"Reading config data from {config_json}",
            verbose=args.verbose,
            vlogger=vlogger,
        )

        biodata_file = folders["summarized"] / Path("biodata.json")
        process_biodata(
            biodata=config["bio"],
            file_path=biodata_file,
            vlogger=vlogger,
            compression_codec=None,
        )

        vlogger.info("Copying export.zip to data/raw folder", 0)
        move_or_copy_export_zip(export_zip, folders["raw"], move=args.move)

        vlogger.info("Extracting export.xml from export.zip", 0)
        export_zip_path = Path(folders["raw"]).joinpath(Path(export_zip).name)
        export_xml = extract_export_xml(
            export_zip_path, folders["raw"], vlogger=vlogger
        )

        parse_export_xml_parameters(
            export_xml=export_xml, target_directory=folders["parsed"], vlogger=vlogger
        )

        wrangler_kwargs = []
        parameters = config["parameters"].copy()  # important to copy!
        for param in parameters:
            kwargs = param["data_wrangler"]
            kwargs["file_path"] = folders["parsed"] / kwargs["file_path"]
            wrangler_kwargs.append(kwargs)

        wrangled_filemap = wrangle_parsed_data(
            wrangler_kwargs=wrangler_kwargs,
            wrangled_folder=folders["wrangled"],
            compression_codec=args.compression,
            vlogger=vlogger,
        )

        wrangled_json = write_json(
            data=wrangled_filemap,
            file_path=folders["wrangled"] / Path("wrangled_filenames.json"),
            compression_codec=None,
            vlogger=vlogger,
        )

        wrangled_filemap = read_json(file_path=Path(wrangled_json), vlogger=vlogger)

        # wrangled_filemap = read_json(
        #     file_path=Path(folders["wrangled"] / Path("wrangled_filenames.json")), vlogger=vlogger
        # )

        summaries_filemap = summarize_parameters(
            wrangled_filemap=wrangled_filemap,
            parameters=config["parameters"],
            summarized_folder=folders["summarized"],
            compression_codec=args.compression,
            vlogger=vlogger,
        )

        summaries_json = write_json(
            data=summaries_filemap,
            file_path=folders["summarized"] / Path("summary_filenames.json"),
            compression_codec=None,
            vlogger=vlogger,
        )

        summaries_filemap = read_json(
            file_path=Path(summaries_json), vlogger=vlogger
        )

        # summaries_filemap = read_json(
        #     file_path=Path(folders["summarized"] / Path("summary_filenames.json")),
        #     vlogger=vlogger,
        # )

        summaries = collate_summaries(
            type_summaries=summaries_filemap,
            vlogger=vlogger,
        )

        export_collated_summaries(
            summaries=summaries,
            summarized_folder=folders["summarized"],
            file_format="csv",
            index=False
        )   

        display_message(
            msg="Script execution completed successfully.",
            verbose=args.verbose,
            vlogger=vlogger,
        )

    except Exception as e:
        display_message(
            msg=f"Script execution failed: {e}",
            verbose=args.verbose,
            vlogger=vlogger,
            level="error",
        )
