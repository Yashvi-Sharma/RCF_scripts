import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
from lxml import html 
import re
import wget
import subprocess
import getpass

def assign_to_sedm(name,sourceid,priority,duration,username,password):
	instrumentid=65
	requestid=-1
	programid=24
	status='new'
	Followup_selection='IFU'
	commit='yes'
	startdate = str(datetime.date.today())
	payload = {'instrumentid':instrumentid,'programid':programid,'sourceid':sourceid,'name':name,'status':status,'commit':commit,
				'Followup_selection':Followup_selection, 'requestid':requestid, 'startdate':startdate,'priority':priority,'duration':duration}
	url = 'http://skipper.caltech.edu:8080/cgi-bin/growth/edit_followup_new.cgi'
	a = requests.post(url,auth=(username,password),data=payload)

	return a.text

def get_args():
	parser = argparse.ArgumentParser()
	#parser.add_argument('--date',default=datetime.datetime.now(),help="Enter the date for which saved sources need to be collected")
	parser.add_argument('ztfname',help="Enter source's name")
	args = parser.parse_args()
	return args

def check_assignment(name,username,password):
	t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi', auth=(username, password),
		data={'name' : name})
	htmltext = html.fromstring(t.content)
	to_assign = False
	try:
		line_class = ((htmltext.xpath('//span/a[contains(font[1]/b/text(),"[classification]")]')[0]).text_content()).strip()
		startind = line_class.find('[classification]:')
		classification = line_class[startind+17:].strip()
		if('[view attachment]' in classification):
			classification = (classification.replace('[view attachment]','')).strip()
	except:
		classification = ''
	if(classification!=''):
		print "Classification found : "+classification+". Moving on to next source."
		to_assign = False
	else:
		print "Source unclassified. Checking spectra availability."
		spec_exists = check_spectra(name,username,password)
		if(spec_exists):
			userinp = raw_input("Spectra exists. If spectra isn't good enough for classification, enter 'n', else to re-assign to SEDM, enter 'y'.")
			if(userinp=='n'):
				to_assign=False
			elif(userinp=='y'):
				to_assign = True
		else:
			try:
				line_sedm_enddate = np.atleast_1d(htmltext.xpath('//table/tbody/tr/td[@name="enddate"]/text()'))[-1]
				sedm_enddate = datetime.datetime.strptime(line_sedm_enddate,'%Y-%m-%d')
			except:
				sedm_enddate = ''
			if(sedm_enddate=='' or sedm_enddate < datetime.date.today()):
				to_assign = True
	return to_assign

def check_spectra(name,username,password):
	s = requests.post('http://skipper.caltech.edu:8080/growth-data/spectra/data',auth=(username, password))
	specpage = html.fromstring(s.content)
	spec_exists = False
	try:
		speclist = specpage.xpath('//td/a[contains(text(),"'+name+'")]')
		specname=[]
		for spec in speclist:
			specname.append(spec.text_content())
		specdate = (specname[-1])[13:21]
		specurl = 'http://skipper.caltech.edu:8080/growth-data/spectra/data/'+specname[-1]
		spec_exists = True
		#specfile = wget.download(specurl,out='spectra/')
	except:
		specurl,specdate='',''
		print "No spectra found for this source"
		spec_exists = False
	return spec_exists

def get_sourcelist(username, password):
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_programs.cgi', auth=(username, password))
	programs = json.loads(r.text)
	#print programs
	programidx = -1
	#print "Programs you are a member of:"
	for index, program in enumerate(programs):
		if program['name'] == 'Redshift Completeness Factor':
			programidx = program['programidx']
		#print programidx
	if programidx >= 0:
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', auth=(username, password),
			data={'programidx' : str(programidx)})
		sources = json.loads(r.text)
		#s = requests.post('http://skipper.caltech.edu:8080/growth-data/spectra/data',auth=(username, password))
		#specpage = html.fromstring(s.content)
	return sources


args = get_args()
print args.ztfname
username = raw_input("Input Marshal username : ")
password = getpass.getpass("Input password : ")
sources = get_sourcelist(username,password)
for source in enumerate(sources[400:]):
	if(source[1]['name']==args.ztfname):
		if(check_assignment(source[1]['name'],username,password)):
			print "Assigning source "+source[1]['name']+" as priority 3 starting from today for 7 days."
			assignment = assign_to_sedm(source[1]['name'],source[1]['id'],3,7,username,password)
			print assignment
		else:
			print "Source not assigned."



