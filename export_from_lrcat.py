from optparse import OptionParser
import sqlite3 as sqlite
import sys

def list_files(conn):
    query = """
SELECT folder.pathFromRoot, file.idx_filename, model.value
FROM
Adobe_images img,
AgLibraryFile file,
AgLibraryFolder folder,
AgHarvestedExifMetadata exif,
AgInternedExifCameraModel model
WHERE
file.id_local = img.rootFile AND
folder.id_local = file.folder AND
img.id_local = exif.image AND
exif.cameraModelRef = model.id_local

ORDER BY img.captureTime"""
    for row in conn.execute(query):
        filename = row[0] + row[1]
        data = {
            'camera_model': row[2]
        }
        yield filename, data

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--cat", dest="catalog", help="lightroom database file")
    options, args = parser.parse_args()

    if not options.catalog:
        print "no catalog specified"
        sys.exit(1)
    
    lrcat = options.catalog
    conn = sqlite.connect(lrcat)
    for file, data in list_files(conn):
        print file, data


    
