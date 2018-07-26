import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
from lxml import html
import argparse
import os
import re
import wget, pprint

def makeparser():#def_progname,def_tel_inst,def_obsdate,def_observer,def_reducer):
	parser = argparse.ArgumentParser()
	parser.add_argument("ZTF_name",help="Target name",nargs='+')
	parser.add_argument("--spectype",default="object",choices=['object','host','sky','arcs','synthetic'],help="Choose spectrum type from options object,host and sky,"+
					  " by default it is object")
	parser.add_argument("--tel_instrument",default='P60+SED-Machine',help="Input telescope and instrument name separated by +, eg. P60+SED-Machine")
	#parser.add_argument("classification")
	#parser.add_argument("--obsdate",help="Observation date",default=None)
	#parser.add_argument("--observer",help="Name of observer",default='SEDmRobot')
	return parser

def get_classification(classification):
	class_ids = {'Afterglow':23, 'AGN':29, 'CV':27, 'Galaxy':30, 'Gap':60, 'Gap I':61, 'Gap II':62, 'ILRT':25, 'Kilonova':70, 'LBV':24,
				'M dwarf':210, 'Nova':26, 'QSO':31, 'SLSN-I':18, 'SLSN-II':19, 'SLSN-R':20, 'SN':1, 'SN I':2, 'SN I-faint':15, 'SN I-rapid':16, 
				'SN Ia':3, 'SN Ia-91bg-like':103, 'SN Ia 91T-like':104,'SN Ia-91T-like':104, 'SN Ia-CSM':106, 'SN Ia-pec':100, 'SN Ia-SC':102, 'SN Iax[02cx-like]':105,
				'SN Ib':4, 'SN Ib-Ca-rich':8, 'SN Ib-pec':107, 'SN Ib/c':6, 'SN Ibn':9, 'SN Ic':5, 'SN Ic-BL':7, 'SN Ic-pec':108, 'SN II':10,
				'SN II-pec':110, 'SN IIb':14, 'SN IIL':12, 'SN IIn':13, 'SN IIn-pec':112, 'SN IIP':11, 'SN impostor':99, 'Std-spec':50, 'TDE':120,
				'Varstar':28, 'WR':200, 'WR-WC':202, 'WR-WN':201, 'WR-WO':203, 'Other':0}
	keys = np.array(class_ids.keys())
	try:
		classkey = keys[keys==classification][0]
		print "Classification found: "+classkey
	except:
		key_options = [classification in x for x in keys]
		key_options = keys[key_options]
		classkey = raw_input(','.join(x for x in key_options)+". Classification matches found. Please enter one manually: ")
	return class_ids[classkey]

#def get_instrument()

def read_header(file):
	fname = os.path.basename(file)
	#print len(fname)
	#print fname[len(fname)-8:len(fname)-4]
	#print fname[len(fname)-5:len(fname)]
	if(fname[len(fname)-3:len(fname)]=='txt' or fname[len(fname)-5:len(fname)]=='ascii'):
		fformat = 'ascii'
	elif(fname[len(fname)-4:len(fname)]=='fits'):
		fformat = 'fits' 

	fdata = open(file,'r').readlines()
	for i,f in enumerate(fdata):
		fdata[i] = f.split(' ')
	tel,inst,user,obsdate,exptime,reducer = '','','','','',''
	if('P200' in fname):
		tel = 'P200'
		inst = 'DBSP'
	if('P60' in fname):
		tel = 'P60'
		inst = 'SED-Machine'
	for i, hline in enumerate(fdata):
		if(hline[0]=='#'):
			if(hline[1]=='TELESCOPE:'):
				tel = hline[2].strip()
			if(hline[1]=='INSTRUMENT:'):
				inst = hline[2].strip()
				if('SED' in inst):
					inst = 'SED-Machine'
			if(hline[1]=='USER:'):
				user = ' '.join(x for x in hline[2:])
				user = user.strip()
				if(user=='sedmdrp'):
					user = 'SEDmRobot'
			if(hline[1]=='OBSUTC:'):
				obsdate = hline[2]+' '+hline[3][0:8]
				obsdate = datetime.datetime.strptime(obsdate,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			if(hline[1]=='EXPTIME:'):
				exptime = hline[2].strip()
			if(hline[1]=='REDUCER:'):
				reducer = ' '.join(x for x in hline[2:])
				reducer = reducer.strip()
			if(hline[1]=='OBSERVER'):
				user = ' '.join(x for x in hline[3:])
				user = user.strip()
			if(hline[1]=='UTSHUT'):
				obsdate = hline[3].strip()[0:19]
				obsdate = datetime.datetime.strptime(obsdate,'%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			if(hline[1]=='EXPTIME'):
				exptime = hline[3].strip()
	confirmuser = raw_input('Confirm observer name found in header: '+user+'. Press "y" if yes or enter new name: ')
	if(confirmuser!='y'):
		user = confirmuser
	confirmreducer = raw_input('Confirm reducer name found in header: '+reducer+'. Press "y" if yes or enter new name: ')
	if(confirmreducer!='y'):
		reducer = confirmreducer
	confirmdate = raw_input("Confirm obsdate found in header "+str(obsdate)+'. Press "y" if yes or enter obsdate in format (Y-m-d H:M:S): ')
	if(confirmdate!='y'):
		obsdate = datetime.datetime.strptime(confirmdate,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
			
	return tel+'+'+inst,user,obsdate,exptime,reducer,fformat

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
		s = requests.post('http://skipper.caltech.edu:8080/growth-data/spectra/data',auth=(username, password))
		specpage = html.fromstring(s.content)
	return sources, specpage

def submitSpectraFiles(uploadUrl, fileList, api_key):
	data = {'api_key' : api_key}
	files = [('files[]', (fileList, open(fileList), 'text/plain'))]
	if(len(fileList) > 0):
		uploadRequest = requests.post(uploadUrl, data=data, files=files)
		if uploadRequest:
			return uploadRequest.json()
		else:
			return {'id_code' : '0', 'id_message' : 'Empty response, something went wrong during file upload.'}
	else:
		return {'id_code' : '0', 'id_message' : 'No Files Provided For Upload'}

def submitClassificationReport(reportUrl, classificationReport, api_key):
	data = {'api_key' : api_key, 'data' : classificationReport.classificationJson()}
	reportRequest = requests.post(reportUrl, data=data)
	if reportRequest:
		return reportRequest.json()
	else:
		return {'id_code' : '0', 'id_message' : 'Empty response, something went wrong during report submission.'}

def receiveFeedback(replyUrl, reportID, api_key):
	data = {'api_key' : api_key, 'report_id' : reportID}
	replyRequest = requests.post(replyUrl, data=data)
	if replyRequest:
		return replyRequest.json()
	else:
		return {'id_code' : '0', 'id_message' : 'Empty response, something went wrong during reply retrieval.'}

class TNSClassificationReport:
	def __init__(self):
		self.name = ''
		self.fitsName = ''
		self.asciiName = ''
		self.classifierName = ''
		self.classificationID = ''
		self.redshift = ''
		self.classificationComments = ''
		self.obsDate = ''
		self.instrumentID = ''
		self.expTime = ''
		self.observers = ''
		self.reducers = ''
		self.specTypeID = ''
		self.spectrumComments = ''
		self.groupID = ''
		self.spec_proprietary_period_value = ''
		self.spec_proprietary_period_units = ''
	 
	def classificationDict(self):
		classificationDict =  {
			'classification_report' : {
				'0' : {
					'name' : self.name, 
					'classifier' : self.classifierName, 
					'objtypeid' : self.classificationID, 
					'redshift': self.redshift, 
					'groupid' : self.groupID, 
					'remarks' : self.classificationComments, 
					'spectra' : {
						'spectra-group' : {
							'0' : {
								'obsdate' : self.obsDate,
								'instrumentid' : self.instrumentID,
								'exptime' : self.expTime,
								'observer' : self.observers,
								'reducer' : self.reducers,
								'spectypeid' : self.specTypeID,
								'ascii_file' : self.asciiName,
								'fits_file' : self.fitsName,
								'remarks' : self.spectrumComments,
								'spec_proprietary_period' : {
									'spec_proprietary_period_value' : self.spec_proprietary_period_value,
									'spec_proprietary_period_units' : self.spec_proprietary_period_units
								}
							}
						}
					}
				}
			}
		}
		return classificationDict

	def classificationJson(self):
		return json.dumps(self.classificationDict())


parser = makeparser()
args = parser.parse_args()
#print args
#print args
username = "ysharma"
password = "rajom$yashvi7"
tns_user = 'cfremling'
tns_pwd = 'acidh+22'
##### Get Source list for RCF program and spectra list
sources, specpage = get_sourcelist(username, password)
#print specpage
for source in sources:
	tns_name, specurl, specfile = '','',''
	if source['name'] in args.ZTF_name:
		#print "here"
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=(username, password),
			data={'sourceid' : str(source['id'])})
		sourceDict = json.loads(r.text)
		##### Get TNS name
		for annot in sourceDict['autoannotations']:
			if(annot['type']=='IAU name'):
				tns_name = annot['comment']
		##### Get latest spectrum of object 
		specname = [0]
		try:
			speclist = specpage.xpath('//td/a[contains(text(),"'+source['name']+'")]')
			for spec in speclist:
				specname.append(spec.text_content())
		except:
			print "ERROR! No spectra found for this source, exiting"
			raise SystemExit
		specurl = 'http://skipper.caltech.edu:8080/growth-data/spectra/data/'+specname[-1]
		confirm_spectrum=raw_input(specurl+' ?(y/n) ')
		if(confirm_spectrum=='y'):
			specfile = wget.download(specurl)
		else:
			print specname
			specf = raw_input('Choose spectrum file: ')
			specurl = 'http://skipper.caltech.edu:8080/growth-data/spectra/data/'+specf
			specfile = wget.download(specurl)
		print specfile

		t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi', auth=(username, password),
			data={'name' : source['name']})
		sourcepage = html.fromstring(t.content)
		#### Get redshift
		try:
			line_z = re.compile('\S+').findall((sourcepage.xpath('//span/a[contains(font[1]/b/text(),"[redshift]")]')[0]).text_content())
			redshift = line_z[-1]
		except:
			redshift=raw_input("Please enter SNID redshift if SN Ia: ")
		#### Get classification
		try:
			line_class = ((sourcepage.xpath('//span/a[contains(font[1]/b/text(),"[classification]")]')[0]).text_content()).strip()
			#time_of_classification = line_class[0:11]
			startind = line_class.find('[classification]:')
			classification = line_class[startind+17:].strip()
			#print classification
			if('[view attachment]' in classification):
				classification = (classification.replace('[view attachment]','')).strip()
		except:
			classification = raw_input("Classification not found, please enter manually: ")
		
		classification = get_classification(classification)
		##### Get telescope, instrument, observer, obsdate, exptime, reducer and spectrum fileformat
		tel_inst, observer,obsdate,exptime,reducer,fformat = read_header(specfile)
		
		if(tel_inst == 'P60+SED-Machine'):
			tel_instrument_id = 149
		elif(tel_inst == 'P200+DBSP'):
			tel_instrument_id = 1
		#elif(tel_inst =='LT+SPRAT'):

		##### Get other required info
		classifiers = 'C. Fremling, Y. Sharma (Caltech) on behalf of the Zwicky Transient Facility (ZTF)'### Change accordingly
		source_group = 48 ### Require source group id from drop down list, 0 is for None
		spectypes = np.array(['object','host','sky','arcs','synthetic'])
		spectype_id = np.where(spectypes==args.spectype)[0][0]+1
		#print spectype_id
		proprietary_period = '3'
		proprietary_units = "years"
		spec_comments =''
		classification_comments = ''

		if(fformat=='ascii'):
			files = specfile
		elif(fformat=='fits'):
			files = specfile

		sandbox = False
		if sandbox:
			TNS_BASE_URL = "https://sandbox-tns.weizmann.ac.il/api/set/"
			upload_url = "https://sandbox-tns.weizmann.ac.il/api/file-upload"
			report_url = "https://sandbox-tns.weizmann.ac.il/api/bulk-report"
			reply_url = "https://sandbox-tns.weizmann.ac.il/api/bulk-report-reply"
		else:
			#TNS_BASE_URL = ""#"https://wis-tns.weizmann.ac.il/api/set/"
			TNS_BASE_URL = "https://wis-tns.weizmann.ac.il/api/set/"
			upload_url = "https://wis-tns.weizmann.ac.il/api/file-upload"
			report_url = "https://wis-tns.weizmann.ac.il/api/bulk-report"
			reply_url = "https://wis-tns.weizmann.ac.il/api/bulk-report-reply"

		API_KEY = "54916f1700966b3bd325fc1189763d86512bda1d"

		start_upload = raw_input("Start upload? (y/n): ")
		if(start_upload=='y'):
			##### Upload spectrum file
			fileUploadResult = submitSpectraFiles(upload_url, files, API_KEY)
			res_code = fileUploadResult['id_code']
			res_message = fileUploadResult['id_message']
			res_fname = fileUploadResult['data'][-1]
			print res_code, res_message
			print "Successfully uploaded spectrum"
			print res_fname
			#res_code=200

			##### Upload classification report
			classificationReport = TNSClassificationReport()
			classificationReport.name = tns_name[2:]
			classificationReport.fitsName = ''
			classificationReport.asciiName = specfile
			classificationReport.classifierName = classifiers
			classificationReport.classificationID = classification
			classificationReport.redshift = redshift
			classificationReport.classificationComments = classification_comments
			classificationReport.obsDate = obsdate
			classificationReport.instrumentID = tel_instrument_id
			classificationReport.expTime = exptime
			classificationReport.observers = observer
			classificationReport.reducers = reducer
			classificationReport.specTypeID = spectype_id
			classificationReport.spectrumComments = spec_comments
			classificationReport.groupID = source_group
			classificationReport.spec_proprietary_period_value = proprietary_period
			classificationReport.spec_proprietary_period_units = proprietary_units
			pprint.pprint(classificationReport.classificationDict(),indent=2)
			proceed = raw_input("Proceed with classification upload? (y/n) : ")
			if(proceed[0]=='y'):
				if res_code == 200:
					reportResult = submitClassificationReport(report_url, classificationReport, API_KEY)
					try:
						res_code = reportResult['id_code']
						res_message = reportResult['id_message']
						report_id = reportResult['data']['report_id']
					except:
						res_code = '0'
						res_message = 'Bad response, something went wrong during report submission.'

				if res_code == 200:
					replyResult = receiveFeedback(reply_url, report_id, API_KEY)
					try:
			   			res_code = replyResult['id_code']
			   			res_message = replyResult['id_message']
					except:
			   			res_code = '0'
			   			res_message = 'Bad response, something went wrong during reply retrieval.'
				print res_code, res_message
			if(res_code==200):
				payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':'STRING','type':'TNS_upload_date','comment':str(datetime.date.today())}
				b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
                data=payload1)



		







