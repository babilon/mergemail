#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import os
import hashlib
import sys
import re
import argparse

class HashMapEntry:
	def __init__(self, path, hashval, linenumber, endline):
		self.path = path
		self.hashvalue = hashval
		self.linenumber = linenumber
		self.endline = endline
		self.dup_id = 0
		self.duplicatepath = []
		self.duplicateline = []
	
	def is_duplicate(self):
		return len(self.duplicatepath) == 0

	def dup_id(self):
		return len(self.duplicatepath)
	
class EmailSplitter:
	#
	# @param workdir The main working directory for all the EmailSplitter action
	# @param emailfilepath The email file to split or hash
	#
	def __init__(self, workdir, emailfilepath):
		# TODO workdir not used; goes with the split email file feature
		self.workdir = os.path.join(workdir, os.path.basename(emailfilepath))
		self.emailfilepath = emailfilepath

		# dictionary of HashMapEntry
		self.hashes = {}

		# XXX pattern seems to match most cases i've run across. would need to
		# modify for ? alternative email clients ?
		pattern = '^(From - )(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ' \
				'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ' \
				'[ 0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}$'

		self.regex = re.compile(pattern)

	def does_line_start_new_message(self, line):
		return self.regex.match(line) != None

	def hash_message(self, message):
		h = hashlib.new('sha512')
		h.update(message)
		hashval = h.hexdigest()

		return hashval

	#
	# TODO Used with splitting emails
	#
	def purge_message(self, message, filename):
		# this had better NOT exist, or else we're in trouble
		assert(os.path.exists(filename) == False)

		f = open(filename, 'w')
		f.write(message)
		f.close()

	#
	# merge self with other
	# we have paths to each email file to merge, all the messages in hashes.
	#
	def merge_email_file(self, other, writetodisk):
		duplicates = []
		new_messages = []

		for h, val in other.hashes.iteritems():
			if h in self.hashes:
				duplicates += [(self.hashes[h], val)]
			else:
				new_messages += [(h, val)]

		self.hashes.update(new_messages)

		# sort new messages based on starting line number for the new message
		new_messages = sorted(new_messages, key=lambda a: a[1].linenumber)

		# sort duplicates based on master's starting line number
		duplicates = sorted(duplicates, key=lambda a: a[0].linenumber)

		# print a report of what is about to or would happen if we continue
		print('master=%s\nother=%s' % (self.emailfilepath, other.emailfilepath))

		if len(duplicates) > 0:
			print('Duplicates (%d): <master> <other>' % len(duplicates))

		for dup in duplicates:
			print('%d-%d equal to %d-%d' % (dup[0].linenumber, dup[0].endline,
									dup[1].linenumber, dup[1].endline))

		if len(new_messages) > 0:
			print('New Messages (%d) in <other>' % len(new_messages))

		for nm in new_messages:
			print('%d-%d' % (nm[1].linenumber, nm[1].endline))

		# TODO pause/continue, dump a log with the important info to merge later
		# (instead of re-hashing the entire file)
		if writetodisk == False:
			return

		print('Merging files...')

		thisf = open(self.emailfilepath, 'a')
		otherf = open(other.emailfilepath, 'r')
		
		linenum = 0

		for newmsg in new_messages:
			while(linenum != newmsg[1].linenumber):
				line = otherf.readline()
				linenum += 1

			thisf.write(line)

			while(linenum != newmsg[1].endline):
				thisf.write(otherf.readline())
				linenum += 1
		
		thisf.close()
		otherf.close()

	#
	# Used to verify email files have unique messages
	#
	def hash_email_file(self):
		self.split_email_file(False)

	#
	# TODO Split email files into individual messages
	#
	def split_email_file(self):
		self.split_email_file(True)

	def split_email_file(self, purge):
		if purge == True:
			os.makedirs(self.workdir)
			os.mkdir(os.path.join(self.workdir, 'duplicates'))

		f = open(self.emailfilepath, 'r')

		line = f.readline()

		if len(line) == 0:
			print('Empty file. Exiting...')
			return

		if self.does_line_start_new_message(line) == False:
			print('Failed to match first line of email file, exiting...')
			print('First line of file: %s' % line)
			return

		linenumber = 1
		startmsg = linenumber
		# start message is a date that indicates when the message was
		# downloaded. it is not part of the 'hashed message'.
		beginmsg = line
		message = ''

		while(True):
			line = f.readline()
			linenumber += 1

			if len(line) == 0 or self.does_line_start_new_message(line):
				hashval = self.hash_message(message)

				if hashval in self.hashes:
					self.hashes[hashval].dup_id += 1
					self.hashes[hashval].duplicateline += [(startmsg, linenumber - 1)]

					filename = os.path.join(self.workdir, 'duplicates', hashval)
					filename += '_%10.10d' % self.hashes[hashval].dup_id

					self.hashes[hashval].duplicatepath += [filename]

				else:
					filename = os.path.join(self.workdir, hashval)
					self.hashes[hashval] = HashMapEntry(filename, hashval, startmsg, linenumber - 1)

				if purge == True:
					self.purge_message(beginmsg + message, filename)

				if len(line) == 0:
					break

				# new messages begin with a date that indicates when the message
				# was downloaded. this date is not part of the 'hashed message'. but if
				# we purge messages to disk, we need to write this date as well.
				beginmsg = line
				line = ''
				# new message begins
				message = ''
				startmsg = linenumber

			message += line

def main():
	parser = argparse.ArgumentParser()

	parser.add_argument('--merge', action='store_true',
		help='if set, will merge files after parsing. otherwise will prompt to'
		'continue.')

	parser.add_argument('--workdir', type=str,
		help='create files in this' 'directory')

	parser.add_argument('--split', action='store_true',
		help='needs work; would split email files into multiple files, inside'
		'sub folders of workdir')

	parser.add_argument('prog', type=str)

	parser.add_argument('input', type=str, nargs='+',
		help='input files to' 'merge with master')

	parser.add_argument('--log', action='store_true',
		help='set to log what is going to happen')

	parser.add_argument('--logfile', type=str,
		help='specify log file path')

	argval = parser.parse_args(sys.argv)

	workdir = ''
	if argval.workdir is not None:
		workdir = argval.workdir
		os.mkdir(workdir)

	# TODO finish implementing logging feature
	logfile = 'log.txt'
	if argval.log == True and argval.logfile is not None:
		logfile = argval.logfile
			
	emailhashes = []

	# hash email files
	for snapshot in argval.input:
		print("Hashing: %s" % snapshot)

		v = EmailSplitter(workdir, snapshot)
		#v.split_email_file()
		v.hash_email_file()

		print("Messages: %d" % len(v.hashes))

		emailhashes += [v]

	# check remaining hashes with those in master
	for v in emailhashes:
		for val in v.hashes.values():
			if len(val.duplicateline) > 0:
				print('Duplicates in single email file!')

				for dup in m.duplicateline:
					print('Duplicate at %d-%d' % (m.linenumber,
												  m.endline))

	masterhash = emailhashes[0]
	del(emailhashes[0])

	for v in emailhashes:
		print('Merging %s' % v.emailfilepath)

		masterhash.merge_email_file(v, argval.merge)

if __name__ == '__main__':
	main()
