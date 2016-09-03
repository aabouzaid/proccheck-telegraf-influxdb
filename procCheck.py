#!/usr/bin/env python

import os
import re
import sys
import yaml
import socket
import argparse

# ------------------------------------------------------------------ #
# Functions.
# ------------------------------------------------------------------ #

#
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

#
# Validate main groups names.
def checkProcsListGroups(rowProcList, groupsList, procsListFile):
  if set(rowProcList.keys()) - set(groupsList):
    groupsListFormated = '", "'.join(groupsList)
    print 'One of following groups "%s" is not found in %s' % (groupsListFormated, procsListFile)
    sys.exit(1)

#
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
    if group == 'byRegex':
      regex = True
    else:
      regex = False

    for proc, pattern in rowProcList[group].iteritems():
      formatedProcList.append({"name": proc, "pattern": pattern, "regex": regex})

  return formatedProcList

#
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

#
# Find procs in system procs, and print them.
def printProcsInSystem(procsList, measurementName):

  def updateProcsFound(procsDict, pid, name, exe, pattern="", matchedRegex=""):
    procData = {pid: {"name": procName, "exe": sysProcName, "pattern": procPattern, "matched_regex": matchedRegex}}
    procsFound.update(procData)

  # Empty dict for all procs are found in the system.
  procsFound = dict()
  hostname = socket.gethostname()

  # Find if processes are found in the system and add them to dict.
  for proc in procsList:
    procName = proc['name']
    procPattern = proc['pattern']
    byRegex = proc['regex']

    for pid, systemProcInfo in systemProcs.iteritems():
      sysProcName = systemProcInfo["name"]
      sysProcArgs = systemProcInfo["args"]

      if byRegex:
        regexPattern = re.compile(procPattern)
        matchedRegex = regexPattern.findall(sysProcArgs)

      # Find procs by Regex
      if byRegex and regexPattern.search(sysProcArgs):
        updateProcsFound(procsFound, pid, procName, sysProcName, procPattern, matchedRegex[0])
      # Find procs by pattern (fixed string).
      elif procPattern and procPattern in sysProcArgs:
        updateProcsFound(procsFound, pid, procName, sysProcName, procPattern)
      # Find procs by name.
      elif procName == sysProcName:
        updateProcsFound(procsFound, pid, procName, sysProcName)
  
  # Loop over procs that are found, and print them in InfluxDB format.
  for pid, procInfo in procsFound.iteritems():
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
    procOutputData = ('host=%(hostname)s,process_name="%(processName)s",exe="%(exe)s",pid=%(pid)s,pattern="%(pattern)s",matched_regex"%(matchedRegex)s"' % outputValues)

    # In InfluxDB format, first group is tags names, and second group is values.
    print procOutputKeys, procOutputData

# ------------------------------------------------------------------ #
# Main.
# ------------------------------------------------------------------ #

if __name__ == "__main__":

  # Script options.
  parser = argparse.ArgumentParser()
  parser.add_argument("-f","--yml-file", default="./procList.yml", help="Path for processes list in YAML file.")
  parser.add_argument("-n","--measurement-name", default="procCheck", help="It will be used as measurement name in Telegraf")
  args = parser.parse_args()
  
  # Check if any group is missing.
  procsListGroups = [
    'byName',
    'byString',
    'byRegex'
  ]
  
  # Set Yaml file path.
  procsListFile = args.yml_file
  
  # Get content of Yaml file.
  yamlProcsList = openYamlFile(procsListFile)
  
  # List of monitored processes.
  procsList = initProcsList(yamlProcsList, procsListGroups, procsListFile)

  # Get list with processes running now.
  systemProcs = getSystemProcs()

  # Print processes that founded.
  printProcsInSystem(procsList, args.measurement_name)
