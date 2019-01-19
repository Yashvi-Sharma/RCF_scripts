import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
from lxml import html 
import re, os
import query_tns
import pprint, getpass

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
		# url = open('urlfile','r').readlines()[0]
		# s = requests.post(url,auth=(username, password))
		# specpage = html.fromstring(s.content)
	return sources

#ZTF_name = sys.argv[1]
username = raw_input('Input Marshal username: ')
password = getpass.getpass('Password: ')
sources = get_sourcelist(username,password)
source_not_reported = []
SEDM_spec_uploaded = []
other_spec = []
no_spec = []
for i,source in enumerate(sources):
	# if(source['name'] != ZTF_name):
	# 	continue
	print "-----------------------------------"
	print source['name']
	try:
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=(username, password),
			data={'sourceid' : str(source['id'])})
		sourceDict = json.loads(r.text)
	except:
		print "No JSON object was found"
		continue
	annotations = sourceDict['autoannotations']
	tnsupload_date_exists = False
	tnsname=''
	for annot in annotations:
		if(annot['type']=='TNS_upload_date'):
			tnsupload_date_exists = True
		if(annot['type']=='IAU name'):
			tnsname = annot['comment']
	if(tnsupload_date_exists == True):
		print "TNS upload date already exists, moving on to next source"
		continue
	if(tnsname==''):
		source_not_reported.append(source['name'])
		print "Source not reported to TNS, no IAU name"
		continue
	elif(tnsname!=''):
		query_tns.api_key="54916f1700966b3bd325fc1189763d86512bda1d"
		query_tns.url_tns_api="https://wis-tns.weizmann.ac.il/api/get"
		query_tns.url_tns_sandbox_api="https://sandbox-tns.weizmann.ac.il/api/get"    
		query_tns.get_obj=[("objname",tnsname[2:]), ("photometry","0"), ("spectra","1")] 
		response=query_tns.get(query_tns.url_tns_api,query_tns.get_obj)
		json_data=json.loads(response.text)
		#pprint.pprint(json_data)
		reply = json_data['data']['reply']
		if('spectra' in reply.keys() and len(reply['spectra'])!=0):
			print "Spectra present"
			print "Number of spectra for this object = "+str(len(reply['spectra']))
			asciifile = [os.path.basename(x['asciifile']) for x in reply['spectra']]
			for i,file in enumerate(asciifile):
				if('ZTF' in file):
					print "Spectra uploaded by ZTF "+file
					tns_upload_date = file[5+len(tnsname[2:]):15+len(tnsname[2:])]
					tns_upload_date = datetime.datetime.strptime(tns_upload_date,'%Y-%m-%d')
					print tns_upload_date
					if(tnsupload_date_exists==True):
						print "TNS upload date already exists, moving on to next source"
						continue
					else:
						payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':'STRING','type':'TNS_upload_date',
									'comment':tns_upload_date}
						b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),data=payload1)
						print b.text
				elif('P60_SED-Machine' in file):
					SEDM_spec_uploaded.append(source['name'])
					print "SEDM spectrum uploaded "+file+", reducer was "+reply['spectra'][i]['reducer']
				else:
					try:
						sourcegroup = reply['spectra'][i]['source_group']['name']
					except:
						sourcegroup = reply['spectra'][i]['source_group_name']
					print sourcegroup
					other_spec.append(source['name'])
		else:
			print "No spectra uploaded"
			no_spec.append(source['name'])

print "Sources not reported to TNS"
print source_not_reported

print "No spectra uploaded for these sources"
print no_spec

print "Sources which were observed by SEDM and classified on TNS"
print SEDM_spec_uploaded

print "Sources whose spectra is available on TNS from other groups"
print other_spec


	






