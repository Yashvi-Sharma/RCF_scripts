import requests
import json
import numpy as np
from datetime import date
import jd_to_date as jd2date
import sys, getopt, argparse
from lxml import html
import os, re, wget
from pprint import pprint
from getpass import getpass

HANDLE_NAMES = {'neill': 'D. Neill', 'adugas': 'A. Dugas', 'ysharma': 'Y. Sharma', 'sedmdrp': 'SEDmRobot', 'shaney': 'S. Sze'}

sandbox = False
if sandbox:
	TNS_BASE_URL = "https://sandbox-tns.weizmann.ac.il/api/set/"
	upload_url   = "https://sandbox-tns.weizmann.ac.il/api/file-upload"
	report_url   = "https://sandbox-tns.weizmann.ac.il/api/bulk-report"
	reply_url    = "https://sandbox-tns.weizmann.ac.il/api/bulk-report-reply"
else:
	TNS_BASE_URL = "https://wis-tns.weizmann.ac.il/api/set/"
	upload_url   = "https://wis-tns.weizmann.ac.il/api/file-upload"
	report_url   = "https://wis-tns.weizmann.ac.il/api/bulk-report"
	reply_url    = "https://wis-tns.weizmann.ac.il/api/bulk-report-reply"

API_KEY = "54916f1700966b3bd325fc1189763d86512bda1d"

def makeparser():
	parser = argparse.ArgumentParser()
	parser.add_argument("ZTF_name", help="Target name", nargs='+')
	parser.add_argument("--spectype", default="object", choices=['object', 'host', 'sky', 'arcs', 'synthetic'],
						help="Choose spectrum type from options object,host and sky, by default it is object")
	parser.add_argument("--tel_instrument", help="Input telescope and instrument name separated by +, eg. P60+SED-Machine")
	parser.add_argument("--observer", help="Name of the observer, eg SEDmRobot or F. Lastname")
	parser.add_argument("--exptime", help="Exposure time in seconds")
	parser.add_argument("--reducer", help="Reducer name, eg F. Lastname")
	parser.add_argument("--obsutc", help="Observation time UTC, format 'YYYY-MM-DD HH:MM:SS'")

	return parser

def get_classification_id(classification):
	class_ids = {'Afterglow':          23, 
				 'AGN':                29,
				 'CV':                 27,
				 'Galaxy':             30,
				 'Gap':                60,
				 'Gap I':              61,
				 'Gap II':             62,
				 'ILRT':               25,
				 'Kilonova':           70,
				 'LBV':                24,
				 'M dwarf':           210,
				 'Nova':               26,
				 'QSO':                31,
				 'SLSN-I':             18,
				 'SLSN-II':            19,
				 'SLSN-R':             20,
				 'SN':                  1,
				 'SN I':                2,
				 'SN I-faint':         15,
				 'SN I-rapid':         16,
				 'SN Ia':               3,
				 'SN Ia 91bg-like':   103,
				 'SN Ia-91bg-like':   103,
				 'SN Ia 91T-like':    104,
				 'SN Ia-91T-like':    104,
				 'SN Ia-CSM':         106,
				 'SN Ia-pec':         100,
				 'SN Ia-SC':          102,
				 'SN Iax[02cx-like]': 105,
				 'SN Ib':               4,
				 'SN Ib-Ca-rich':       8,
				 'SN Ib-pec':         107,
				 'SN Ib/c':             6,
				 'SN Ibn':              9,
				 'SN Ic':               5,
				 'SN Ic-BL':            7,
				 'SN Ic-pec':         108,
				 'SN II':              10,
				 'SN II-pec':         110,
				 'SN IIb':             14,
				 'SN IIL':             12,
				 'SN IIn':             13,
				 'SN IIn-pec':        112,
				 'SN IIP':             11,
				 'SN impostor':        99,
				 'Std-spec':           50,
				 'TDE':               120,
				 'Varstar':            28,
				 'WR':                200,
				 'WR-WC':             202,
				 'WR-WN':             201,
				 'WR-WO':             203,
				 'Other':               0}
	keys = np.array(class_ids.keys())
	try:
		classkey = keys[keys == classification][0]
		print "classification found: " + classkey
	except:
		key_options = [classification in x for x in keys]
		key_options = keys[key_options]
		classkey = raw_input(','.join(x for x in key_options) + ". classification id matches found. Please enter one manually: ")
	return class_ids[classkey]

def read_header(filename):
	'''returns a dictionary with important information and the filetype'''
	fname = os.path.basename(filename)
	
	file_ext = fname.split('.')[-1]
	if file_ext == 'txt':
		file_ext = 'ascii'
	assert file_ext == 'fits' or file_ext == 'ascii'
	
	header_info = {'_name': 'header'}

	# I don't know why she put it up here
	if('P200' in fname):
		header_info['telescope']  = 'P200'
		header_info['instrument'] = 'DBSP'
	if('P60' in fname):
		header_info['telescope']  = 'P60'
		header_info['instrument'] = 'SED-Machine'
		
	# so user can see format when prompted - will throw an error if unchanged
	header_info['obsutc'] = ''
		
	with open(filename) as f:
		for line in f:
			# ensure we're working only with header info
			if '#' not in line: # we've reached the end of the header, now in data
				break
			
			line = line[1:-1] # remove hash and newline
			# parse usable keys, values depending on format
			try:
				delim = line.find(':')
			except ValueError: # there's less than one ': ' to split on
				delim = line.find(' ')
			if header_info['instrument'] == 'DBSP':
				delim = line.find('=')
			key, value = line[:delim].strip(), line[delim + 1:].strip()
			key = key.lower()
				
			# save value for relevant keys
			if key in ('telescope', 'instrument', 'exptime', 'user', 'reducer', 'observer', 'obsutc'):
				header_info[key] = value
			elif key in ('utshut'):
				header_info['obsutc'] = value
			elif key in ('user'):
				header_info['observer'] = value
				
			elif key in ('obsdate'):
				header_info['obsutc'] = value
			elif key in ('obstime'):
				header_info['obsutc'] += ' ' + value


	# put final values in more appropriate formats
	if header_info.get('instrument'):
		if 'SED' in header_info['instrument']:
			header_info['instrument'] = 'SED-Machine'
	if header_info.get('observer') == 'sedmdrp':
		header_info['observer'] = 'SEDmRobot'
	header_info['obsutc'] = header_info['obsutc'].replace('T', ' ')[:19]    # 'YYYY-MM-DD HH:MM:SS'

	for key in header_info.keys():
		print '{:23}'.format(key), '\t', header_info[key]
		
	try:
		header_info['tel_inst'] = '{}+{}'.format(header_info['telescope'], header_info['instrument'])
	except KeyError:
		pass
	if header_info.get('tel_inst') == 'P60+SED-Machine':
		header_info['tel_instrument_id'] = 149
	elif header_info.get('tel_inst') == 'P200+DBSP':
		header_info['tel_instrument_id'] = 1
	elif header_info.get('tel_inst') == 'NOT+ALFOSC':
		header_info['tel_instrument_id'] = 41
		
	if header_info.get('reducer') in HANDLE_NAMES:
		print header['reducer']
		header['reducer'] = HANDLE_NAMES[header['reducer']]
		print header['reducer']

	return header_info
	
def get_program_idx(auth, program='Redshift Completeness Factor'):
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_programs.cgi', auth=auth)
	programs = json.loads(r.content)

	return [p['programidx'] for p in programs if p['name'] == program][-1]

def get_sourcelist(auth, program='Redshift Completeness Factor', return_specpage=True):
	programidx = get_program_idx(auth, program=program)
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', 
					  auth=auth, data={'programidx' : str(programidx)})
	sources = json.loads(r.content)
	
	if return_specpage:
		s = requests.post('http://skipper.caltech.edu:8080/growth-data/spectra/data', auth=auth)
		specpage = html.fromstring(s.content)
		return sources, specpage
		
	else:
		return sources

def submitSpectraFiles(uploadUrl, specfile, api_key):
	data = {'api_key' : api_key}
	files = [('files[]', (specfile, open(specfile), 'text/plain'))]
	if(len(specfile) > 0):
		uploadRequest = requests.post(uploadUrl, data=data, files=files)
		if uploadRequest:
			return uploadRequest.json()
		else:
			return {'id_code' : '0', 'id_message' : 'Empty response, something went wrong during file upload.'}
	else:
		return {'id_code' : '0', 'id_message' : 'No Files Provided For Upload'}

def submitclassificationReport(reportUrl, classificationReport, api_key):
	data = {'api_key' : api_key, 'data' : classificationReport.as_json()}
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

class TNSclassificationReport:
	def __init__(self):
		self.name                          = None
		self.fitsName                      = ''
		self.asciiName                     = None
		self.classifierName                = None
		self.classificationID              = None
		self.redshift                      = ''
		self.classificationComments        = ''
		self.obsDate                       = None
		self.instrumentID                  = None
		self.expTime                       = ''
		self.observers                     = None
		self.reducers                      = ''
		self.specTypeID                    = ''
		self.spectrumComments              = ''
		self.groupID                       = ''
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
		
		# make sure we have at least the required values
		for field in (self.name, self.asciiName, self.classifierName, self.classificationID, self.instrumentID, self.obsDate, self.observers):
			try:
				assert field
			except:
				print field
				pprint(classificationDict)
				raise
		return classificationDict

	def as_json(self):
		return json.dumps(self.classificationDict())
		
def read_view_spec(auth, ZTFname):
	'''TODO: have it confirm with the user HERE so we get the right telescope etc'''
	##### Get view_spec page with spectrum url, observer/reducer names
	t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_spec.cgi', 
					  auth=auth, data={'name' : ZTFname})
	view_spec = html.fromstring(t.content).getroottree()
	view_spec_info = {'_name': 'view_spec'}
	
	##### Get latest spectrum of object
	specurl_path = '//tr[3]/td[2]/table/tr[2]/td[1]/table/tr[1]/td[2]/span/font/a/attribute::*[2]'
	index = np.argmax(view_spec.xpath(specurl_path)) # finds the position of the largest href='' value

	specurl = 'http://skipper.caltech.edu:8080' + view_spec.xpath(specurl_path)[index]
	confirm_spectrum = raw_input(specurl + ' ?([y]/n) ')
	
	if not (confirm_spectrum == 'y' or confirm_spectrum.strip() == ''):
		print view_spec.xpath('//tr[3]/td[2]/table/tr[2]/td[1]/table/tr[1]/td[2]/span/font/a/attribute::*[2]')
		specurl = 'http://skipper.caltech.edu:8080/growth-data/spectra/data/' + raw_input('Choose spectrum file: ')
	
	view_spec_table = '//table[{}]/tr[2]/td[1]/table/tr/td[3]/span/font/tr[{{}}]/td[{{}}]/span/font/text()'.format(2 + index)
	
	assert view_spec.xpath(view_spec_table.format(2, 1)) == ['Observed by: ']
	assert view_spec.xpath(view_spec_table.format(3, 1)) == ['Reduced by: ']
	
	view_spec_info['observer'] = view_spec.xpath(view_spec_table.format(2, 2))[0]
	view_spec_info['reducer'] = view_spec.xpath(view_spec_table.format(3, 2))[0]
	view_spec_info['tel_inst'] = view_spec.xpath('//tr[3]/td[2]/span[{}]/font/b[1]/text()'.format(index + 1))[0].replace(' |', '')
	view_spec_info['classification'] = view_spec.xpath('///tr/td[4]/span/font/text()')[0].strip()
	
	for field in ('observer', 'reducer'):
		if view_spec_info.get(field) in HANDLE_NAMES:
			view_spec_info[field] = HANDLE_NAMES[view_spec_info[field]]
	

	if view_spec_info.get('tel_inst') == 'NOT+ALFOSC':
		view_spec_info['tel_instrument_id'] = 41
		
	return view_spec_info, specurl
	
def read_view_source(auth, ZTFname):
	#### Get html view_source overview page
	view_source_info = {'_name' : 'view_source'}
	t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi',
						auth=auth, data={'name' : ZTFname})
	view_source = html.fromstring(t.content)
	
	#### Get classification
	line_class = view_source.xpath('//span/a[contains(font[1]/b/text(),"[classification]")]')[0].text_content().strip()
	view_source_info['classification'] = line_class.split('[classification]:')[1].replace('[view attachment]','').strip()
	
	try:
		view_source_info['redshift'] = view_source.xpath('//span/a[contains(font[1]/b/text(),"[redshift]")]')[0].text_content().split('[redshift]:')[1].strip()
	except:
		view_source_info['redshift'] = None
	
	
	print view_source_info
	return view_source_info
	
	
def choose_best(field, list_of_dicts):
	'''gets field from each entry in list_of_dicts in turn until it finds a valid value'''
	bad_values = ("uknown", "none", "n/a", "None", "N/A", "Unknown", "undefined", "Undefined")
	#print field
	for di in list_of_dicts:
		if di.get(field):
			if di[field] not in bad_values:
				#print di['_name'], di[field], "GOOD!~~~~~~"
				return di[field]
	'''        else:
				print di['_name'], di[field]
		else:
			try:
				print di['_name'], di[field]
			except Exception as e:
				print field, "not in", di['_name']'''
				
	return raw_input('Could not find a valid value for {}, please enter: '.format(field))

def main():
	args = makeparser().parse_args()
	
	auth = (raw_input('Skipper username: '), getpass())
	
	##### Get Source list for RCF program and spectra list
	programidx = get_program_idx(auth, program="Redshift Completeness Factor")
	
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', 
					  auth=auth, data={'programidx' : str(programidx)})
	source = [source for source in json.loads(r.content) if source['name'] in args.ZTF_name][0]
	
	
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi',
					  auth=auth, data={'sourceid' : str(source['id'])})
					  
	source_summary = json.loads(r.content)
	source_summary_info = {}
	
	view_spec, specurl = read_view_spec(auth, source['name'])
	specfile = wget.download(specurl)
	file_ext = specfile.split('.')[-1]
	assert file_ext == 'ascii' or file_ext == 'fits'
	print '\n' + specfile

	##### Get telescope, instrument, observer, obsdate, exptime, reducer and spectrum fileformat
	header = read_header(specfile)

	view_source = read_view_source(auth, source['name'])

	##### Get other required info
	tns_name = [annot['comment'] for annot in source_summary['autoannotations'] if annot['type'] == 'IAU name'][-1]
	spectype_id = ['object','host','sky','arcs','synthetic'].index(args.spectype) + 1
	
	### Confirm values with user
	'''for key in ('observer', 'reducer', 'obsutc'):
		user_val = raw_input('Enter {} value found in header ({}):'.format(key.lower(), header_info.get(key)))
		if user_val.strip() != '': # they pressed enter, or space enter
			header_info[key] = user_val'''

	start_upload = raw_input("Start upload? ([y]/n): ")
	if start_upload == 'y' or start_upload.strip() == '':
		##### Upload spectrum file
		fileUploadResult = submitSpectraFiles(upload_url, specfile, API_KEY)
		print fileUploadResult
		
		upload_code = fileUploadResult['id_code']
		
		print upload_code, fileUploadResult['id_message']
		print "Successfully uploaded spectrum"
		print fileUploadResult['data'][-1]
				
		##### Upload classification report
		classificationReport  = TNSclassificationReport()
		
		classificationReport.name                          = tns_name[2:]
		classificationReport.fitsName                      = ''
		classificationReport.asciiName                     = fileUploadResult['data'][-1]
		classificationReport.classifierName                = 'C. Fremling, A. Dugas, Y. Sharma (Caltech) on behalf of the Zwicky Transient Facility (ZTF)'### Change accordingly
		classificationReport.classificationID              = get_classification_id(choose_best('classification', [view_source]))
		classificationReport.redshift                      = choose_best('redshift', [view_source, view_spec])
		classificationReport.classificationComments        = ''
		classificationReport.obsDate                       = choose_best('obsutc', [header])[:19]
		classificationReport.instrumentID                  = choose_best('tel_instrument_id', [header, view_spec])
		classificationReport.expTime                       = choose_best('exptime', [header])
		classificationReport.observers                     = choose_best('observer', [header, view_spec])
		classificationReport.reducers                      = choose_best('reducer', [header, view_spec])
		classificationReport.specTypeID                    = spectype_id
		classificationReport.spectrumComments              = ''
		classificationReport.groupID                       = 48 # I guess this means ZTF?
		classificationReport.spec_proprietary_period_value = '3'
		classificationReport.spec_proprietary_period_units = "years"
		
		assert re.findall(r'\d{4}-\d{2}-\d{2} \d{2}\:\d{2}', classificationReport.obsDate) # check if 'YYYY-MM-DD HH:MM:SS'


		pprint(classificationReport.classificationDict(), indent=2)
		proceed = raw_input("Proceed with classification upload? ([y]/n) : ")
		if proceed == 'y' or proceed.strip() == '':
			if upload_code == 200:
				reportResult = submitclassificationReport(report_url, classificationReport, API_KEY)

				res_code = reportResult['id_code']
				res_message = reportResult['id_message']
				report_id = reportResult['data']['report_id']
				print "ID:", report_id
				print res_code, res_message, "report worked"

			if res_code == 200:
				replyResult = receiveFeedback(reply_url, report_id, API_KEY)
				feedback_code = replyResult['id_code']
				res_message = replyResult['id_message']
				print feedback_code, res_message, "feedback worked"
			else:
				print "Result reporting didn't work"
			
		if feedback_code == 200:
			payload = {'action':'commit', 'id':-1, 'sourceid':str(source['id']), 'datatype':'STRING','type':'TNS_upload_date', 'comment':str(date.today())}
			b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=auth, data=payload)

if __name__ == '__main__':
	main()
