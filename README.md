# Apple Health Data Export Readme

This README file provides an overview of the Python script used to process Apple Health data exported from an iPhone. The script processes the exported data to extract and summarize various health parameters, providing useful insights into the user's health and fitness activities.

## Prerequisites

Before running the script, ensure you have the following prerequisites:

1. **Python**: The script requires Python to be installed on your system. The script is compatible with Python 3.6 and above.

2. **Apple Health Data Export**: Make sure you have exported your Apple Health data from your iPhone. The export should be in a ZIP file containing the data in XML format.

## Setup

To set up the script for processing your Apple Health data, follow these steps:

1. **Clone the Repository or Download the Script Files**: Clone the repository containing the script files to your local machine. Alternatively, you can download the script files directly.

2. **Install Python Dependencies**: Install the required Python dependencies by running the following command in your terminal or command prompt:

3. **Place Exported ZIP File**: Place the exported ZIP file containing your Apple Health data into the same directory as the script files.

## Configuration

The script uses a configuration file named `config.json` to customize the processing of Apple Health data. The `config.json` file should be present in the `apple_health_data` directory. It contains settings related to logging, folder paths, and other parameters used during data processing.

To modify the configuration, open the `config.json` file using a text editor and adjust the values as needed. The parameters in the configuration file are self-explanatory and can be customized according to your requirements.

## Script Usage

To run the script, use the following command in your terminal or command prompt:

```
python <path_to_script.py> --export-zip <path_to_export_zip> [--move] [--verbose]
```

### Command-line Arguments:

- `--export-zip`: (Required) Specify the path to the exported ZIP file containing Apple Health data in XML format.

- `--move`: (Optional) Use this flag to move the export ZIP file instead of copying it to the data processing folder. If not provided, the script will copy the ZIP file.

- `--verbose`: (Optional) Display log messages on the screen even if logging is disabled in the configuration.

**Note:** If any of the command-line arguments are omitted, default values will be used. If `--export-zip` is not provided, the script will look for an `export.zip` file in the same directory as the script.

## Data Processing

The script processes the Apple Health data in the following steps:

1. **Logging Initialization**: The script initializes logging, which records the progress and status of the data processing.

2. **Folder Setup**: The script creates the necessary folder structure for data processing based on the configuration file.

3. **Biodata Processing**: The script summarizes biodata (biological information) from the Apple Health export and stores it in JSON format.

4. **Copying Export Zip**: The script copies or moves the original export ZIP file to the data processing folder.

5. **Export XML Extraction**: The script extracts the `export.xml` file from the copied/moved ZIP file.

6. **Parsing Parameters**: The script parses specific parameters from the `export.xml` file and stores them in separate files according to the configuration.

7. **Parameter Summarization**: The script summarizes the parsed parameters as specified in the configuration.

## Output

Upon successful execution of the script, various processed files will be available in the output folders as defined in the `config.json` file. The output will include biodata in JSON format, parsed parameter files, and summarized parameter files.

In case of any errors during execution, the script will log the error messages along with relevant details to facilitate troubleshooting.

## Disclaimer

This script processes Apple Health data based on the provided configuration. The interpretation and usage of the processed data are the responsibility of the user. The script is not intended to be a substitute for professional medical advice or diagnosis. Always consult with qualified healthcare professionals for any health-related concerns.

## Sample Command Example

To process your Apple Health data using the provided script, you can use the following example command:

```
/usr/bin/python3 main.py --export-zip ~/Downloads/export.zip --verbose --compression="gzip"
```

This command will execute the `main.py` script with the specified options:

- `--export-zip`: The path to the Apple Health data export ZIP file. In this example, it is set to `~/Downloads/export.zip`, but you should replace it with the actual path to your exported ZIP file.

- `--verbose`: This flag will enable verbose mode, displaying log messages on the screen even if logging is disabled in the configuration.

Make sure you have met all the prerequisites and have set up the configuration file (`config.json`) as described in the README before running the script.

After successful execution, the processed data will be available in the specified output folders as defined in the configuration file. If any issues or errors occur during execution, the script will log the error messages for troubleshooting.

Remember that the script is provided as-is and is not a substitute for professional medical advice. Always consult with qualified healthcare professionals for any health-related concerns.

## Configuration Details

The `config.json` file contains parameters and settings used for processing various health data from Apple Health export. Each section in the configuration corresponds to a specific health parameter and defines how the data should be processed and analyzed.

Before running the script, make sure to update the `config.json` file with accurate file names, target values, intervals, and other parameter-specific settings based on your Apple Health export data and your analysis requirements.

Ensure that the CSV files referenced in the configuration are present in the appropriate directories alongside the script files.

---
