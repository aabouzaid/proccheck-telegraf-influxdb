#!/usr/bin/env python

import os
import sys
import yaml
import socket
import argparse

# ------------------------------------------------------------------ #
# Functions.
# ------------------------------------------------------------------ #

# Open Yaml file.
def openYamlFile(yamlFile):
  # Check if procs list file exists.
  try:
    os.path.isfile(yamlFile)
  except TypeError:
    print "Cannot open YAML file: %s." % (yamlFile)
    sys.exit(1)
  
  # Load content of Yaml file.
  with open(yamlFile, 'r') as procsYamlFile:
    try:
      yamlFileContent = yaml.load(procsYamlFile)
    except yaml.YAMLError as yamlError:
      print(yamlError)

  return yamlFileContent


# Validate main groups names.
def checkProcsListGroups(rowProcList, groupsList, procsListFile):
  if set(rowProcList.keys()) - set(groupsList):
    groupsListFormated = '", "'.join(groupsList)
    print 'One of following groups "%s" is not found in %s' % (groupsListFormated, procsListFile)
    sys.exit(1)


# Merge all groups in one list.
def initProcsList(rowProcList, procsListGroups, procsListFile):
  # Validate names of main groups in procs list file.
  checkProcsListGroups(yamlProcsList, procsListGroups, procsListFile)

  # Formated list.
  formatedProcList = list()

  # Convert procs list to dict (key is proc, and value is pattern).
  byProcName = 'byName'
  byNameDict = dict((key,"") for key in rowProcList[byProcName])
  del rowProcList[byProcName]
  rowProcList[byProcName] = byNameDict

  # Append content of groups to the list.
  for group in rowProcList:
    for proc, pattern in rowProcList[group].iteritems():
      formatedProcList.append({"name": proc, "pattern": pattern})

  return formatedProcList


# Get list of procs in the system.
def getSystemProcs():
  # Empty dict to put all procs in the system in it.
  systemProcs = dict()
  
  # Loop over pids in /proc.
  pidsList = [pid for pid in os.listdir('/proc') if pid.isdigit()]
  
  # Function to get info from any file inside "/proc/PID" path.
  def getProcInfo(pid, pathName):
    try:
      procInfo = open(os.path.join('/proc', pid, pathName), 'rb').read().rstrip('\n').replace('\x00',' ')
    # Handle the error in case any proc did exit while script is still working.
    except IOError:
      pass
    return procInfo
  
  # Add proc PID, command arguments, and bin/exe name.
  for pid in pidsList:
    procArgs = getProcInfo(pid, 'cmdline')
    procBin = getProcInfo(pid, 'comm')
    if procArgs:
      systemProcs.update({pid: {"name": procBin, "args": procArgs}})

  return systemProcs


# Find procs in system procs, and print them.
def findProcsInSystem(procsList, commonOptions):
  # Empty dict for all procs are found in the system.
  procsFound = dict()
  
  # Find if processes are found in the system and add them to dict.
  for proc in procsList:
    procName = proc['name']
    procPattern = proc['pattern']

    for pid, systemProcInfo in systemProcs.iteritems():
      # Find procs by pattern first.
      if procPattern and procPattern in systemProcInfo["args"]:
        procsFound.update({pid: {"name": procName, "exe": systemProcInfo["name"], "pattern": procPattern}})
      # Find procs by bin name.
      elif procName == systemProcInfo["name"]:
        procsFound.update({pid: {"name": procName, "exe": systemProcInfo["name"], "pattern": ""}})
  
  # Loop over procs that are found, and print them in InfluxDB format.
  for pid, procInfo in procsFound.iteritems():
    outputValues = {
      'processName': procInfo["name"],
      'pid': pid,
      'exe': procInfo["exe"],
      'pattern': procInfo["pattern"]
    }
    outputValues.update(commonOptions)
  
    # In InfluxDB format, first group is tags names, and second group is values.
    print ('%(pluginName)s,host=%(hostname)s,process_name=%(processName)s,exe=%(exe)s,pid=%(pid)s'
           ' host=%(hostname)s,process_name="%(processName)s",exe="%(exe)s",pid=%(pid)s,pattern="%(pattern)s"' % outputValues)

# ------------------------------------------------------------------ #
# Main.
# ------------------------------------------------------------------ #

if __name__ == "__main__":
  # Script options.
  parser = argparse.ArgumentParser()
  parser.add_argument("-f","--yml-file", default="./procList.yml", help="Path for processes list in YAML file.")
  args = parser.parse_args()
  
  # Plugin name will be used as measurement name in Telegraf.
  mainOptions = {
    "pluginName": "procCheck",
    "hostname": socket.gethostname()
  }
  
  # Check if any group is missing.
  procsListGroups = [
    'byName',
    'byString',
    'byRegex'
  ]
  
  # Yaml file path.
  procsListFile = args.yml_file
  
  # Get content of Yaml file.
  yamlProcsList = openYamlFile(procsListFile)
  
  # List of monitored processes.
  procsList = initProcsList(yamlProcsList, procsListGroups, procsListFile)

  # Get list with processes running now.
  systemProcs = getSystemProcs()

  # Print processes that founded.
  findProcsInSystem(procsList, mainOptions)
