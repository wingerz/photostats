from collections import defaultdict
import json
from optparse import OptionParser
import sqlite3 as sqlite
import sys

#Added changes for Python 3.5. Example: adding parethesis to the print commands
#Added: usage()

def usage():
    print("Usage:\n"," -c, --c\tlightroom database file","\n"," -o,--o\toutput file name (json)","\n")
 
def list_files(conn):
    query = """
SELECT folder.pathFromRoot, file.idx_filename, model.value, exif.dateDay, exif.dateMonth, exif.dateYear, exif.aperture, exif.flashFired, exif.focalLength, exif.isoSpeedRating, exif.shutterSpeed, img.fileFormat, img.fileHeight, img.fileWidth, img.orientation, img.rating, lens.value, img.captureTime
FROM
Adobe_images img,
AgLibraryFile file,
AgLibraryFolder folder,
AgHarvestedExifMetadata exif,
AgInternedExifCameraModel model,
AgInternedExifLens lens
WHERE
file.id_local = img.rootFile AND
folder.id_local = file.folder AND
img.id_local = exif.image AND
exif.cameraModelRef = model.id_local AND
exif.lensRef = lens.id_local

ORDER BY img.captureTime"""
    for row in conn.execute(query):
        filename = row[0] + row[1]
        data = {
            'camera_model': row[2],
            'name': row[1],
            'dir': row[0],
            'aperture': row[6],
            'flashFired': row[7],
            'focal_length': row[8],
            'iso': row[9],
            'shutter_speed': row[10],
            'format': row[11],
            'height': row[12],
            'width': row[13],
            'orientation': row[14],
            'rating': row[15],
            'lens': row[16],
            'capture_time': row[17],
        }
        if row[5] is not None:
            data['date'] = (int(row[5]), int(row[4]), int(row[3]))
        else:
            data['date'] = None
            
        yield filename, data

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--cat", dest="catalog", help="lightroom database file")
    parser.add_option("-o", "--out", dest="outfile", help="outputfile")
    (options, args) = parser.parse_args()

    if not options.catalog:
        print("no catalog specified")
        usage()
        sys.exit(1)
    
    lrcat = options.catalog
    conn = sqlite.connect(lrcat)
    seen_photos = defaultdict(list)
    for file, data in list_files(conn):
        seen_photos[(data['name'], data['date'])].append(data)

    file_metadata = []
    #for key, files in seen_photos.iteritems():

    for key, files in seen_photos.items() :
        file_metadata.append(files[0])
        if len(files) > 1:
            for file in files:
                print(file['name'] + '\t' +  file['dir'])
    with open(options.outfile, 'w') as f:
        f.write(json.dumps(file_metadata))

    #Adding some metrics in hte output
    print("Metrics\n","\ttotal photos:\t",len(seen_photos))
