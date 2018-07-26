import requests
import json
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
from lxml import html 
import re
import wget
import subprocess
import query_tns
from astropy import units as u
from astropy.coordinates import SkyCoord

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

def get_spectra(specpage,sourcename):
	try:
		#print '//td/a[contains(text(),'+source['name']+')]'
		speclist = specpage.xpath('//td/a[contains(text(),"'+sourcename+'")]')
		#print speclist
		specname=[0]
		for spec in speclist:
			if('P60' in spec.text_content() or 'P200' in spec.text_content()):
				specname.append(spec.text_content())
		specdate = (specname[-1])[13:21]
		specurl = 'http://skipper.caltech.edu:8080/growth-data/spectra/data/'+specname[-1]
		#specfile = wget.download(specurl,out='spectra/')
	except:
		specurl,specdate='',''
		print "No spectra found for this source"
	return specurl,specdate

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
		redshift=None
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
	# try:
	# 	line_sedm_enddate = np.atleast_1d(htmltext.xpath('//table/tbody/tr/td[@name="enddate"]/text()'))[-1]
	# except:
	# 	line_sedm_enddate = 'None'
	return redshift,classification,time_of_classification

def basic_data(sourceDict):
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

	return obsdate, mag, ra, dec, filter_name

def from_tns(tnsname):
	query_tns.api_key="54916f1700966b3bd325fc1189763d86512bda1d"
	query_tns.url_tns_api="https://wis-tns.weizmann.ac.il/api/get"
	query_tns.url_tns_sandbox_api="https://sandbox-tns.weizmann.ac.il/api/get"    
	query_tns.get_obj=[("objname",tnsname[2:]), ("photometry","0"), ("spectra","0")] 
	response=query_tns.get(query_tns.url_tns_api,query_tns.get_obj)
	json_data=json.loads(response.text)

	return json_data['data']['reply']['host_redshift'], json_data['data']['reply']['internal_name']

username = 'ysharma'
password = 'rajom$yashvi7'
sources,specpage = get_sourcelist(username,password)

parser = argparse.ArgumentParser()
parser.add_argument('-startdate',help="Query info from date (enter date in format 'YYYY-MM-DD'",type=str)
parser.add_argument('-enddate',help="Query info to date (enter date in format 'YYYY-MM-DD'",type=str)
args = parser.parse_args()
startdate = datetime.datetime.strptime(args.startdate,'%Y-%m-%d')
enddate = datetime.datetime.strptime(args.enddate,'%Y-%m-%d')

######### go through all sources and select the ones within given period
outfile = open('tns_upload_info_output.txt','w')
outfile.write('Source_name IAU_name TNS_upload_date SEDM_spectra_date Saved_on_date \n')
list_of_sources = []
for i,source in enumerate(sources[63:]):
	print source['name']
	try:
		r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=(username, password),
			data={'sourceid' : str(source['id'])})
		sourceDict = json.loads(r.text)
	except:
		print "No JSON object was found"
		continue
	recent_source = False
	tnsuploaddate,saveddate,tnsname,sedmspecdate='','','',''
	annotations = sourceDict['autoannotations']
	for annot in annotations:
		if(annot['type']=='TNS_upload_date'):
			date = datetime.datetime.strptime(annot['comment'][0:10],'%Y-%m-%d')
			print date
			if(date>=startdate and date<=enddate):
				recent_source = True
				print recent_source
				tnsuploaddate = date
		if(annot['type']=='IAU name'):
			tnsname = annot['comment']
		if(annot['type']=='Saved_date'):
			saveddate = annot['comment']
	if(recent_source == True):
		####### Get data
		specurl,specdate = get_spectra(specpage,source['name'])
		specdate = datetime.datetime.strptime(specdate,'%Y%m%d').strftime('%Y-%m-%d')
		disc_date, disc_mag, ra, dec, discfilter = basic_data(sourceDict)
		sn_redshift,sn_class,time_of_classification = from_viewsourcepage(username,password,source['name'])
		host_redshift,internal_name = from_tns(tnsname)
		c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree)
		ra = c.ra.to_string(unit=u.hour,sep=':')
		ra = ra[0:len(ra)-2]
		dec = c.dec.signed_dms
		if(dec.sign==1.0):
			sign = '+'
		else:
			sign = '-'
		dec = sign+c.dec.to_string(unit=u.degree,sep=':')
		dec = dec[0:len(dec)-2]
		####### List of recently uploaded sources
		outfile.write(source['name']+' '+tnsname+' '+str(tnsuploaddate)[0:10]+'      '+str(specdate)+'       '+saveddate[0:10]+' \n')
		outarr = [source['name'],tnsname,ra,dec,str(disc_date)[0:10],disc_mag,discfilter,host_redshift,sn_redshift,sn_class,time_of_classification,internal_name]
		list_of_sources.append(outarr)
	else:
		continue
outfile.close()
#subprocess.call("gedit tns_upload_info_output.txt",shell=True)

def make_atel(list_of_sources):
	####### Make atel header
	atel = open('atel_rcf.txt','w')
	atel.write('Title : ZTF Bright Transient Survey classifications\n\n'+
		'Authors : Y. Sharma, Woody Ko, Shaney ,C. Fremling, S. R. Kulkarni, R. Walters, N. Blagorodnova, J. D. Neill (Caltech),'+
		' A. A. Miller (Northwestern), K. Taggart, D. A. Perley (LJMU), A. Goobar (OKC), M. L. Graham (UW) on behalf of the Zwicky'+
		' Transient Facility collaboration\n\n')
	atel.write('The Zwicky Transient Facility (ZTF; ATel #11266) Bright Transient Survey (BTS; ATel #11688) reports classifications'+
		' of the following targets. Spectra have been obtained with the Spectral Energy Distribution Machine (SEDM)'+
		' (range 350-950nm, spectral resolution R~100) mounted on the Palomar 60-inch (P60) telescope (Blagorodnova et. al. 2018, PASP, 130, 5003).'+
		' Classifications were done with SNID (Blondin & Tonry, 2007, ApJ, 666, 1024). Redshifts are derived from the broad SN features'+
		' (two decimal points), and from narrow SN features or host galaxy lines (three decimal points).'+
		' Limits prior to detection and current magnitudes are available on the Transient Name Server (https://wis-tns.weizmann.ac.il). \r\n')
	atel.write('\n{:>13} | {:>13} | {:>9} | {:>11} | {:>12} | {:>10} | {:<9} | {:>8} | {:>10} |  {:>10} | Notes | '.format('Survey Name','Discovery Name','IAU Name','RA (J2000)','Dec (J2000)','Disc. date','Disc. mag','Redshift','Class','Class. date'))
	atel.write('\n'+'-'*13+' | '+'-'*13+' | '+'-'*9+' | '+'-'*11+' | '+'-'*12+' | '+'-'*10+' | '+'-'*9+' | '+'-'*8+' | '+'-'*10+' | '+'-'*12+' | '+'-'*5+' | ')

	for line in list_of_sources:
		if line[7]!=None:
			atel.write('\n{:>13} | {:>13} | {:>9} | {:>11} | {:>12} | {:>10} | {:<6.2f}({:>1}) | {:>8} | {:>10} |  {:>11} |       | '.format(line[0],line[11],line[1],line[2],line[3],line[4],round(float(line[5]),2),line[6],round(float(line[7]),3),line[9],line[10]))
		elif line[7]==None and line[8]!=None: 
			atel.write('\n{:>13} | {:>13} | {:>9} | {:>11} | {:>12} | {:>10} | {:<6.2f}({:>1}) | {:>8} | {:>10} |  {:>11} |       | '.format(line[0],line[11],line[1],line[2],line[3],line[4],round(float(line[5]),2),line[6],round(float(line[8]),3),line[9],line[10]))
		else:   
			atel.write('\n{:>13} | {:>13} | {:>9} | {:>11} | {:>12} | {:>10} | {:<6.2f}({:>1}) | {:>8} | {:>10} |  {:>11} |       | '.format(line[0],line[11],line[1],line[2],line[3],line[4],round(float(line[5]),2),line[6],None,line[9],line[10]))

	atel.write('\r\n\r\n ZTF is a project led by PI S. R. Kulkarni at Caltech (see ATEL #11266), and includes IPAC; WIS, Israel; '+
		'OKC, Sweden; JSI/UMd, USA; UW,USA; DESY, Germany; NRC, Taiwan; UW Milwaukee, USA and LANL USA. ZTF acknowledges the generous '+
		'support of the NSF under AST MSIP Grant No 1440341. Alert distribution service provided by DIRAC@UW. Alert filtering is being '+
		'undertaken by the GROWTH marshal system, supported by NSF PIRE grant 1545949. ')
	atel.close()

make_atel(list_of_sources)

