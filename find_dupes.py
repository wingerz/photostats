from collections import defaultdict
from optparse import OptionParser
import pprint
import sqlite3 as sqlite
import sys

def list_files(conn):
    query = """
SELECT folder.pathFromRoot, file.idx_filename, model.value, exif.dateDay, exif.dateMonth, exif.dateYear, img.captureTime
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
            'camera_model': row[2],
            'name': row[1],
            'dir': row[0],
        }

        if row[5] is not None:
            data['date'] = (int(row[5]), int(row[4]), int(row[3]))
        else:
            data['date'] = None
        data['datetime'] = row[6]
        yield filename, data

def file_key(file, ignore_ext=False):
    if ignore_ext:
        return file['name'].split('.')[0], file['datetime']
    else:    
        return file['name'], file['datetime']

        
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--cat", dest="catalog", help="lightroom database file")
    parser.add_option("-i", "--ignore-ext", dest="ignore_ext", help="if present, ignore file extensions", action="store_true", default=False)

    # optional for computing folder differences
    parser.add_option("-a", "--f1", dest="folder1", help="first folder to compare")
    parser.add_option("-b", "--f2", dest="folder2", help="second folder to compare")
    
    options, args = parser.parse_args()

    if not options.catalog:
        print "no catalog specified"
        sys.exit(1)
    
    lrcat = options.catalog
    conn = sqlite.connect(lrcat)
    seen_photos = defaultdict(list)
    count_no_date = 0
    for file, data in list_files(conn):
        if 'dupes temp' in data['dir']:
            continue
        
        if data['datetime'] is None:
            count_no_date += 1
        seen_photos[file_key(data, options.ignore_ext)].append(data)

    count_dupe_files = 0
    linked_folders = defaultdict(lambda:defaultdict(int))
    for key, files in sorted(seen_photos.items(), key=lambda x: (x[0][1], x[0][0], x[1])):
        if len(files) > 1:
            count_dupe_files += 1
            for file in files:
                print file['name'] + '\t' +  file['dir']
            dirs = [file['dir'] for file in files]
            if len(dirs) == 2:
                dirs = sorted(dirs)
                linked_folders[dirs[0]][dirs[1]] += 1
            else:
                print len(dirs)

    all_pairs = []
    for f1, f2counts in linked_folders.iteritems():
        for f2, count in f2counts.iteritems():
            all_pairs.append((f1, f2, count))
    sorted(all_pairs, key=lambda x: x[2], reverse=True)
    
    print "top 10 pairs"
    pprint.pprint(all_pairs[:10])    

    if options.folder1 and not options.folder2:
        files_in_folder = []
        for key, data in seen_photos.iteritems():
            if options.folder1 in [d['dir'] for d in data]:
                files_in_folder.append(key)
        print "files in folder %s (%d)" % (options.folder1, len(files_in_folder))
        pprint.pprint(files_in_folder)
        single_files = []
        other_directories = set()
        for file_key in files_in_folder:
            folders = seen_photos[file_key]
            if len(folders) == 1:
                single_files.append((file_key, folders[0]['dir']))
            else:
                for f in folders:
                    if f['dir'] != options.folder1:
                        other_directories.add(f['dir'])
        print "unduplicated files in %s (%d)" % (options.folder1, len(single_files))
        pprint.pprint(single_files)
        print "duplicated files in:"
        pprint.pprint(other_directories)

    if options.folder1 and options.folder2:
        print "folder comparison"
        by_folder = defaultdict(list)
        for _, files in seen_photos.iteritems():
            for file in files:
                if file['dir'] in (options.folder1, options.folder2):
                    by_folder[file['dir']].append(file_key(file, options.ignore_ext))

        set1 = set(by_folder[options.folder1])
        set2 = set(by_folder[options.folder2])

        if len(set1) != len(by_folder[options.folder1]):
            print '%s has duplicates' % options.folder1

        if len(set2) != len(by_folder[options.folder2]):
            print '%s has duplicates' % options.folder2
        
        in1 = set1.difference(set2)
        in2 = set2.difference(set1)
        inboth = set1.intersection(set2)

        print "in both (%d):" % (len(inboth))
        pprint.pprint(inboth)
        print "only in %s (%d):" % (options.folder1, len(in1))
        pprint.pprint(in1)
        print "only in %s (%d):" % (options.folder2, len(in2))
        pprint.pprint(in2)

        
    print "%d files with no date" % count_no_date
    print "%d files with duplicates" % count_dupe_files
    print "%d unique files" % len(seen_photos)
