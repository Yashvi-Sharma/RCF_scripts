import requests
import json
import numpy as np
import datetime
import jd_to_date as jd2date
import argparse
from lxml import html 
import re
import wget
import query_tns
from astropy import units as u
from astropy.coordinates import SkyCoord
from getpass import getpass
from tns_upload_spec import get_sourcelist, get_program_idx

def get_namedate_in_range(startdate, enddate, auth):
	'''
	manual html-parsing mess I made in a hurry. #TODO use html.xpath or something
	adapted from scrape_TNS_uploads but too different to import
	faster than loading every single source, even though the initial page load is slow
	
	params:
		startdate: str
			beginning of acceptable TNS upload dates, inclusive. YYYY-MM-DD
		enddate: str
			end of acceptable TNS upload dates, inclusive. YYYY-MM-DD
		auth: tuple(string, string)
			growth marshal authorization, eg ('flastname', 'password')
	
	returns: results (list of tuples of two strings)
				 first string is ZTFname, second is TNS_upload_date (YYYY-MM-DD)
				 eg [('ZTF18abcdefg', '2018-01-01'), ...]
				 
				 for objects that:
					-have been uploaded to TNS before (inclusive) enddate
					-AND have been uploaded to TNS after (inclusive) startdate
	'''

	i = 0
	results = []
	while True:
		t = requests.get("http://skipper.caltech.edu:8080/cgi-bin/growth/list_sources_bare.cgi", auth=auth, 
						 params={'programidx': get_program_idx(auth),
								 'sortby': "TNS_upload_date",
								 'offset': i,
								'reverse': 1})
		objs = t.content.split('<a href="view_source.cgi?name=')[1:]
		for obj in objs:
			namepart, datepart = obj.split('[TNS_upload_date]:</b></font><font face="MyriadPro-Regular, \'Myriad Pro Regular\', MyriadPro, \'Myriad Pro\', Helvetica, sans-serif, Arial" color="black">\n                            ')[:2]
			name = namepart[:namepart.find('"')]
			date = datepart[:10]
			if date < startdate:
				break
			elif date <= enddate:
				results.append((name, date))
		if date < startdate or len(objs) < 100:
			break
		i += 100
	return results

def from_viewsourcepage(auth, sourcename):
	t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi', 
					  auth=auth, data={'name' : sourcename})
	htmltext = html.fromstring(t.content)
	
	#### Get redshift
	try:
		redshift = re.compile('\S+').findall((htmltext.xpath('//span/a[contains(font[1]/b/text(),"[redshift]")]')[0]).text_content())[-1]
	except:
		redshift=None
		
	#### Get classification
	try:
		line_class = ((htmltext.xpath('//span/a[contains(font[1]/b/text(),"[classification]")]')[0]).text_content()).strip()
		time_of_classification = datetime.datetime.strptime(line_class[:11],'%Y %b %d').strftime('%Y-%m-%d')
		classification = line_class.split('[classification]:')[1].strip()

		if('[view attachment]' in classification):
			classification = (classification.replace('[view attachment]','')).strip()

	except:
		classification = None

	return redshift, classification, time_of_classification

def basic_data(sourceDict):
	#TODO this needs to be redone in pandas or something so it's comprehensible
	mag,mager,time,filt,lim_mag,name,programid=[],[],[],[],[],[],[]
	for i in range (0,len(sourceDict['uploaded_photometry'])):
		mag.append(sourceDict['uploaded_photometry'][i]['magpsf'])
		mager.append(sourceDict['uploaded_photometry'][i]['sigmamagpsf'])
		time.append(sourceDict['uploaded_photometry'][i]['jd'])
		filt.append(sourceDict['uploaded_photometry'][i]['filter'])
		lim_mag.append(sourceDict['uploaded_photometry'][i]['limmag'])
		programid.append(sourceDict['uploaded_photometry'][i]['programid']) ###### Add this
	ind=np.argsort(time)
	time=np.asarray(time)[ind]
	mag=np.asarray(mag)[ind]
	mager=np.asarray(mager)[ind]
	filt=np.asarray(filt)[ind]
	lim_mag=np.asarray(lim_mag)[ind]
  
	up_ind=[]
	for i in range(0,len(mag)):
		if mag[i]<99:
			up_ind.append(i)
		
	if len(lim_mag)>0 and up_ind[0]>0:
		if time[up_ind[0]]-time[up_ind[0]-1] > 0.01:
			lim_mag=lim_mag[up_ind[0]-1]
			time_lim=time[up_ind[0]-1]
			filt_lim=filt[up_ind[0]-1]
		else:
			lim_mag=99
		time_lim=99
		filt_lim='r'
	else: 
		lim_mag=99
		time_lim=99
		filt_lim='r'


	mag_last=mag[len(mag)-1]
	magerr_last=mager[len(mag)-1]

	time_last=jd2date.jd_to_date(time[len(mag)-1])
	filt_last=filt[len(mag)-1]
	time_last=datetime.datetime(time_last[0],time_last[1],time_last[2],time_last[3],time_last[4],int(time_last[5]))

	obsdate = (jd2date.jd_to_date(time[up_ind[0]]))
	obsdate=datetime.datetime(obsdate[0],obsdate[1],obsdate[2],obsdate[3],obsdate[4],int(obsdate[5]))
	if time_lim == 99:
		time_lim=datetime.datetime(9999,9,9,9,9,9)
	else:
		time_lim=(jd2date.jd_to_date(time_lim))
		time_lim=datetime.datetime(time_lim[0],time_lim[1],time_lim[2],time_lim[3],time_lim[4],int(time_lim[5]))
	ra = sourceDict['ra']
	dec = sourceDict['dec']
	mag = mag[up_ind[0]]
	mag_err=mager[up_ind[0]]
	filter_name = filt[up_ind[0]]

	return obsdate, mag, ra, dec, filter_name

def from_tns(tnsname):
	query_tns.api_key="54916f1700966b3bd325fc1189763d86512bda1d"
	query_tns.url_tns_api="https://wis-tns.weizmann.ac.il/api/get"
	query_tns.url_tns_sandbox_api="https://sandbox-tns.weizmann.ac.il/api/get"    
	query_tns.get_obj=[("objname",tnsname[2:]), ("photometry","0"), ("spectra","0")] 
	response = query_tns.get(query_tns.url_tns_api,query_tns.get_obj)
	json_data = json.loads(response.text)

	return json_data['data']['reply']['host_redshift'], json_data['data']['reply']['internal_name']

def write_atel(args):
	'''writes an ascii atel to file "atel_rcf_startdate_to_enddate.txt" for objects 
	   uploaded to TNS within args.startdate to args.enddate, inclusive'''
	auth = (raw_input('Skipper username: '), getpass())
	sources = get_sourcelist(auth, return_specpage=False)
	ztfnames, tnsuploaddates = zip(*get_namedate_in_range(args.startdate, args.enddate, auth))
	source_ids = get_source_id(ztfnames, auth)


	daterange = '{}_to_{}'.format(args.startdate, args.enddate)
	if args.enddate == str(datetime.date.today()):
		daterange += '_partial' # there could be new TNS submissions today after you've written the ATel
		
	with open('atel_rcf_{}.txt'.format(daterange), 'w') as atel:
		colwidths = [13, 14, 9, 11, 12, 10, 9, 8, 10, 11]
		cols = ('Survey Name','   Disc. Name','IAU Name','RA (J2000)','Dec (J2000)','Disc. date','Disc. mag','Redshift','Class','Class. date')
		for i, col in enumerate(cols):
			colwidths[i] = max(len(col), colwidths[i])
		fmtstr = '\n{:>13} | {:>13} | {:>9} | {:>11} | {:>12} | {:>10} | {:<6.2f}({:>1}) | {:>8} | {:>10} |  {:>11} |'
		
		atel.write('Title : ZTF Bright Transient Survey classifications\n\n'+
			'Authors : A. Dugas, C. Fremling, Y. Sharma, H. Ko, S. Sze, S. R. Kulkarni, R. Walters, N. Blagorodnova, J. D. Neill (Caltech),'+
			' A. A. Miller (Northwestern), K. Taggart, D. A. Perley (LJMU), A. Goobar (OKC), M. L. Graham (UW) on behalf of the Zwicky'+
			' Transient Facility collaboration\n\n')
		atel.write('The Zwicky Transient Facility (ZTF; ATel #11266) Bright Transient Survey (BTS; ATel #11688) reports classifications'+
			' of the following targets. Spectra have been obtained with the Spectral Energy Distribution Machine (SEDM)'+
			' (range 350-950nm, spectral resolution R~100) mounted on the Palomar 60-inch (P60) telescope (Blagorodnova et. al. 2018, PASP, 130, 5003).'+
			' Classifications were done with SNID (Blondin & Tonry, 2007, ApJ, 666, 1024). Redshifts are derived from the broad SN features'+
			' (two decimal points), and from narrow SN features or host galaxy lines (three decimal points).'+
			' Limits prior to detection and current magnitudes are available on the Transient Name Server (https://wis-tns.weizmann.ac.il). \r\n')
		atel.write('\n{:>12} | {:>12} | {:>9} | {:>11} | {:>12} | {:>10} | {:<9} | {:>8} | {:>10} | {:>11} | Notes'.format('Survey Name','Disc. Name','IAU Name','RA (J2000)','Dec (J2000)','Disc. date','Disc. mag','Redshift','Class','Class. date'))
		atel.write('\n' + ' | '.join(['-' * i for i in (12, 12, 9, 11, 12, 10, 9, 8, 10, 11, 5)]))
		
		for ztfname in ztfnames:
			if source_ids.get(ztfname):
				atel.write(get_ascii_row(ztfname, source_ids[ztfname], auth))
			else:
				print "could not find sourceid for", ztfname
			
		atel.write('\r\n\r\n ZTF is a project led by PI S. R. Kulkarni at Caltech (see ATEL #11266), and includes IPAC; WIS, Israel; '+
			'OKC, Sweden; JSI/UMd, USA; UW,USA; DESY, Germany; NRC, Taiwan; UW Milwaukee, USA and LANL USA. ZTF acknowledges the generous '+
			'support of the NSF under AST MSIP Grant No 1440341. Alert distribution service provided by DIRAC@UW. Alert filtering is being '+
			'undertaken by the GROWTH marshal system, supported by NSF PIRE grant 1545949. ')


def get_source_id(ztfnames, auth, program="Redshift Completeness Factor"):
	''' takes a list of string ZTF names and finds their integer ids in the marshal
	param: ztfnames
		eg ['ZTF18abcdef', 'AT2018cow', ...]
	param: auth
		tuple of two strings (username, password)
	param: program
		string, name of program in growth marshal. All objects must be saved to that program.
	returns: sourceids
		dictionary of ztfname:int, with int to be used for /cgi-bin/growth/source_summary.cgi page'''
		
	programidx = get_program_idx(auth, program=program)
	
	r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', 
					  auth=auth, data={'programidx' : str(programidx)})
					  
	sourceids = {}
	for source in json.loads(r.content):
		if source['name'] in ztfnames:
			sourceids[source['name']] = source['id']
			
	return sourceids
	
def get_ascii_row(ztfname, sourceid, auth, return_class_date=False):
	''' makes a formatted row as to be inserted into an ATel ascii table
		param: ztfname
			string, usually like ZTF18abcdefg. Internal ZTF name in skipper.caltech marshal
		param: sourcid
			integer
			
		returns:
			string, that object's row in the table
			
	'''
	try:
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=auth,
							data={'sourceid' : str(sourceid)})
		sourceDict = json.loads(r.text)
	except ValueError:
		print ztfname + ": no JSON object was found, perhaps your credentials were mistyped"
		raise

	autoannot = {annot['type']:annot['comment'] for annot in sourceDict['autoannotations']}
	saveddate = autoannot.get('Saved_date')
	tnsname = autoannot.get('IAU name')
	'''assert tnsuploaddate == autoannot.get('TNS_upload_date')

	try:
		assert len(tnsuploaddate) == 10
	except AssertionError:
		print "ASSERTION ERROR tns date-------"
		print len(tnsuploaddate), tnsuploaddate'''
	
	print ztfname#, tnsuploaddate
	
	disc_date, disc_mag, ra, dec, discfilter = basic_data(sourceDict)
	sn_redshift, sn_class, time_of_classification = from_viewsourcepage(auth, ztfname) #TODO get from list_sources_growth in get_namedate_in_range
	host_redshift, internal_name = from_tns(tnsname)
	
	c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
	ra = c.ra.to_string(unit=u.hour, sep=':')[:-2]
	dec = c.dec.signed_dms
	if dec.sign == 1.0:
		sign = '+'
	else:
		sign = '-'
	dec = sign + c.dec.to_string(unit=u.degree, sep=':')
	dec = dec[:-2]
	
	if host_redshift != None:
		redshift = round(float(host_redshift), 3) # I think this needs string formatting not rounding - 0.20 will be displayed as 0.2 as long as it's a float
	elif sn_redshift != None:
		redshift = round(float(sn_redshift), 3)
	else:
		redshift = None
		
	disc_mag = round(float(disc_mag), 2)
	
	####### List of recently uploaded sources
	outarr = [ztfname, internal_name, tnsname, ra, dec, str(disc_date)[:10], disc_mag, discfilter, redshift, sn_class, time_of_classification]
	line = '\n{:>12} | {:>12} | {:>9} | {:>11} | {:>12} | {:>10} | {:<6.2f}({:>1}) | {:>8} | {:>10} | {:>11} |'.format(*outarr)
	
	if return_class_date:
		return line, time_of_classification
	else:
		return line


if __name__ == "__main__":
	### parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-startdate', help="Query info from [TNS_upload_date] inclusive (YYYY-MM-DD)", type=str)
	parser.add_argument('-enddate',   help="Query info to   [TNS_upload_date] inclusive (YYYY-MM-DD)", type=str)
	args = parser.parse_args()
	write_atel(args)
