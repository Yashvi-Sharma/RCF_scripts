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
		url = open('urlfile','r').readlines()[0]
		s = requests.post(url,auth=(username, password))
		specpage = html.fromstring(s.content)
	return sources, specpage

def webpage_init():
	subprocess.call("rm rcf_table.html",shell=True)
	tbl = open('rcf_table.html','a')
	head = ['Sr No.','Object Name','TNS Name','Spectra', 'Classification','Time of classification','TNS upload date','Latest SEDM assignment end date','Redshift','Nearest Galaxy-(redshift,separation in arcmin)','Saving date','Date of discovery','Magnitude','RA','Dec']
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
	var TSort_Data = new Array ("sort",'i','s','s','s','s','s','s','s','f','s','s','s','f','','');
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
	mag,mager,time,filt,lim_mag,name=[],[],[],[],[],[]
	for i in range (0,len(sourceDict['uploaded_photometry'])):
		mag.append(sourceDict['uploaded_photometry'][i]['magpsf'])
		mager.append(sourceDict['uploaded_photometry'][i]['sigmamagpsf'])
		time.append(sourceDict['uploaded_photometry'][i]['jd'])
		filt.append(sourceDict['uploaded_photometry'][i]['filter'])
		lim_mag.append(sourceDict['uploaded_photometry'][i]['limmag'])
	ind=np.argsort(time)
	time=np.asarray(time)[ind]
	mag=np.asarray(mag)[ind]
	mager=np.asarray(mager)[ind]
	filt=np.asarray(filt)[ind]
	lim_mag=np.asarray(lim_mag)[ind]
	#print time
  
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

	return obsdate, mag, ra, dec

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

def get_spectra(specpage,sourcename):
	try:
		#print '//td/a[contains(text(),'+source['name']+')]'
		speclist = specpage.xpath('//td/a[contains(text(),"'+sourcename+'")]')
		#print speclist
		specname=[]
		for spec in speclist:
			specname.append(spec.text_content())
		specdate = (specname[-1])[13:21]
		url = open('urlfile','r').readlines()[0]
		specurl = url+specname[-1]
		#specfile = wget.download(specurl,out='spectra/')
	except:
		specurl,specdate='',''
		print "No spectra found for this source"
	return specurl,specdate

def from_ned(lat,lon):
	c = SkyCoord(ra=lon*u.degree, dec=lat*u.degree)
	lon = c.ra.to_string(u.hour)
	lat = c.dec.to_string(u.degree)
	nedurl = 'http://ned.ipac.caltech.edu/cgi-bin/objsearch?in_csys=Equatorial&in_equinox=J2000.0&lon='+str(lon)+'&lat='+str(lat)+'&'+'radius=2.0&hconst=73&omegam=0.27&omegav=0.73&corr_z=1&search_type=Near+Position+Search&z_constraint=Unconstrained&z_value1=&'+'z_value2=&z_unit=z&ot_include=ANY&nmp_op=ANY&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=Distance+to+search+center&of=pre_text&'+'zv_breaker=30000.0&list_limit=5&img_stamp=YES'
	nedreq = requests.get(nedurl)
	try:
		tbl = (html.fromstring(nedreq.content).xpath('//pre')[0].text_content()).split('\n')
		line = re.compile('\S+').findall(tbl[3].replace(u'\xa0',u'XX '))
		#print line
		host_redshift = line[7]
		#print line[3], line[4]
		hostcoord = SkyCoord(line[3]+' '+line[4])
		host_sep = c.separation(hostcoord).arcminute
		print host_sep
	except:
		host_sep='...'
		host_redshift='...'
	return host_sep,host_redshift

  
#ZTF_name=str(sys.argv[1]) 
username = raw_input('Input Marshal username: ')
password = getpass.getpass('Password: ')
#### Get program id and source list
sources, specpage = get_sourcelist(username, password)
#### Initialize webpage
tbl = webpage_init()
SN_class = []
index=0
for source in sources:
	#if(source['name']!=ZTF_name):
	#	continue
	index=index+1				
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
	if('SN' not in classification):
		continue
	obsdate, mag, ra, dec = basic_data(sourceDict)
	#### Other data extraction
	tnsname,saved_date,tnsupload_date = from_annotations(sourceDict['autoannotations'])
	#redshift, classification, time_of_classification,sedm_enddate = from_viewsourcepage(username,password,source['name'])
	SN_class.append(classification)
	#### NED query
	sep_arcmin,host_redshift = from_ned(dec,ra)
	#break
	#### Find if spectra exists, if yes download
	specurl,specdate = get_spectra(specpage,source['name'])
	print index, source['name'], tnsname, classification, time_of_classification, redshift, saved_date, obsdate, ra, dec, specdate
	if(specurl!=''):
		tbl.write('<tr><td> '+str(index)+' </td><td>'+source['name']+' </td><td> '+tnsname+' </td><td><a href="'+specurl+'"> Spectra available </a>'+specdate+' </td><td> '+
			classification+' </td><td> '+time_of_classification+' </td><td> '+tnsupload_date+' </td><td> '+str(sedm_enddate)+' </td><td> '+str(redshift)+
			' </td><td> '+str(host_redshift)+','+str(sep_arcmin)+' </td><td> '+saved_date+' </td><td> '+str(obsdate)+' </td><td> '+
			str(mag)+' </td><td> '+str(ra)+' </td><td> '+str(dec)+' </td><td></tr>\n ')
	else:
		tbl.write('<tr><td> '+str(index)+' </td><td>'+source['name']+' </td><td> '+tnsname+' </td><td> Spectra not available </td><td> '+
			classification+' </td><td> '+time_of_classification+' </td><td> '+tnsupload_date+' </td><td> '+str(sedm_enddate)+' </td><td> '+str(redshift)+
			' </td><td> '+str(host_redshift)+','+str(sep_arcmin)+' </td><td> '+saved_date+' </td><td> '+str(obsdate)+' </td><td> '+
			str(mag)+' </td><td> '+str(ra)+' </td><td> '+str(dec)+' </td><td></tr>\n ')
tbl.write('</table></body></html>')
SN_classes = np.unique(SN_class,return_counts=True)
print SN_classes


