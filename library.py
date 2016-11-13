import plistlib
import os
import regex as re
from urllib.parse import unquote
import shutil
import logging


logger = logging.getLogger(__name__)


class Library(object):
    def __init__(self, itunes_path):
        self.itunes_path = itunes_path
        self.library_path = self.find_library_path()
        self.library = None

        if self.library_path is not None:
            with open(self.library_path, 'rb') as f:
                self.library = plistlib.load(f)
            logger.info('Successfully loaded {}'.format(self.library_path))

    def find_library_path(self):
        for fn in os.listdir(self.itunes_path):
            if fn.startswith('iTunes Music Library.xml'):
                break
        else:
            logging.warning('Unable to find iTunes Library path in {}'
                            .format(self.itunes_path))
            return None

        return os.path.join(self.itunes_path, fn)

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
        return re.sub(r'file://.*/iTunes/', self.itunes_path, path)

    def copy_playlist_tracks(self, playlist, dst):
        for track in playlist['Playlist Items']:
            track_path = self.path_of_track(track['Track ID'])
            try:
                shutil.copy(track_path, dst)
            except:
                logger.warning("Can't find {} for playlist {}"
                               .format(track_path, playlist['Name']))

    def copy_playlists(self, root_path):
        # create folders for playlists
        playlists, paths = self.playlist_paths()

        paths = sorted(paths)
        for pid_path in paths:
            named_path = '/'.join(playlists[pid]['Name'] for pid in pid_path)
            directory = os.path.join(root_path, named_path)
            if not os.path.exists(directory):
                os.makedirs(directory)

            playlist = playlists[pid_path[-1]]
            self.copy_playlist_tracks(playlist, directory)


def main():
    logging.basicConfig(level=logging.INFO)
    itunes_path = ('/Volumes/Manticore 2/Henry’s MacBook Pro (2)/'
                   '2015-07-03-161447/Macintosh HD/Users/henry/'
                   'Music/iTunes/')
    library = Library(itunes_path)
    library.copy_playlists(os.path.expanduser('/Volumes/DELPHI/old-playlists'))


if __name__ == '__main__':
    main()
