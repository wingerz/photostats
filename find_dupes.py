from collections import defaultdict
from optparse import OptionParser
import pprint
import sqlite3 as sqlite
import sys

def list_files(conn):
    query = """
SELECT folder.pathFromRoot, file.idx_filename, model.value, exif.dateDay, exif.dateMonth, exif.dateYear, img.captureTime, img.fileHeight, img.fileWidth
FROM
Adobe_images img,
AgLibraryFile file,
AgLibraryFolder folder,
AgHarvestedExifMetadata exif left join
AgInternedExifCameraModel model on exif.cameraModelRef = model.id_local
WHERE
file.id_local = img.rootFile AND
folder.id_local = file.folder AND
img.id_local = exif.image 
ORDER BY img.captureTime"""
    for row in conn.execute(query):
        filename = row[0] + row[1]
        data = {
            'camera_model': row[2],
            'name': row[1],
            'dir': row[0],
            'dimensions': (int(row[7]), int(row[8])),
        }

        if row[5] is not None:
            data['date'] = (int(row[5]), int(row[4]), int(row[3]))
        else:
            data['date'] = None
        data['datetime'] = row[6]
        yield filename, data

def file_key(file, ignore_ext=False, ignore_date=False):
    if ignore_date:
        capture_datetime = None
    else:
        capture_datetime = file['datetime']
    if ignore_ext:
        return file['name'].split('.')[0], capture_datetime
    else:    
        return file['name'], capture_datetime

def all_pairs(l):
    """Given a sorted list, return all pairs of elements."""
    results = []
    for i in xrange(len(l)):
        for j in xrange(i + 1, len(l)):
            results.append((l[i], l[j]))
    return results
    
def get_linked_folders(seen_photos):
    """Return folders with duplicate images."""

    count_dupe_files = 0

    # folder1: folder2: number of duplicates
    linked_folders = defaultdict(lambda:defaultdict(int))

    for key, files in sorted(seen_photos.items()):
        if len(files) > 1:
            count_dupe_files += 1
            dirs = list(set([file['dir'] for file in files]))
            dir_pairs = all_pairs(sorted(dirs))
            for dir_pair in dir_pairs:
                linked_folders[dir_pair[0]][dir_pair[1]] += 1

    return linked_folders, count_dupe_files

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--cat", dest="catalog", help="lightroom database file")
    parser.add_option("-i", "--ignore-ext", dest="ignore_ext", help="if present, ignore file extensions", action="store_true", default=False)
    parser.add_option("-d", "--ignore-capture-time", dest="ignore_capture_time", help="if present, ignore capture time", action="store_true", default=False)

    # optional for computing folder differences
    parser.add_option("-a", "--f1", dest="folder1", help="first folder to compare")
    parser.add_option("-b", "--f2", dest="folder2", help="second folder to compare")

    parser.add_option("-f", "--file", dest="debug_file", help="single file to check")
    
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
        seen_photos[file_key(data, options.ignore_ext, options.ignore_capture_time)].append(data)

    linked_folders, count_dupe_files = get_linked_folders(seen_photos)
    pair_counts = []
    for f1, f2counts in linked_folders.iteritems():
        for f2, count in f2counts.iteritems():
            pair_counts.append((f1, f2, count))
    pair_counts = sorted(pair_counts, key=lambda x: x[2], reverse=True)
    
    print "top 10 pairs"
    pprint.pprint(pair_counts[:10])    


    if options.debug_file:
        for key, data in seen_photos.iteritems():
            if options.debug_file == key[0]:
                print "folders for %s" % options.debug_file
                pprint.pprint(data)
    
    if options.folder1 and not options.folder2:
        files_in_folder = []
        for key, data in seen_photos.iteritems():
            for d in data:
                if options.folder1 == d['dir']:
                    files_in_folder.append((key, d['dimensions']))
                    break
        print "files in folder %s (%d)" % (options.folder1, len(files_in_folder))

        pprint.pprint(files_in_folder)
        single_files = []
        other_directories = defaultdict(list)
        for file_key, _ in files_in_folder:
            folders = seen_photos[file_key]
            if len(folders) == 1:
                single_files.append((file_key, folders[0]['dir']))
            else:
                for f in folders:
                    if f['dir'] != options.folder1:
                        other_directories[f['dir']].append((file_key, f['dimensions']))
        print "unduplicated files in %s (%d)" % (options.folder1, len(single_files))
        pprint.pprint(single_files)
        print "duplicated files in:"

        other_directories_sorted = sorted(other_directories.items(), key=lambda x: len(x[0][1]), reverse=True)

        files_in_folder_keys = [key for key, _ in files_in_folder]
        for folder, files in other_directories_sorted:
            print "%s (%d)" % (folder, len(files))
            for file, dimensions in files:
                print "\t%s %s" % (file, dimensions)
            files_keys = [file for file, _ in files]
            missing_files = set(files_in_folder_keys).difference(set(files_keys))
            print 'missing from %s (%d)' % (folder, len(missing_files))
            pprint.pprint(sorted(missing_files))

    if options.folder1 and options.folder2:
        print "folder comparison"
        by_folder = defaultdict(list)
        for _, files in seen_photos.iteritems():
            for file in files:
                if file['dir'] in (options.folder1, options.folder2):
                    by_folder[file['dir']].append(file_key(file, options.ignore_ext, options.ignore_capture_time))

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
