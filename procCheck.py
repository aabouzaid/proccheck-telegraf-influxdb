#!/usr/bin/env python

import os
import sys
import yaml
import socket
import argparse


# Script options.
parser = argparse.ArgumentParser()
parser.add_argument("-f","--yml-file", help="Path for processes list in YAML file.")
args = parser.parse_args()


# ------------------------------------------------------------------ #
# Main.
# ------------------------------------------------------------------ #

# Plugin name will be used as measurement name in Telegraf.
pluginName = "procCheck"
hostName = socket.gethostname()

# Set path of Yaml file with procs list.
if args.yml_file:
  procsListFile = args.yml_file
else:
  procsListFile = "./procList.yml"

# Check if procs list file exists.
try:
  os.path.isfile(procsListFile)
except TypeError:
  print "Cannot open YAML file: %s." % (procsListFile)
  sys.exit(1)

# Load content of Yaml file.
with open(procsListFile, 'r') as procsYamlFile:
  try:
    procsList = yaml.load(procsYamlFile)
  except yaml.YAMLError as yamlError:
    print(yamlError)

# Load procs list by category.
try:
  byName = procsList["byName"]
  byPattern = procsList["byPattern"]
except KeyError:
  print 'Cannot find "byName" or "byPattern" in %s.' % (procsListFile)
  sys.exit(1)

# Add list procs with empty pattern list of procs with pattern.
for proc in byName:
  byPattern.update({proc: ""})

# Use merged dict as procs list.
procsList = byPattern


# ------------------------------------------------------------------ #
# Get list of procs in the system.
# ------------------------------------------------------------------ #

# Empty dict to put all procs in the system in it.
systemProcs = dict()

# Loop over pids in /proc.
pidsList = [pid for pid in os.listdir('/proc') if pid.isdigit()]

# Function to get info from any file inside "/proc/PID" path.
def getProcInfo(pid, pathName):
  procInfo = open(os.path.join('/proc', pid, pathName), 'rb').read().rstrip('\n').replace('\x00',' ')
  return procInfo

# Add proc PID, command arguments, and bin/exe name.
for pid in pidsList:
  try:
    procArgs = getProcInfo(pid, 'cmdline')
    procBin = getProcInfo(pid, 'comm')
    if procArgs:
      systemProcs.update({pid: {"name": procBin, "args": procArgs}})

  # Handle the error in case any proc did exit while script is still working.
  except IOError:
    continue


# ------------------------------------------------------------------ #
# Find procs in system procs, and print them.
# ------------------------------------------------------------------ #

# Empty dict for all procs are found in the system.
procsFound = dict()

# Find if processes are found found in the system and add them to dict.
for procName, procPattern in procsList.iteritems():
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
    'host': hostName,
    'pluginName': pluginName,
    'processName': procInfo["name"],
    'pid': pid,
    'exe': procInfo["exe"],
    'pattern': procInfo["pattern"]
  }

  # In InfluxDB format, first group is tags names, and second group is values.
  print ('%(pluginName)s,host=%(host)s,process_name=%(processName)s,exe=%(exe)s,pid=%(pid)s'
         ' host=%(host)s,process_name="%(processName)s",exe="%(exe)s",pid=%(pid)s,pattern="%(pattern)s"' % outputValues)
