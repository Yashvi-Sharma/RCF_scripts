import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
import lxml.html 
import re, getpass

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

def main():  
		#ZTF_name=str(sys.argv[1]) 
		username = raw_input('Input Marshal username: ')
		password = getpass.getpass('Password: ')
		sources = get_sourcelist(username,password)
		for i,source in enumerate(sources):
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
			#print annotations
			save_date_exists = False
			for annot in annotations:
				if(annot['type']=='Saved_date'):
					# olddate = annot['comment'].split()[0]
					# print olddate
					# try:
					#   newdate = datetime.datetime.strptime(str(olddate),'%y-%m-%d').strftime('%Y-%m-%d')
					#   print newdate
					#   payload = {'action':'delete','id':str(annot['id']),'sourceid':str(source['id'])}
					#   a = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
					#       data=payload)
					#   payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':'STRING','type':annot['type'],'comment':newdate+' RCF'}
					#   b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
					#       data=payload1)
					# except:
					#   print "Date modified"
					save_date_exists = True
				if(annot['comment']=='Redshift Completeness Factor' and annot['type']=='passed_filter'):
					annot_tag = annot
			if(save_date_exists == True):
				print "Saved date already exists, moving on to next source"
				#log.write(source['name']+' '+"Saved date exists\n")
				continue
			else:
				t = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi', auth=(username, password),data={'name' : source['name']})
				page = t.content
				page_source = lxml.html.fromstring(page)
				data = page_source.xpath('//span/a[contains(font[2]/text(),"Redshift Completeness Factor")]')
				if(data==[]):
					print "Auto annotation corresponding to passed filter RCF not found!"
					#log.write(source['name']+' '+"Auto annotation not found\n")
					continue
				else:
					line = data[0].text_content()
					#print line
					newline = re.compile('\w+').findall(line)
					#print newline
					date = newline[0]+'-'+newline[1]+'-'+newline[2]
					date = datetime.datetime.strptime(date,'%Y-%b-%d').strftime('%Y-%m-%d')
					user = newline[3]
					atype = newline[4]
					comments = newline[5]+" "+newline[6]+" "+newline[7]
					print date, user, atype, comments
					print annot_tag
					if(annot_tag['username']==user and annot_tag['comment'] == comments and annot_tag['type']==atype):
						print "Correct auto annotation identified"
					else:
						print "Couldn't match auto annotation, exiting the program"
						#log.write(source['name']+' '+"Auto annotation didn't match\n")
						continue
					print "Commiting annotation with datatype : STRING"+", type : Saved_date"+", comment : "+date
					payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':'STRING','type':'Saved_date','comment':date+' RCF'}
					b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
										data=payload1)
					print b.text
					#log.write(source['name']+' '+"Saved date entered successfully\n")

if __name__=='__main__':
		main()