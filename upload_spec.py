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
import glob2
import getpass

def makeparser():#def_progname,def_tel_inst,def_obsdate,def_observer,def_reducer):
  parser = argparse.ArgumentParser()
  parser.add_argument("ZTF_name",help="Target name",nargs='+')
  parser.add_argument("--specfile",help="Path to spectrum file")
  parser.add_argument("--spectype",default="object",choices=['object','host','sky'],help="Choose spectrum type from options object,host and sky,"+
                      " by default it is object")
  parser.add_argument("--prog_name",default="Redshift Completeness Factor",help="Mention program name for target")
  parser.add_argument("--tel_instrument",default=os.environ.get('TEL_INSTRUMENT'),help="Mention telescope name and instrument name used in this exact format"+
                      " without the quotes: 'telescope + instrument'")
  parser.add_argument("--obsdate",help="Observation date",default = os.environ.get('OBSDATE'))
  parser.add_argument("--observer",help="Name of observer",default=os.environ.get('OBSERVER'))
  parser.add_argument("--reducer",help="Name of data reducer",default=os.environ.get('REDUCER'))
  return parser

def get_prog_id(prog_name):
  prog_dict = {'Afterglows of Fermi Gamma Ray Bursts':35,'Caltech Spectroscopic Dump':40,'Cataclysmic Variables':22,'Census of the Local Universe':19,
                'Cosmology':32,'Electromagnetic Counterparts to Gravitational Waves':17,'Electromagnetic Counterparts to Neutrinos':25,
                'Failed Supernovae':5,'Fast Transients':9,'Fremling Subtractions':1,'Garbage Dump':39,'Graham Nuclear Transients':12,
                'Infant Supernovae':14,'Nuclear Transients':10,'Orphan Afterglows Caltech':38,'Rapidly Evolving Transients':31,
                'Redshift Completeness Factor':24,'Red Transients':15,'Stripped Envelope Supernovae':29,'Superluminous Supernovae II':36,
                'Superluminous Supernovae':7,'Test Filter':37,'Test':34,'Transients in Elliptical Galaxies':27,'Variable AGN':13,'Young Stars':21,
                'ZTF Science Validation':3}
  return prog_dict[prog_name]

def get_inst_id(tel_instrument):
  inst_dict = {'EFT + Photometrizer':0,'GS + FLAMINGOS-2':1,'CTIO-4m + DECam':2,'VISTA + VIRCAM':3,'HST + WFC3/UVIS':4,'P48 + ZTF':5,'P60 + P60 Camera':6,
  'P200 + DBSP':7,'P200 + LFC':8,'P200 + WIRC':9,'Keck1 + LRIS':10,'Lick 3-m + KAST':11,'WHT + ISIS':12,'MDM24 + Mk III':13,'Wise1m1 + LAIWO':14,
  'Wise1m1 + PI':15,'HET + FORS2':16,'VLT + FORS2':17,'Keck2 + DEIMOS':18,'HET + LRS':19,'VLT + X-Shooter':20,'VLT + X-Shooter':21,'PTEL + PTEL':22,
  'Gemini N + GMOS':23,'UH88 + SNIFS':24,'WHT + ACAM':25,'GS + GMOS':26,'TNG + DOLORES':27,'KPNO4m + RC Spec':28,'NOT + ALFOSC':29,'GS + GMOS':30,
  'GS + GMOS-S':31,'UH88 + SNIFS':32,'C18 + Camera':33,'WHT + ACAM/NIRIS':34,'INT + IDS':35,'Gemini N + UVOT':36,'Swift + UVOT':37,'Magellan_Baade + IMACS':38,
  'Magellan_Clay + LDSS3':39,'LT + Frodospec':40,'APO + DIS':41,'Wise1m1 + FOSC':42,'Lick 3-m + GEMINI':43,'HET + LRS':44,'GTC + OSIRIS':45,'FTN + FS02':46,
  'FTN + FS03':47,'FTN + EM01':48,'FTS + EM03':49,'FTS + FS01':50,'FTS + FLOYDS':51,'P200 + TSPEC':52,'MLO + CCD':53,'FTN + FLOYDS':54,'LT + IOO':55,
  'LT + RATCam':56,'Magellan_Baade + FIRE':57,'SPM15 + RATIR':58,'IGO + iFOSC':59,'HCT + HCT Spectograph':60,'IRSF + Unknown':61,'KMTNet + 18KCCD':62,
  'SALT + Spectrograph':63,'P60 + SED-Machine':64,'P60 + SEDM':65,'WHT + ACAM':66,'LCOGT1m + SBIG':67,'DUP + WFCCD':68,'Swope + e2v':69,'Nanshan 1m + 1.2x1.2 deg^2 CCD':70,
  'Keck1 + MOSFIRE':71,'DCT + LMI':72,'CAHA 1.2m + CCD':73,'Ekar + AFOSCH':74,'Ekar + AFOSCH':75,'PS1 + PS1':76,'DFOT + ANDOR_2kx2k':77,'Keck2 + ESI':78,
  'LCOGT1m + Sinistro':79,'DCT + Deveny+LMI':80,'INT + IDS':81,'SDSS2.5m + BOSS':82,'Subaru FOCAS + FOCAS':83,'VLT + UVES':84,'NTT + EFOSC2':85,'LT + SPRAT':86,
  'XL216 + LAMOST':87,'LT + SPRAT':88,'MASTER-SAAO + NA':89,'MPI_ESO-2.2m + GROND':90,'Magellan_Clay + MEGACAM':91,'NOT + NOTCam':93,'PROMPT5 + CCD':94,
  'SSO + CCD':95,'Skymapper + Skymapper':96,'Zadko + AndorIKON-L':97,'CTIO-1.3m  + ANDICAM':98,'VISTA + OMEGACAM':99,'CNEOST + CCD':100}
  return inst_dict[tel_instrument]

def read_header(file,args):
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
        elif(user==''):
          user = args.observer
      if(hline[1]=='OBSUTC:'):
        obsdate = hline[2]+' '+hline[3][0:8]
        obsdate = datetime.datetime.strptime(obsdate,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
      if(hline[1]=='EXPTIME:'):
        exptime = hline[2].strip()
      if(hline[1]=='REDUCER:'):
        reducer = ' '.join(x for x in hline[2:])
        reducer = reducer.strip()
        if(reducer==''):
          reducer = args.reducer
      if(hline[1]=='OBSERVER'):
        user = ' '.join(x for x in hline[3:])
        user = user.strip()
        if(user=='' or user=='unknown' or user=='Unknown'):
          user = args.observer
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
      
  return tel,inst,user,obsdate,exptime,reducer,fformat

###### Fetch specfile function
def get_specfile(name):
  specfile = glob2.glob('spec_to_upload/'+name+'*')[0]
  print specfile
  return specfile

def main():
  parser = makeparser()#def_progname,def_tel_inst,def_obsdate,def_observer,def_reducer)
  args = parser.parse_args()
  #print args
  username = raw_input('Input Marshal username: ')
  password = getpass.getpass('Password: ')
  r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_programs.cgi', auth=(username, password))
  programs = json.loads(r.text)
  #print programs
  programidx = -1
  #print "Programs you are a member of:"
  for index, program in enumerate(programs):
     if program['name'] == args.prog_name:
        programidx = program['programidx']
        #print programidx

  if programidx >= 0:
    r = requests.post('http://skipper.caltech.edu:8080/cgi-bin/growth/list_program_sources.cgi', auth=(username, password), 
        data={'programidx' : str(programidx)})
    sources = json.loads(r.text)
  
    for source in sources:
        if(source['name'] in args.ZTF_name):
  ################### To upload spectra
            ###### Uncomment following line to automatically fetch specfile, comment out the next line
            specfile = get_specfile(source['name'])
            #specfile = args.specfile
            tel,inst,user,obsdate,exptime,reducer,fformat = '','','','','','',''
            tel,inst,user,obsdate,exptime,reducer,fformat = read_header(specfile,args)
            #print tel,inst,user,obsdate,exptime,reducer,fformat
            if(tel == '' or inst == ''):
              telname = args.tel_instrument
            else:
              telname = tel+' + '+inst
            if(user == ''):
              user = args.observer
            if(obsdate == ''):
              obsdate = args.obsdate
            if(reducer == ''):
              reducer = args.reducer
            print tel,inst,user,obsdate,exptime,reducer,fformat
            files = {'upfile' : open(specfile)}
            payload = {'sourceid' : str(source['id']),'spectype':args.spectype,'programid':get_prog_id(args.prog_name),'instrumentid':get_inst_id(telname),
                      'format':fformat,'obsdate':obsdate,'exptime':exptime,'observer':user,'reducedby':reducer,'class':"",'redshift':"",
                      'phase':"",'comment':"",'commit':'yes','submit':'upload the file'}
            #print payload
            a = requests.post(url='http://skipper.caltech.edu:8080/cgi-bin/growth/add_spec.cgi', auth=(username, password),data=payload,files=files)
            print(a.text)

if __name__=='__main__':
    main()