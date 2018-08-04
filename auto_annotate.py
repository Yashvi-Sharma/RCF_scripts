import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import datetime
import jd_to_date as jd2date
import sys,getopt,argparse
import simplejson
from lxml import html
from pick import pick


def main(argv):
    
    
    ZTF_name=str(sys.argv[1]) 
    
    for arg in sys.argv:
        print arg
    
	username = raw_input('Input Marshal username: ')
	password = getpass.getpass('Password: ')
    r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_programs.cgi', auth=(username, password))
    programs = json.loads(r.text)
    programidx = -1
    #print "Programs you are a member of:"
    for index, program in enumerate(programs):
       if program['name'] == "Redshift Completeness Factor":
          programidx = program['programidx']
          #print programidx
    
    if programidx >= 0:
      r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', auth=(username, password), 
          data={'programidx' : str(programidx)})
      sources = json.loads(r.text)
      #print sources
    
      for source in sources:
          if source['name']==ZTF_name:
              r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/source_summary.cgi', auth=(username, password),
                  data={'sourceid' : str(source['id'])})
              sourceDict = json.loads(r.text)
              annotations = sourceDict['autoannotations']
              # payload = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':'STRING','type':'IAU name','comment':'Test annotation'}
              # a = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
              #      data=payload)
              action = ['Remove','Replace','Add']
              sel_action = pick(action,"Select the action to perform on auto annotations",min_selection_count=1)
              if(sel_action[0]=='Remove' or sel_action[0]=='Replace'):
                sel_annot = pick(annotations,"Select the auto annotation to modify",min_selection_count=1)
                print "Your selected option is "+sel_action[0]+" the auto annotation "+sel_annot[0]['type']+" "+sel_annot[0]['comment']+" by "+sel_annot[0]['username']
                annot_id = sel_annot[0]['id']
                #print annot_id
                if(sel_action[0]=='Remove'):
                  print "Removing annotation with id "+str(annot_id)
                  payload = {'action':'delete','id':annot_id,'sourceid':str(source['id'])}
                  a = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
                      data=payload)
                elif(sel_action[0]=='Replace'):
                  datatype = raw_input("Enter datatype(STRING | INT | FLOAT | DOUBLE | BOOL): ")
                  atype = raw_input("Enter auto annotation type: ")
                  comment = raw_input("Enter comment: ")
                  print "Removing annotation with id "+str(annot_id)
                  payload = {'action':'delete','id':str(annot_id),'sourceid':str(source['id'])}
                  a = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
                      data=payload)
                  print "Commiting annotation with datatype : "+datatype+", type : "+atype+", comment : "+comment
                  payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':datatype,'type':atype,'comment':comment}
                  b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
                      data=payload1)
              elif(sel_action[0]=='Add'):
                datatype = raw_input("Enter datatype(STRING | INT | FLOAT | DOUBLE | BOOL): ")
                atype = raw_input("Enter auto annotation type: ")
                comment = raw_input("Enter comment: ")
                print "Commiting annotation with datatype : "+datatype+", type : "+atype+", comment : "+comment
                payload1 = {'action':'commit','id':-1,'sourceid':str(source['id']),'datatype':datatype,'type':atype,'comment':comment}
                b = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/add_autoannotation.cgi', auth=(username, password),
                    data=payload1)







if __name__=='__main__':
    main(sys.argv[1:])