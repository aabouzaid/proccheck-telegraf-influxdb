#!/usr/bin/env python

import os
import re
import sys
import yaml
import socket
import argparse

# ------------------------------------------------------------------ #
# Classes/Functions.
# ------------------------------------------------------------------ #

class script(object):
    #
    # Script options.
    def arguments(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-f", "--procs-list-file", default="procList.yml",
                            help="Path for processes list in YAML file.")
        parser.add_argument("-n", "--measurement-name", default="procCheck",
                            help="It will be used as measurement name in Telegraf.")
        arguments = parser.parse_args()
        #
        return arguments

    #
    # Open Yaml file.
    def openYamlFile(self, yamlFile):
        # Check if procs list file exists.
        try:
            os.path.isfile(yamlFile)
        except TypeError:
            print("Cannot open YAML file: %s." % (yamlFile))
            sys.exit(1)

        # Load content of Yaml file.
        with open(yamlFile, 'r') as procsYamlFile:
            try:
                yamlFileContent = yaml.load(procsYamlFile)
            except yaml.YAMLError as yamlError:
                print(yamlError)
        #
        return yamlFileContent

class procCheck(object):
    #
    # Init.
    def __init__(self, monitoredProcsGroups):
        self.monitoredProcsGroups = monitoredProcsGroups

    #
    # Merge all groups in one list.
    def initProcsList(self, yamlMonitoredProcs, monitoredProcsFile):
        # Validate names of main groups in procs list file.
        if set(yamlMonitoredProcs.keys()) - set(self.monitoredProcsGroups):
            groupsListFormated = '", "'.join(self.monitoredProcsGroups)
            print('One of following groups "%s" is not found in %s' % (groupsListFormated, monitoredProcsFile))
            sys.exit(1)

        # Init a list of dicts, where each dict reprecents a proc.
        formatedProcList = list()

        # Convert procs list to dict (key is proc, and value is pattern).
        byProcName = 'byName'
        byNameDict = dict((key,"") for key in yamlMonitoredProcs[byProcName])
        del yamlMonitoredProcs[byProcName]
        yamlMonitoredProcs[byProcName] = byNameDict

        # Append content of groups to the list.
        for group in yamlMonitoredProcs:
            if group == 'byRegex':
               regex = True
            else:
               regex = False

            for proc, pattern in yamlMonitoredProcs[group].items():
                formatedProcList.append({"name": proc, "pattern": pattern, "regex": regex})
        #
        return formatedProcList

    #
    # Get info from any file inside "/proc/PID" path.
    def getProcInfo(self, pid, pathName):
        try:
            procInfo = open(os.path.join('/proc', pid, pathName), 'r').read().rstrip('\n')
        # Handle the error in case any proc did exit while script is still working.
        except IOError:
            pass
        #
        return procInfo

    #
    # Get list of all procs are running in the system.
    def getSystemProcs(self):
        # Empty dict to put all procs in the system in it.
        systemProcs = dict()

        # Loop over pids in /proc.
        pidsList = filter(lambda pid: pid.isdigit(), os.listdir('/proc'))

        # Add proc PID, command arguments, and bin/exe name.
        for pid in pidsList:
            procArgs = self.getProcInfo(pid, 'cmdline')
            procBin = self.getProcInfo(pid, 'comm')
            if procArgs:
                systemProcs.update({pid: {"name": procBin, "args": procArgs}})
        #
        return systemProcs

    #
    # Update dict with proc info.
    def updateProcsDict(self, procsDict, pid, name, exe, pattern="", matchedRegex=""):
        procData = {pid: {"name": name, "exe": exe, "pattern": pattern, "matched_regex": matchedRegex}}
        procsDict.update(procData)
        #
        return procsDict

    #
    # Find procs in system procs.
    def findProcsInSystem(self, monitoredProcs, systemProcs):
        # Empty dict for all procs are found in the system.
        foundProcs = dict()

        # Find if processes are found in the system and add them to dict.
        for proc in monitoredProcs:
            procName = proc['name']
            procPattern = proc['pattern']
            byRegex = proc['regex']

            for pid, systemProcInfo in systemProcs.items():
                sysProcName = systemProcInfo["name"]
                sysProcArgs = systemProcInfo["args"]

                if byRegex:
                    regexPattern = re.compile(procPattern)
                    matchedRegex = regexPattern.findall(sysProcArgs)

                # Find procs by Regex
                if byRegex and regexPattern.search(sysProcArgs):
                   self.updateProcsDict(foundProcs, pid, procName, sysProcName, procPattern, matchedRegex[0])
                # Find procs by pattern (fixed string).
                elif procPattern and procPattern in sysProcArgs:
                   self.updateProcsDict(foundProcs, pid, procName, sysProcName, procPattern)
                # Find procs by name.
                elif procName == sysProcName:
                   self.updateProcsDict(foundProcs, pid, procName, sysProcName)
        #
        return foundProcs

    #
    # Find procs in system procs, and print them.
    def printFoundProcsInSystem(self, foundProcs, measurementName):
        hostname = socket.gethostname()
        # Loop over procs that are found, and print them in InfluxDB format.
        for pid, procInfo in foundProcs.items():
            outputValues = {
                'pluginName': measurementName,
                'hostname': hostname,
                'pid': pid,
                'exe': procInfo["exe"],
                'pattern': procInfo["pattern"],
                'processName': procInfo["name"],
                'matchedRegex': procInfo['matched_regex']
            }

            procOutputKeys = ('%(pluginName)s,host=%(hostname)s,process_name=%(processName)s,exe=%(exe)s,pid=%(pid)s' % outputValues)
            procOutputData = ('host=%(hostname)s,process_name="%(processName)s",exe="%(exe)s",pid=%(pid)s,pattern="%(pattern)s",matched_regex="%(matchedRegex)s"' % outputValues)

            # In InfluxDB format, first group is tags names, and second group is values.
            print("%s %s" % (procOutputKeys, procOutputData))

# ------------------------------------------------------------------ #
# Main.
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    # Check if any group is missing.
    monitoredProcsGroups = [
        'byName',
        'byString',
        'byRegex'
    ]

    # Init script class.
    script = script()

    # Arguments.
    args = script.arguments()
    monitoredProcsFile = args.procs_list_file
    measurementName = args.measurement_name

    # Get content of Yaml file.
    yamlMonitoredProcs = script.openYamlFile(monitoredProcsFile)

    # Init procCheck class.
    pc = procCheck(monitoredProcsGroups)

    # Get list of monitored processes and processes are running now.
    monitoredProcs = pc.initProcsList(yamlMonitoredProcs, monitoredProcsFile)
    systemProcs = pc.getSystemProcs()

    # Find monitored processes are running now on the system.
    foundProcs = pc.findProcsInSystem(monitoredProcs, systemProcs)

    # Print processes that founded.
    pc.printFoundProcsInSystem(foundProcs, measurementName)
