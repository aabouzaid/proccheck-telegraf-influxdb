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

# Plugin name will be used as measurement name in Telegraf.
pluginName = "procCheck"
hostName = socket.gethostname()

# Set path of Yaml file with procs list.
if args.yml_file:
  procsYamlFile = args.yml_file
else:
  procsYamlFile = "./procList.yml"

# Check if procs list file exists.
try:
    os.path.isfile(procsYamlFile)
except TypeError:
    print "Cannot open YAML file: %s." % (procsYamlFile)
    sys.exit(1)

# Laod content of Yaml file.
with open(procsYamlFile, 'r') as procsListFile:
  try:
    procsList = yaml.load(procsListFile)
  except yaml.YAMLError as yamlError:
    print(yamlError)

#
byName = procsList["byName"]
byPattern = procsList["byPattern"]

# Convert list procs to dict with empty pattern.
for proc in byName:
  byPattern.update({proc: ""})

#
procsList = byPattern

#
systemProcs = dict()
procsFound = dict()

#
pidsList = [pid for pid in os.listdir('/proc') if pid.isdigit()]

#
def getProcInfo(pid, pathName):
  procInfo = open(os.path.join('/proc', pid, pathName), 'rb').read().rstrip('\n').replace('\x00',' ')
  return procInfo

#
for pid in pidsList:
  try:
    procArgs = getProcInfo(pid, 'cmdline')
    procBin = getProcInfo(pid, 'comm')
    if procArgs:
      systemProcs.update({pid: {"name": procBin, "args": procArgs}})
  # For procs that did exit.
  except IOError:
    continue

#
for procName, procPattern in procsList.iteritems():
  for pid, systemProcInfo in systemProcs.iteritems():
    #
    if procPattern and procPattern in systemProcInfo["args"]:
      procsFound.update({pid: {"name": procName, "exe": systemProcInfo["name"], "pattern": procPattern}})
    #
    elif procName == systemProcInfo["name"]:
      procsFound.update({pid: {"name": procName, "exe": systemProcInfo["name"], "pattern": ""}})

#
for pid, procInfo in procsFound.iteritems():
  outputValues = {
    'host': hostName,
    'pluginName': pluginName,
    'processName': procInfo["name"],
    'pid': pid,
    'exe': procInfo["exe"],
    'pattern': procInfo["pattern"]
  }

  #
  print ('%(pluginName)s,host=%(host)s,process_name=%(processName)s,exe=%(exe)s,pid=%(pid)s'
         ' host=%(host)s,process_name="%(processName)s",exe="%(exe)s",pid=%(pid)s,pattern="%(pattern)s"' % outputValues)
