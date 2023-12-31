# -*- coding: utf-8 -*-
"""
applehealthdata.py: Extract data from Apple Health App's export.xml.
Copyright (c) 2016 Nicholas J. Radcliffe
Licence: MIT
"""
import os
import re

from xml.etree import ElementTree
from collections import Counter, OrderedDict

from typing import Union
from apple_health_data.core.logger import VerbosityLogger


__version__ = "1.3"

RECORD_FIELDS = OrderedDict(
    (
        ("sourceName", "s"),
        ("sourceVersion", "s"),
        ("device", "s"),
        ("type", "s"),
        ("unit", "s"),
        ("creationDate", "d"),
        ("startDate", "d"),
        ("endDate", "d"),
        ("value", "n"),
    )
)

ACTIVITY_SUMMARY_FIELDS = OrderedDict(
    (
        ("dateComponents", "d"),
        ("activeEnergyBurned", "n"),
        ("activeEnergyBurnedGoal", "n"),
        ("activeEnergyBurnedUnit", "s"),
        ("appleExerciseTime", "s"),
        ("appleExerciseTimeGoal", "s"),
        ("appleStandHours", "n"),
        ("appleStandHoursGoal", "n"),
    )
)

WORKOUT_FIELDS = OrderedDict(
    (
        ("sourceName", "s"),
        ("sourceVersion", "s"),
        ("device", "s"),
        ("creationDate", "d"),
        ("startDate", "d"),
        ("endDate", "d"),
        ("workoutActivityType", "s"),
        ("duration", "n"),
        ("durationUnit", "s"),
        ("totalDistance", "n"),
        ("totalDistanceUnit", "s"),
        ("totalEnergyBurned", "n"),
        ("totalEnergyBurnedUnit", "s"),
    )
)

FIELDS = {
    "Record": RECORD_FIELDS,
    "ActivitySummary": ACTIVITY_SUMMARY_FIELDS,
    "Workout": WORKOUT_FIELDS,
}


PREFIX_RE = re.compile("^HK.*TypeIdentifier(.+)$")
ABBREVIATE = True


def format_freqs(counter):
    """
    Format a counter object for display.
    """
    return "; ".join("%s: %d" % (tag, counter[tag]) for tag in sorted(counter.keys()))


def format_value(value, datatype):
    """
    Format a value for a CSV file, escaping double quotes and backslashes.
    None maps to empty.
    datatype should be
        's' for string (escaped)
        'n' for number
        'd' for datetime
    """
    if value is None:
        return ""
    elif datatype == "s":  # string
        return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')
    elif datatype in ("n", "d"):  # number or date
        return value
    else:
        raise KeyError("Unexpected format value: %s" % datatype)


def abbreviate(s, enabled=ABBREVIATE):
    """
    Abbreviate particularly verbose strings based on a regular expression
    """
    m = re.match(PREFIX_RE, s)
    return m.group(1) if enabled and m else s


class HealthDataExtractor(object):
    """
    Extract health data from Apple Health App's XML export, export.xml.
    Inputs:
        path:      Relative or absolute path to export.xml
        verbose:   Set to False for less verbose output
    Outputs:
        Writes a CSV file for each record type found, in the same
        directory as the input export.xml. Reports each file written
        unless verbose has been set to False.
    """

    def __init__(
        self,
        path,
        target_directory=None,
        vlogger: Union[VerbosityLogger, None] = None,
    ):
        self.in_path = path
        self.__vlogger = vlogger
        if target_directory is not None:
            self.directory = target_directory
        else:
            self.directory = os.path.abspath(os.path.split(path)[0])
        with open(path) as f:
            self.log("info", "Reading data from %s . . . " % path, 0)
            self.data = ElementTree.parse(f)
            self.log("info", "done", 0)
        self.root = self.data._root
        self.nodes = list(self.root)
        self.n_nodes = len(self.nodes)
        self.abbreviate_types()
        self.collect_stats()

    @property
    def vlogger(self):
        """
        Get the verbosity logger instance.

        Returns:
            Union[VerbosityLogger, None]: Verbosity logger instance or None.
        """
        return self.__vlogger

    def log(self, level: str, message: str, verbosity: int) -> None:
        """
        Log a message with a specific level and verbosity.

        Args:
            level (str): Log level ('info', 'debug', 'error', etc.).
            message (str): Log message.
            verbosity (int): Verbosity level.
        """
        if self.vlogger is not None:
            self.vlogger.log(level, message, verbosity)

    def count_tags_and_fields(self):
        self.tags = Counter()
        self.fields = Counter()
        for record in self.nodes:
            self.tags[record.tag] += 1
            for k in record.keys():
                self.fields[k] += 1

    def count_record_types(self):
        """
        Counts occurrences of each type of (conceptual) "record" in the data.
        In the case of nodes of type 'Record', this counts the number of
        occurrences of each 'type' or record in self.record_types.
        In the case of nodes of type 'ActivitySummary' and 'Workout',
        it just counts those in self.other_types.
        The slightly different handling reflects the fact that 'Record'
        nodes come in a variety of different subtypes that we want to write
        to different data files, whereas (for now) we are going to write
        all Workout entries to a single file, and all ActivitySummary
        entries to another single file.
        """
        self.record_types = Counter()
        self.other_types = Counter()
        for record in self.nodes:
            if record.tag == "Record":
                self.record_types[record.attrib["type"]] += 1
            elif record.tag in ("ActivitySummary", "Workout"):
                self.other_types[record.tag] += 1
            elif record.tag in ("Export", "Me"):
                pass
            else:
                self.log("warning", "Unexpected node of type %s." % record.tag, 1)

    def collect_stats(self):
        self.count_record_types()
        self.count_tags_and_fields()

    def open_for_writing(self):
        self.handles = {}
        self.paths = []
        for kind in list(self.record_types) + list(self.other_types):
            path = os.path.join(self.directory, "%s.csv" % abbreviate(kind))
            f = open(path, "w")
            headerType = kind if kind in ("Workout", "ActivitySummary") else "Record"
            f.write(",".join(FIELDS[headerType].keys()) + "\n")
            self.handles[kind] = f
            self.log("debug", "Opening %s for writing" % path, 1)

    def abbreviate_types(self):
        """
        Shorten types by removing common boilerplate text.
        """
        for node in self.nodes:
            if node.tag == "Record":
                if "type" in node.attrib:
                    node.attrib["type"] = abbreviate(node.attrib["type"])

    def write_records(self):
        kinds = FIELDS.keys()
        for node in self.nodes:
            if node.tag in kinds:
                attributes = node.attrib
                kind = attributes["type"] if node.tag == "Record" else node.tag
                values = [
                    format_value(attributes.get(field), datatype)
                    for (field, datatype) in FIELDS[node.tag].items()
                ]
                line = ",".join(values) + "\n"
                self.handles[kind].write(line)

    def close_files(self):
        for kind, f in self.handles.items():
            f.close()
            self.log("debug", "Written %s data." % abbreviate(kind), 1)

    def extract(self):
        self.open_for_writing()
        self.write_records()
        self.close_files()

    def report_stats(self):
        self.log("info", "Tags: %s" % format_freqs(self.tags), 0)
        self.log("info", "Fields: %s" % format_freqs(self.fields), 0)
        self.log("info", "Record types: %s" % format_freqs(self.record_types), 0)
