#!/usr/bin/python

import web, os, requests
from datetime import datetime
from fontTools.ttLib import TTFont

web.config.debug = False  # to be able to use session
DEBUG            = False  # dev mode

urls = (
	'/', 'index',           # The visibile app
	'/thefont', 'thefont',  # Serve the uploaded .woff file
	'/thedata', 'thedata'   # Serve the .ttx file (XML info file of font)
)

app       = web.application(urls, globals())
session   = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'fontdata': False, 'filepath': False, 'error': False})
render    = web.template.render('templates/')

workspace = "/".join(os.path.realpath(__file__).split("/")[:-2]) # /home/ubuntu/workspace/bin/app.py -> /home/ubuntu/workspace

# Return .woff file
class thefont:
	def GET(self):
		if session.filepath and os.path.isfile(session.filepath):
			return open(session.filepath, 'r').read()
		else:
			raise web.notfound()

# Return .ttx file
class thedata:
	def GET(self):
		if session.filepath and os.path.isfile(session.filepath):

			web.header("Content-Disposition", "attachment; filename=%s.ttx" % session.filename.rsplit('.', 1)[0])
			web.header("Content-Type", "text/plain; charset=utf-8")
			web.header("Transfer-Encoding","chunked")

			if not os.path.isfile(session.filepath + '.ttx'):
				os.system('ttx -o "' + session.filepath + '.ttx" "' + session.filepath + '"')

			return open(session.filepath + ".ttx", 'r').read()
		else:
			raise web.notfound()

# App
class index:
	def GET(self):
		error   = session.error
		content = session.fontdata
		session.error = ""

		# Dev mode: recall fontdata every time
		if DEBUG and session.filepath and os.path.isfile(session.filepath):
			content = fontdata(
				filename=session.filename,
				filesize=session.filesize,
				filetype=session.filetype,
				file=open(session.filepath, "r"))

		web.header('Content-Type','text/html; charset=utf-8', unique=True)
		return render.index(error=error, fontdata=content)

	def POST(self):
		x = web.input(file={})

		if x['file'].filename != "":
			filename  = x['file'].filename
			file      = x['file'].file
			filesize  = os.fstat(file.fileno()).st_size
		else:
			filename  = x['url']
			file      = False
			if filename == "":
				raise web.seeother("/")

			try:
				response = requests.get(filename)
			except Exception as e:
				etype = e.__class__.__name__
				msg   = etype + ": " + {
					'HTTPError'            : "An HTTP error occurred.",
					'ConnectionError'      : "A Connection error occurred.",
					'ProxyError'           : "A proxy error occurred.",
					'SSLError'             : "An SSL error occurred.",
					'Timeout'              : "The request timed out.",
					'ConnectTimeout'       : "The request timed out while trying to connect to the remote server.",
					'ReadTimeout'          : "The server did not send any data in the allotted amount of time.",
					'URLRequired'          : "A valid URL is required to make a request.",
					'TooManyRedirects'     : "Too many redirects.",
					'MissingSchema'        : "The URL schema (e.g. http or https) is missing.",
					'InvalidSchema'        : "The URL schema is invalid (accepts http or https)",
					'InvalidHeader'        : "The request was somehow invalid.",
					'ChunkedEncodingError' : "The server declared chunked encoding but sent an invalid chunk.",
					'ContentDecodingError' : "Failed to decode response content.",
					'StreamConsumedError'  : "The content for this response was already consumed.",
					'RetryError'           : "Custom retries logic failed.",
					'UnrewindableBodyError': "Requests encountered an error when trying to rewind a body"
				}.get(etype,  str(e))

				session.error = msg
				raise web.seeother("/")

			filesize  = int(response.headers['content-length'])

		# Check we've got a valid font extension (TTF/OTF/WOFF)
		extension = os.path.splitext(filename)[1][1:].lower()
		convert   = False

		if extension == "ttf" or extension == "otf":
			convert = True
		elif extension == "woff" or extension == "woff2":
			convert = False
		else:
			session.error = "The file type \"" + extension + "\" isn't allowed";
			raise web.seeother('/')

		session.error    = False
		session.fontdata = False

		# Store uploaded file in /tmp (dev mode)
		os.system("rm /tmp/" + session.session_id + "*")
		filepath = '/tmp/' + session.session_id + "." + extension # re.sub('[^-a-zA-Z0-9_.() ]+', '', x['file'].filename)

		if file:
			fout = open(filepath, 'w')
			fout.write(file.read())
			fout.close()
		else:
			fout = open(filepath, 'w')
			fout.write(response.content)
			fout.close()
			file = open(filepath, 'r')

		# Convert to WOFF
		filetype = extension
		if convert:
			os.system(workspace + '/ttf2woff-1.2/ttf2woff -t woff "' + filepath + '" "' + filepath + '.woff"')
			filepath += ".woff"
			filetype  = "woff"

		session.filepath = filepath
		session.filename = filename
		session.filesize = filesize
		session.filetype = filetype

		# Retrieve font informations
		if not DEBUG:
			file.close()
			file = open(filepath, "r")

			content = str(fontdata(filename, filetype, filesize, file))
			session.fontdata = content

		raise web.seeother('/')

#+---------------------------------------------------------
#| HELPER GET FONT DATA
#+---------------------------------------------------------

# DejaVuSans.ttf, woff, 147000, <ressource file>
def fontdata(filename, filetype, filesize, file):
	font     = TTFont(file)
	basename = filename.rsplit('.', 1)[0]

	# Info
	head = [] 
	head.append(str(font['maxp'].numGlyphs) + " glyphs")
	head.append(hsize(filesize))

	date  = "created: " + dateformat(font['head'].created)
	date += " (modified: " + dateformat(font['head'].modified) + ")"
	head.append(date)

	# Get metadatas
	metadatas = []
	data = {}
	for name in font['name'].names:
		data[name.nameID] = {
			"name" : namerecord(str(name.nameID)),
			"value": str(name).decode('utf-8','ignore').encode("utf-8")
		}

	for index in sorted(data.keys(), key=int):
		metadatas.append(data[index]);

	# Get list of glyphs
	data   = font['cmap'].tables[0].cmap
	codes  = {}
	glyphs = {}

	for index in data:
		codes[data[index]] = index

		row = str(int(index/16))
		if not row in glyphs:
			glyphs[row] = {}
		glyphs[row][index] = data[index]

	cmap = glyphs.items()
	cmap.sort( key=lambda i: int(i[0]) )

	data   = None
	glyphs = None

	# Get features list for GPOS and GSUB
	features = []
	for table in ['GPOS', 'GSUB']:
		if not table in font:
			continue
		data = {}

		for record in font[table].table.FeatureList.FeatureRecord:
			feature = str(record.FeatureTag)
			index   = record.Feature.LookupListIndex[0]
			data[index] = {"index": index, "feature": feature, "table": table}

		index = -1
		for lookup in font[table].table.LookupList.Lookup:
			index += 1
			if not index in data:
				continue

			table = lookup.SubTable[0]
			# data[index]["format"] = table.Format

			if hasattr(table, 'mapping'):
				data[index]["glyphs"] = {codes[clean(k)]:k for k in table.mapping}
			elif hasattr(table, 'alternates'):
				data[index]["glyphs"] = {codes[clean(k)]:k for k in table.alternates}
			elif hasattr(table, 'ligatures'):
				data[index]["glyphs"] = {codes[clean(k)]:k for k in table.ligatures}
			elif hasattr(table, 'Coverage'):
				data[index]["glyphs"] = {codes[clean(k)]:k for k in table.Coverage.glyphs}
			elif data[index]["feature"] == "mark" or data[index]["feature"] == "mkmk":
				for t in table.__dict__.keys():
					if not t.endswith("Coverage"):
						continue
					data[index]["glyphs"] = {codes[clean(k)]:k for k in getattr(table, t).glyphs}
			else:
				print data[index]
				print table.__dict__.keys()

		for index in sorted(data.keys(), key=int):
			features.append(data[index]);

	return render.fontdata(
		filename,
		basename,
		filetype,
		metadatas,
		features,
		head,
		cmap)

def clean(s):
	return os.path.splitext(s)[0]

def namerecord(nameID):
	# https://localfonts.eu/typography-basics/type-design-tips-and-tricks/font-family-naming/
	return {
		'0': "Copyright",
		'1': "Family Name",           # My Family Light
		'2': "Subfamily Name",        # Bold Italic
		'3': "Id",
		'4': "Full Name",
		'5': "Version",
		'6': "PostScript Name",       # MyFamily-SemiBoldItalic
		'7': "Trademark",
		'8': "Manufacturer",
		'9': "Desginer",
		'10': "Description",
		'11': "Manufacturer URL",
		'12': "Designer URL",
		'13': "License Description",
		'14': "License URL",
		'16': "OpenType Family Name",     # My Family
		'17': "OpenType Subfamily Name",  # Semibold Italic
		'18': "Mac Family Name",
		'19': "Sample text",
		'20': "PostScript CID findfont name",
		'21': "WWS Family Name",
		'22': "WWS Subfamily Name",
		'23': "Light Background Palette",
		'24': "Dark Background Palette",
		'25': "Variations PostScript Name Prefix"
	}.get(nameID, "#" + nameID)

# https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
def dateformat(time):
	epoch_diff = -2082844800 # calendar.timegm((1904, 1, 1, 0, 0, 0, 0, 0, 0))
	return datetime.fromtimestamp(time + epoch_diff).strftime('%Y-%m-%d')

def hsize(size, precision=2):
    suffixes    = ['B','KB','MB','GB','TB']
    suffixIndex = 0

    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1
        size         = size/1024.0
    return "%.*f%s" % (precision, size, suffixes[suffixIndex])

#+---------------------------------------------------------
#| RUN
#+---------------------------------------------------------

if __name__ == "__main__":

	# Cleanup /tmp dir
	os.system("find /tmp -atime +1 -type f -exec rm {} \;")
	app.run()