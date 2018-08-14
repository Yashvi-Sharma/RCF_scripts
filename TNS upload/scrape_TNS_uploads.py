import re, requests
from getpass import getpass

def get_classification_date(name, auth):
	'''takes the date from the latest [classification] comment. #TODO redo with lxml.html.xpath() '''
	r = requests.post("http://skipper.caltech.edu:8080/cgi-bin/growth/view_source.cgi", data={'name': name.strip()}, auth=auth)
	content = r.content
	classid = content.find('[classification]')
	date = re.findall(r'20\d\d \w\w\w \d\d', content[:classid])[-1]
	return date

def bad_names():
	'''returns a list of objnames classified on or before Jul 10 or that have otherwise been found unsuitable'''
	old =  ['ZTF18aabxlsv', 'ZTF18aagpzjk', 'ZTF18aagrdcs', 'ZTF18aagrtxs', 'ZTF18aahfeiy', 'ZTF18aahfqbc', 
			'ZTF18aahfzea', 'ZTF18aahhenr', 'ZTF18aahhqih', 'ZTF18aahhzqn', 'ZTF18aahjafd', 'ZTF18aahmhxu', 
			'ZTF18aahpbwz', 'ZTF18aahptcq', 'ZTF18aahqmsr', 'ZTF18aainvic', 'ZTF18aaisyyp', 'ZTF18aajqcue', 
			'ZTF18aajtlbf', 'ZTF18aakaljn', 'ZTF18aakctzv', 'ZTF18aakgzot', 'ZTF18aakrnvd', 'ZTF18aakzliv', 
			'ZTF18aalcxig', 'ZTF18aamfrvy', 'ZTF18aamigmk', 'ZTF18aaotzhu', 'ZTF18aaovbiy', 'ZTF18aaphzut', 
			'ZTF18aapictz', 'ZTF18aaqcqvr', 'ZTF18aaqcugm', 'ZTF18aaqedfj', 'ZTF18aaqehoc', 'ZTF18aaqfqaa', 
			'ZTF18aaqfziz', 'ZTF18aaqgadq', 'ZTF18aaqjhqz', 'ZTF18aaqjovh', 'ZTF18aaqkoyr', 'ZTF18aaqkqxi', 
			'ZTF18aaqpjja', 'ZTF18aaqpkvx', 'ZTF18aaqqoqs', 'ZTF18aaqskoy', 'ZTF18aaqznkg', 'ZTF18aaraifg', 
			'ZTF18aarbgdn', 'ZTF18aarbify', 'ZTF18aarcygc', 'ZTF18aarcypa', 'ZTF18aaripcr', 'ZTF18aaroihe', 
			'ZTF18aartimj', 'ZTF18aasdted', 'ZTF18aaslhxt', 'ZTF18aasufva', 'ZTF18aasycpd', 'ZTF18aataafd', 
			'ZTF18aatlfus', 'ZTF18aatyqds', 'ZTF18aatzygk', 'ZTF18aauizcr', 'ZTF18aaumeys', 'ZTF18aaunfqq', 
			'ZTF18aaupmks', 'ZTF18aauqdyb', 'ZTF18aauworo', 'ZTF18aauxltf', 'ZTF18aauxzle', 'ZTF18aavjcpf', 
			'ZTF18aavjnfx', 'ZTF18aavnvmp', 'ZTF18aavqdyq', 'ZTF18aavrmcg', 'ZTF18aawjywv', 'ZTF18aawrmhl', 
			'ZTF18aawyjjq', 'ZTF18aaxcntm', 'ZTF18aaxjuwy', 'ZTF18aaxkfos', 'ZTF18aaxkqgy', 'ZTF18aaytovs', 
			'ZTF18aayxupv', 'ZTF18aazgfkq', 'ZTF18aazhklh', 'ZTF18abajlni', 'ZTF18abbqjds', 'ZTF18abckxfb', 
			'ZTF18abclfee', 'ZTF18abcvush', 'ZTF18abcysdx', 'ZTF18abcyues', 'ZTF18abdbysy', 'ZTF18abdefet', 
			'ZTF18abdfaqi', 'ZTF18abdfazk', 'ZTF18abdfwur', 'ZTF18abdfydj', 'ZTF18abdgwxn', 'ZTF18abdhsfc', 
			'ZTF18abdiqdh', 'ZTF18abdjmfh', 'ZTF18abdmlya', 'ZTF18abeajml', 'ZTF18abecbks', 'ZTF18abfhryc']
	bad = ['ZTF18abgzkmf', 'ZTF18abklaoj', 'ZTF18abgkjff'] # never uploaded to TNS because no new spectrum, classification from elsewhere
	return tuple(old + bad)

		
def main():
	'''
	oh no it is a terrible manual html-parsing mess I made in a hurry
	#TODO redo it with lxml.html.xpath or something
	
	returns: a list of tuples (ZTF_name (str), classification_date (str, YYYY-MM-DD), classification (str) )
			 eg: [('ZTF18abcdefg', '2018-01-01', 'SN Ia'), ...]
			 for objects:
				 -without [TNS_upload_date] autoannotation
				 -AND with [Classification] comment
				 -AND classified no later than 2018-07-10
				 -AND that weren't manually excluded in bad_names()
	'''
	auth = (raw_input('Skipper username:'), getpass())
	startind = 225 # you can skip this many if you know there are at least this many RCF objs already in TNS
	
	i = startind
	dump = ""   # all of the html after the last [TNS upload date] across all pages
	while True:
		t = requests.get("http://skipper.caltech.edu:8080/cgi-bin/growth/list_sources_bare.cgi", auth=auth, 
						 params={'programidx': 14,
								 'sortby': "TNS_upload_date",
								 'offset': i,
								'reverse': 0})
		content = t.content.split('[TNS_upload_date]:')[-1]
		total_objs = int(re.findall(r'\d+ of \d+', content)[0].split(' of ')[1])
		not_in_tns = len(content.split('<a href="view_source.cgi?name=')) - 1

		i += 100
		if not_in_tns < 100 and i < total_objs:
			print "only", not_in_tns, "still need uploading" 
			# you can occasionally add a number less than (100 - not_in_tns) to startind. Should be <, not <= so you can tell if you skipped too many
		dump += content
		
		total_number = int(re.findall(r'\d+ of \d+', content)[0].split(' of ')[1])
		print '{}/{}'.format(i - startind, total_number - startind)
		if i >= total_number:
			print '-------------done-------------'
			break

	name_classes = []
	for chunk in dump.split('<a href="view_source.cgi?name=')[1:]:
		name = chunk[chunk.find('>') + 1:chunk.find('<')]
		classi = chunk.split('</font><br><font size="1" color="white" style="line-height:30%">.<br></font> \n             </font></td>   \n             <td align=left valign=top><font face="Myriad Pro" size="2">')[1].split('\n')[0]
		name_classes.append((name, classi))
	print '{:>5} not in TNS'.format(len(name_classes))
	
	# doesn't contain '?', has 'SN' or 'CV'
	good_names = [nc for nc in name_classes if (nc[1].find('SN') >= 0 or nc[1].find('CV') >= 0) and nc[1].find('?') < 0]
	print '{:>5} SNs/CVs'.format(len(good_names))
	
	bn = bad_names()
	new_names = [name_class for name_class in good_names if name_class[0] not in bn]
	print '{:>5} not in the bad list'.format(len(new_names))
	
	if len(new_names):
		print '-------classified dates-------'
		name_date_class = [(nn[0], get_classification_date(nn[0]), nn[1]) for nn in new_names]
		for ndc in name_date_class:
			print '\t'.join(ndc)
	return new_names
	
	 
if __name__ == '__main__':
	main()
