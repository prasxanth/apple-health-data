# Apple Health Data Export Readme

Welcome to the Apple Health Data Export Readme. This guide provides comprehensive information about the Python script designed to process Apple Health data exported from iPhones. The script is specifically developed to extract and summarize diverse health parameters, granting valuable insights into users' health and fitness activities.

## Prerequisites

Before launching the script, ensure you have the following prerequisites in place:

1. **Python Installation**: The script requires Python to be installed on your system. It is compatible with Python 3.6 and newer versions.

2. **Exported Apple Health Data**: Prior to running the script, export your Apple Health data from your iPhone. This export should be stored in a ZIP file containing the data in XML format.

## Setup

Follow these steps to set up the script for processing your Apple Health data:

1. **Clone or Download**: Clone the repository containing the script files to your local machine or directly download the script files.

2. **Install Python Dependencies**: Install the necessary Python dependencies by executing the following command in your terminal or command prompt:

   ```bash
   pip install argparse pathlib apple_health_data
   ```

3. **Provide Exported ZIP File**: Place the exported ZIP file containing your Apple Health data into the same directory as the script files.

## Configuration

The script relies on a configuration file named `config.json` to customize the processing of Apple Health data. This file should reside in the `apple_health_data` directory. It contains settings concerning logging, folder paths, and other parameters used during data processing.

To modify the configuration, open the `config.json` file using a text editor and adjust the values as necessary. The configuration parameters are self-explanatory and can be tailored to meet your specific requirements.

## Using the Script

Execute the script using the following command in your terminal or command prompt:

```bash
python <path_to_script.py> --export-zip <path_to_export_zip> [--move] [--verbose]
```

### Command-line Arguments:

- `--export-zip`: (Required) Specify the path to the exported ZIP file containing Apple Health data in XML format.

- `--move`: (Optional) Use this flag to move the export ZIP file instead of copying it to the data processing folder. If not provided, the script will copy the ZIP file.

- `--verbose`: (Optional) Display log messages on the screen even if logging is disabled in the configuration.

**Note:** If any of the command-line arguments are omitted, default values will be used. If `--export-zip` is not provided, the script will look for an `export.zip` file in the same directory as the script.

## Data Processing

The script carries out the Apple Health data processing through these steps:

1. **Logging Initialization**: The script initializes logging to track progress and processing status.

2. **Folder Setup**: The script creates the required folder structure for data processing based on the configuration.

3. **Biodata Processing**: Biodata (biological information) from the Apple Health export is summarized and saved in JSON format.

4. **Copying Export Zip**: The script either copies or moves the original export ZIP file to the data processing folder.

5. **Export XML Extraction**: The `export.xml` file is extracted from the copied/moved ZIP file.

6. **Parsing Parameters**: Specific parameters are parsed from `export.xml` and stored in separate files as specified in the configuration.

7. **Parameter Summarization**: The script generates summaries of parsed parameters as outlined in the configuration.

## Output

Upon successful execution of the script, various processed files will be available in the output folders as defined in the `config.json` file. The output includes biodata in JSON format, parsed parameter files, and summarized parameter files.

In the case of any errors during execution, the script logs error messages along with relevant details to facilitate troubleshooting.

Certainly, you can add the description of the folder structure to the README in the "Folder Structure" section. This section can provide readers with a clear understanding of how the processed data is organized within the directory. Here's where you can include the description:

### Folder Structure

The script creates a well-organized folder structure to manage the processed data and logs. This structure ensures that data is stored systematically for easy analysis and reference. The main directory is named `data`, and within it, the processed data is organized into different subdirectories:

- **summarized**: This directory contains the summarized data generated from processing the exported Apple Health data. The data is organized based on the parameters defined in the configuration.

- **wrangled**: The `wrangled` directory holds the processed data that has undergone preprocessing and cleaning. This data is ready for further analysis and insights.

- **raw**: The `raw` directory preserves the original exported Apple Health data in its unaltered form. This is the starting point for all processing steps.

- **parsed**: In the `parsed` directory, you'll find the extracted and parsed data. This data includes specific parameters that have been isolated for analysis.

Furthermore, the script generates log files to document the processing progress and any encountered errors. These log files offer valuable insights into the execution of the script, helping with troubleshooting and monitoring.

By maintaining this organized folder structure, the script facilitates efficient data management, ensuring that each stage of the processing pipeline is clearly separated for ease of analysis and reference.

## Disclaimer

The script processes Apple Health data based on the provided configuration. It is crucial to note that the interpretation and utilization of processed data are the responsibility of the user. The script is not intended to replace professional medical advice or diagnosis. For any health-related concerns, always consult qualified healthcare professionals.

## Example Command

To process your Apple Health data using the provided script, utilize the following example command:

```bash
/usr/bin/python3 main.py --export-zip ~/Downloads/export.zip --verbose --compression="gzip"
```

This command executes the `main.py` script with specified options:

- `--export-zip` ~/Downloads/export.zip: This option specifies the path to the Apple Health data export ZIP file that will be processed. The path is set to ~/Downloads/export.zip in this example. Replace this with the actual path to your exported ZIP file.

- `--verbose`: By including this flag, you enable verbose mode. In verbose mode, the script will display log messages on the screen, even if logging is disabled in the configuration. This can be useful for monitoring the script's progress and diagnosing any issues during execution.

- `--compression="gzip"`: This option sets the compression codec for JSON data generated during processing. You can adjust this option to other supported codecs like zstd, snappy, or lzo, or omit it for no compression.

Ensure you meet all prerequisites, set up the configuration file (`config.json`) as instructed in the README, and then run the script.

After successful execution, the processed data will be accessible in the designated output folders as configured. For any issues or errors, the script logs error messages for effective troubleshooting.

Remember, the script is provided "as-is" and is not a substitute for professional medical advice. Always consult with qualified healthcare professionals for health-related concerns.

## Configuration Details

The `config.json` file houses parameters and settings for processing various health data from Apple Health export. Each configuration section corresponds to a specific health parameter, outlining data processing, and analysis settings.

Before running the script, ensure the `config.json` file is updated with accurate file names, target values, intervals, and other parameter-specific settings based on your Apple Health export data and analysis requirements.

Confirm that the CSV files referenced in the configuration are present in the appropriate directories alongside the script files.

---