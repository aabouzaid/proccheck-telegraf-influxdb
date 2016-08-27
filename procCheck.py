#!/usr/bin/env python

import os
import socket
import yaml

#
pluginName = "procCheck"
hostName = socket.gethostname()

#
procsListFile = "./procList.yml"
with open(procsListFile, 'r') as allProcsList:
  try:
    procsList = yaml.load(allProcsList)
  except yaml.YAMLError as yamlError:
    print(yamlError)

#
byName = procsList["procs"]["byName"]
byPattern = procsList["procs"]["byPattern"]

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
