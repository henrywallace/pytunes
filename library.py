'''Recover playlists from iTunes music library XML.
'''
import logging
import os
import plistlib
import shutil
from urllib.parse import unquote

import regex as re
from multiprocess import Pool, cpu_count

logger = logging.getLogger(__name__)


class Library(object):
    '''
    '''
    def __init__(self, library_filename, itunes_directory=None):
        '''

        `library_filename` or `itunes_directory` will be tilde expanded.

        If `itunes_directory` is None, it's set to the parent directory of
        `library_filename`.
        '''
        self.library_filename = os.path.expanduser(library_filename)
        if itunes_directory is None:
            self.itunes_directory = os.path.dirname(self.library_filename)

        with open(self.library_filename, 'rb') as f:
            self.library = plistlib.load(f)
        logger.info('Successfully loaded {}'
                    .format(self.library_filename))

    def playlist_paths(self):
        '''Construct playlist hierarchy referenced by "Persistent ID"s, which we call
        `pid`s.

        '''
        parents = {}  # pid to parent pid
        playlists = {}  # pid to playlist dict

        for playlist in self.library['Playlists']:
            if 'Distinguished Kind' in playlist:
                continue
            elif playlist.get('Name') == 'Library':
                continue

            pid = playlist['Playlist Persistent ID']
            playlists[pid] = playlist

            parent_pid = playlist.get('Parent Persistent ID')
            if parent_pid is not None:  # if playlist is inside a playlist
                parents[pid] = parent_pid

        # pids of playlists that don't contain nested playlists
        leafs = set(playlists) - set(parents.values())

        paths = []
        for leaf_pid in leafs:
            pid = leaf_pid
            path = [pid]
            while pid in parents:
                pid = parents[pid]
                path.append(pid)
            paths.append(list(reversed(path)))

        return playlists, paths

    def path_of_track(self, tid):
        if isinstance(tid, int):
            tid = str(tid)  # for some reason the itl has both :(
        track = self.library['Tracks'][tid]
        path = unquote(track['Location'])
        repl = os.path.join(self.itunes_directory, '')  # end in slash
        path = re.sub(r'file://.*/iTunes/', repl, path)
        if os.path.exists(path):
            return path

        # Now we have to try harder...

        def normalize(filename):
            return re.sub(r'^[\d- ]+', '', filename)

        target = normalize(os.path.basename(path))
        dirname = os.path.dirname(path)
        seen = set()
        max_steps = 2

        for _ in range(max_steps):
            if dirname in seen:
                continue
            seen.add(dirname)
            for dirpath, _, filenames in os.walk(dirname):
                for filename in filenames:
                    if normalize(filename) == target:
                        return os.path.join(dirpath, filename)
            dirname = os.path.dirname(dirname)

        return path

    def copy_playlist_tracks(self, playlist, dst):
        for track in playlist['Playlist Items']:
            track_path = self.path_of_track(track['Track ID'])
            try:
                shutil.copy(track_path, dst)
            except KeyboardInterrupt:
                exit(1)
            except:
                logger.warning("Can't find {} for playlist {}"
                               .format(track_path, playlist['Name']))

    def copy_playlists(self, target_directory):
        '''Copy playlists from iTunes library to `target_directory`.
        '''
        target_directory = os.path.expanduser(target_directory)
        playlists, pid_paths = self.playlist_paths()

        def copy_playlist(pid_path):
            named_path = '/'.join(playlists[pid]['Name'] for pid in pid_path)
            directory = os.path.join(target_directory, named_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            playlist = playlists[pid_path[-1]]
            self.copy_playlist_tracks(playlist, directory)

        pid_paths = sorted(pid_paths)

        pool = Pool(processes=cpu_count())
        for _ in pool.imap_unordered(copy_playlist, pid_paths):
            pass


def main():
    logging.basicConfig(level=logging.INFO)
    library_filename = ('/Volumes/Manticore 2/Henry’s MacBook Pro (2)/'
                        '2015-07-03-161447/Macintosh HD/Users/henry/'
                        'Music/iTunes/iTunes Music Library.xml.last')
    library = Library(library_filename)

    target_directory = '~/Desktop/playlists/'
    library.copy_playlists(target_directory)


if __name__ == '__main__':
    main()
