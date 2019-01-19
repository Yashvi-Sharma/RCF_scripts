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
from astropy import units as u
from astropy.coordinates import SkyCoord
import pandas as pd
import getpass

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
		# s = requests.post('http://skipper.caltech.edu:8080/growth-data/spectra/data',auth=(username, password))
		# specpage = html.fromstring(s.content)
	return sources

def webpage_init():
	#subprocess.call("rm rcf_table_100.html",shell=True)
	tbl = open('t4.html','a')
	head = ['Sr No.','Object Name','TNS Name','Spectra', 'Classification','Time of classification','TNS upload date','Latest SEDM assignment end date','Redshift','Nearest Galaxy-redshift','Nearest galaxy separation in arcmin','Saving date','Date of discovery','Magnitude','RA','Dec','NEDCheck']
	msg = """ <html>
	<h1> Redshift Completeness Fraction-Discovered SNe </h1>
	<body>
	<style>
	table, th, td {
	    border: 1px solid black;
	}
	th, td {
	    padding: 15px;
	}
	</style>

	<script type="text/javascript" src="gs_sortable.js"></script>
	<script type="text/javascript">
	<!--
	var TSort_Data = new Array ("sort",'i','s','s','s','s','s','s','s','f','f','f','s','s','f','','','');
	var TSort_Icons = new Array (' V', ' &#923;');
	var TSort_Initial = 0;
	tsRegister();
	// -->
	</script> 

	<table> 
	<TABLE id = "sort">
	<thead> <tr><th> """
	tbl.write(msg)
	tbl.write(' </th><th>'.join(head)+' </th></tr> </thead> \n')
	return tbl

def basic_data(sourceDict):
	mag,mager,time,filt,lim_mag,name,programid=[],[],[],[],[],[],[]
	for i in range (0,len(sourceDict['uploaded_photometry'])):
		mag.append(sourceDict['uploaded_photometry'][i]['magpsf'])
		mager.append(sourceDict['uploaded_photometry'][i]['sigmamagpsf'])
		time.append(sourceDict['uploaded_photometry'][i]['jd'])
		filt.append(sourceDict['uploaded_photometry'][i]['filter'])
		lim_mag.append(sourceDict['uploaded_photometry'][i]['limmag'])
		programid.append(sourceDict['uploaded_photometry'][i]['programid']) 
	ind=np.argsort(time)
	time=np.asarray(time)[ind]
	mag=np.asarray(mag)[ind]
	mager=np.asarray(mager)[ind]
	filt=np.asarray(filt)[ind]
	lim_mag=np.asarray(lim_mag)[ind]
	programid=np.asarray(programid)[ind]

	#print time
	pi_filt=programid==1

	time=np.asarray(time)[pi_filt]
	mag=np.asarray(mag)[pi_filt]
	mager=np.asarray(mager)[pi_filt]
	filt=np.asarray(filt)[pi_filt]
	lim_mag=np.asarray(lim_mag)[pi_filt]
	programid=np.asarray(programid)[pi_filt]
  
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
	#print up_ind


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

	return obsdate, mag, ra, dec#, filter_name
	
def from_annotations(annotations):
	tnsname, saved_date, tnsupload_date = 'None','None','None'
	for diction in annotations:
		if(diction['type']=='IAU name'):
			tnsname = diction['comment']
		if(diction['type']=='Saved_date'):
			saved_date = diction['comment'].split(' ')[0]
		if(diction['type']=='TNS_upload_date'):
			tnsupload_date = diction['comment']
	return tnsname, saved_date, tnsupload_date

def from_viewsourcepage(username,password,sourcename):
	t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi', auth=(username, password),
		data={'name' : sourcename})
	htmltext = html.fromstring(t.content)
	redshift,classification,time_of_classification = 'None','None','None'
	#### Get redshift
	try:
		line_z = re.compile('\S+').findall((htmltext.xpath('//span/a[contains(font[1]/b/text(),"[redshift]")]')[0]).text_content())
		redshift = line_z[-1]
		#print line_z
	except:
		redshift='None'
	#### Get classification
	try:
		line_class = ((htmltext.xpath('//span/a[contains(font[1]/b/text(),"[classification]")]')[0]).text_content()).strip()
		time_of_classification = datetime.datetime.strptime(line_class[0:11],'%Y %b %d').strftime('%Y-%m-%d')
		startind = line_class.find('[classification]:')
		classification = line_class[startind+17:].strip()
		print classification
		if('[view attachment]' in classification):
			classification = (classification.replace('[view attachment]','')).strip()

	except:
		classification='None'
	#### Get latest SEDM assignment last date
	try:
		line_sedm_enddate = np.atleast_1d(htmltext.xpath('//table/tbody/tr/td[@name="enddate"]/text()'))[-1]
	except:
		line_sedm_enddate = 'None'
	return redshift,classification,time_of_classification,line_sedm_enddate

def get_spectra(sourcename,username,password):
	mainurl = 'http://skipper.caltech.edu:8080'
	specpageurl = "http://skipper.caltech.edu:8080/cgi-bin/growth/view_spec.cgi"
	data = {'name':sourcename}
	s = requests.post(url=specpageurl,auth=(username, password),data=data)
	specpage = html.fromstring(s.content)
	try:
		#print '//td/a[contains(text(),'+source['name']+')]'
		speclist = specpage.xpath('//a[contains(text(),"ASCII")]')
		#print speclist
		specname=[]
		for spec in speclist:
			specname.append(spec.get('href'))
		specdate = (specname[-1])[13:21]
		specurl = mainurl+specname[-1]
		# specfile = os.path.basename(specname[-1])
		# prefix = os.path.dirname(specname[-1])
		# print "All spectrum files are - "
		# for spec in specname:
		# 	print os.path.basename(spec)
		# proceed = raw_input("Selected file is "+specfile+" .Press enter if this file is ok or enter the name of new file. ")
		# if(proceed != ''):
		# 	specfile = proceed
		# 	specurl = mainurl+prefix+'/'+specfile
		#subprocess.call('wget '+specurl,cwd='/'+snidpath,shell=True)
	except:
		specurl,specdate='',''
		specfile = ''
		print "No spectra found for this source"
	return specurl,specdate

def from_ned(lat,lon,z_sn):
	c = SkyCoord(ra=lon*u.degree, dec=lat*u.degree)
	lon = c.ra.to_string(u.hour)
	lat = c.dec.to_string(u.degree)
	nedurl = 'http://ned.ipac.caltech.edu/cgi-bin/objsearch?in_csys=Equatorial&in_equinox=J2000.0&lon='+str(lon)+'&lat='+str(lat)+'&'+'radius=2.0&hconst=73&omegam=0.27&omegav=0.73&corr_z=1&search_type=Near+Position+Search&z_constraint=Unconstrained&z_value1=&'+'z_value2=&z_unit=z&ot_include=ANY&nmp_op=ANY&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=Distance+to+search+center&of=pre_text&'+'zv_breaker=30000.0&list_limit=5&img_stamp=YES'
	nedreq = requests.get(nedurl)
	if('No object found.' in nedreq.text):
		hit = False
		sep_arcmin='...'
		host_redshift='...'
	else:
		hit = False
		tbl = (html.fromstring(nedreq.content).xpath('//pre')[0].text_content()).split('\n')
		sep_arcmin = 100
		for line in tbl[3:len(tbl)-1]:
			line = re.compile('\S+').findall(line.replace(u'\xa0',u'XX '))
			#print z_host
			for f,val in enumerate(line):
				if(val[-1]=='s' and val[-2].isdigit()):
					ra = val
					dec = line[f+1]
					z_host = line[f+4]
					break
			print z_host
			hostcoord = SkyCoord(ra+' '+dec)
			host_sep = c.separation(hostcoord).arcminute
			sep_arcmin = min(sep_arcmin,host_sep)
			if(z_host == '...'):
				continue
			elif(abs(float(z_host)-float(z_sn))<=0.01):
				hit=True
				sep_arcmin = host_sep
				break
		print host_sep

	return sep_arcmin,z_host,hit

  
#ZTF_name=str(sys.argv[1]) 
username = raw_input("Input Marshal username : ")
password = getpass.getpass("Input password : ")
#### Get program id and source list
sources = get_sourcelist(username, password)
#### Initialize webpage
tbl = webpage_init()
SN_class = []
index=0
for index,source in enumerate(sources[0:]):
	#if(source['name']!=ZTF_name):
	#	continue				
	print "-----------------------------------"
	print source['name']
	try:
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=(username, password),
			data={'sourceid' : str(source['id'])})
		sourceDict = json.loads(r.text)
	except:
		print "No JSON object was found"
		continue
	#### Some data extraction taken from import_requests.py
	redshift, classification, time_of_classification,sedm_enddate = from_viewsourcepage(username,password,source['name'])
	# if('SN' not in classification):
	# 	continue
	obsdate, mag, ra, dec = basic_data(sourceDict)
	#### Other data extraction
	tnsname,saved_date,tnsupload_date = from_annotations(sourceDict['autoannotations'])
	#redshift, classification, time_of_classification,sedm_enddate = from_viewsourcepage(username,password,source['name'])
	SN_class.append(classification)
	#### NED query
	if(redshift!='None'):
		sep_arcmin,host_redshift,hit = from_ned(dec,ra,float(redshift))
	else:
		sep_arcmin,host_redshift,hit = 'NA','NA','NA'
	#break
	#### Find if spectra exists, if yes download
	specurl,specdate = '',''#get_spectra(source['name'],username,password)
	print index, source['name'], tnsname, classification, time_of_classification, redshift, saved_date, obsdate, ra, dec, specdate
	if(specurl!=''):
		tbl.write('<tr><td> '+str(index)+' </td><td>'+source['name']+' </td><td> '+tnsname+' </td><td><a href="'+specurl+'"> Spectra available </a>'+specdate+' </td><td> '+
			classification+' </td><td> '+time_of_classification+' </td><td> '+tnsupload_date+' </td><td> '+str(sedm_enddate)+' </td><td> '+str(redshift)+
			' </td><td> '+host_redshift+' </td><td> '+sep_arcmin+' </td><td> '+saved_date+' </td><td> '+str(obsdate)+' </td><td> '+
			str(mag)+' </td><td> '+str(ra)+' </td><td> '+str(dec)+' </td><td> '+str(hit)+' </td><td></tr>\n ')
	else:
		tbl.write('<tr><td> '+str(index)+' </td><td>'+source['name']+' </td><td> '+tnsname+' </td><td> Spectra not available </td><td> '+
			classification+' </td><td> '+time_of_classification+' </td><td> '+tnsupload_date+' </td><td> '+str(sedm_enddate)+' </td><td> '+str(redshift)+
			' </td><td> '+host_redshift+' </td><td> '+sep_arcmin+' </td><td> '+saved_date+' </td><td> '+str(obsdate)+' </td><td> '+
			str(mag)+' </td><td> '+str(ra)+' </td><td> '+str(dec)+' </td><td> '+str(hit)+' </td><td></tr>\n ')
tbl.write('</table></body></html>')
SN_classes = np.unique(SN_class,return_counts=True)
SN_classes = dict(zip(*SN_classes))
print SN_classes


