import os,requests
import aeneas.globalconstants as gc
import aeneas.globalfunctions as gf
from aeneas.executetask import ExecuteTask
from aeneas.language import Language
from aeneas.syncmap import SyncMapFormat
from aeneas.task import Task
from aeneas.task import TaskConfiguration
from aeneas.textfile import TextFileFormat
from bs4 import BeautifulSoup
from mutagen.id3 import ID3, USLT, TIT2
from mutagen.mp4 import MP4

TOKEN = 'L0s4uQQnLQILxY4DUoBCXxfELE4smQiTcVqZ5cBtxgecdJqUzmH6Ux_g4365toN6'  # Genius API Token
MUSIC_FOLDER = "/Users/Alexandre/Music/iTunes/iTunes Media/Music"
SEARCH_FAIL = 'The lyrics for this song were not found!'
URL = 'https://api.genius.com'
os.environ["PYTHONDONTWRITEBYTECODE"] = "None"
errors = newLyrics = lyricsFound = totalFiles = filesVerified = lyricsSynced = 0
searchEnabled = True
syncEnabled = True
searchAllLyrics = False

try:
    with open(MUSIC_FOLDER+'/verifList.txt') as f:
        verified = f.read().splitlines()
except FileNotFoundError:
    with open(MUSIC_FOLDER+'/verifList.txt', "w") as f:
        f.write("")
    verified = []


def request_song_info(param1, param2):
    headers = {'Authorization': 'Bearer ' + TOKEN}
    search_url = URL + '/search'
    data = {'q': param1 + ' ' + param2}
    response = requests.get(search_url, data=data, headers=headers)
    return response

def scrap_song_url(url):
    page = requests.get(url)
    html = BeautifulSoup(page.text, 'html.parser')
    [h.extract() for h in html('script')]
    lyrics = html.find('div', class_='lyrics').get_text()
    return lyrics

def getSongInfo(title, artist, param2):
    # Search for matches in request response
    response = request_song_info(title, param2)
    json = response.json()
    for hit in json['response']['hits']:
        if artist.lower() in hit['result']['primary_artist']['name'].lower() or hit['result']['primary_artist']['name'].lower() in artist.lower():
            return hit
    return None

def countfiles(file):
    if os.path.isdir(file):
        list = os.listdir(file)
        for element in list:
            countfiles(file + "/" + element)
    else:
        global totalFiles
        if ".mp3" in file or ".m4a" in file:
            totalFiles += 1

def enhanceLyrics(lyrics):
    tempLyrics = lyrics
    for k in range(len(lyrics) - 1, 2, -1):
        if lyrics[k] == '\\' and lyrics[k - 1] == '\\' and lyrics[k - 2] == '\\':
            tempLyrics = tempLyrics[:k - 2] + tempLyrics[k:]
    tempLyrics2 = tempLyrics
    for i in range(0, len(tempLyrics)):
        if tempLyrics[i] != '\n':
            break
        else:
            tempLyrics2 = tempLyrics[i + 1:]
    finalLyrics = tempLyrics2
    for i in range(len(tempLyrics2) - 1, 0, -1):
        if tempLyrics2[i] != '\n':
            break
        else:
            finalLyrics = tempLyrics2[:i]
    return finalLyrics

def createSyncedLyricsFile(lyrics, file):
    global lyricsSynced, errors
    f = open("tempSync.txt", "w+")
    f.write(lyrics)
    f.close()
    config = TaskConfiguration()
    config[gc.PPN_TASK_LANGUAGE] = Language.FRA
    config[gc.PPN_TASK_IS_TEXT_FILE_FORMAT] = TextFileFormat.PLAIN
    config[gc.PPN_TASK_OS_FILE_FORMAT] = SyncMapFormat.AUDH
    task = Task()
    task.configuration = config
    try:
        task.audio_file_path_absolute = file
        task.text_file_path_absolute = "tempSync.txt"
        ExecuteTask(task).execute()
        syncedLyricsFile = open(file[:-4] + ".lrc", "w+")
        for fragment in task.sync_map_leaves():
            syncedLyricsFile.write(
                str('[' + gf.time_to_hhmmssmmm(fragment.interval.begin, '.')[3:-1] + ']' + fragment.text + '\n'))
        syncedLyricsFile.close()
        print("   Sync Added", sep=' ', end='', flush=True)
        lyricsSynced += 1
    except Exception as e :
        errors += 1
        print("   Sync error", sep=' ', end='',flush=True)

def completeTags(tags, file):
    global lyricsFound, errors, newLyrics, filesVerified, searchEnabled, lyricsSynced
    filesVerified += 1
    tagDict = {}
    lyrics = ""
    if ".mp3" in file:
        tagDict = {"title": "TIT2", "album": "TALB", "artist": "TPE1", "albArtist": "TPE2", "lyrics": "USLT",
                   "completeLyrics": "USLT::eng"}
    elif ".m4a" in file:
        tagDict = {"title": "©nam", "album": "©alb", "artist": "©ART", "albArtist": "aART", "lyrics": "©lyr",
                   "completeLyrics": "©lyr"}
    if tagDict["title"] in tags:
        print("\n"+tag(tags, tagDict["title"]) + "    " + str(filesVerified) + "/" + str(totalFiles), sep=' ', end='',
              flush=True)
        if tagDict["album"] in tags:
            album = tag(tags, tagDict["album"])
        else:
            album = ""
        lyricsInFile = False
        for t in tags:
            if tagDict["lyrics"] in t :
                lyricsInFile = True
                lyricsFound += 1
                if os.path.isfile(file[:-4] + ".lrc"):
                    lyricsSynced += 1
                    print("   OK",sep=' ', end='',flush=True)
                    """
                    newLyricsEmbded=""
                    with open(file[:-4] + ".lrc") as f:
                        lyrics2 = f.read().splitlines()[1:]
                        for lyric in lyrics2:
                            newLyricsEmbded=newLyricsEmbded+lyric[10:]+"\n"
                        if ".mp3" in file:
                            tags[tagDict["completeLyrics"]] = USLT(lang='eng', text=newLyricsEmbded)
                        elif ".m4a" in file:
                            tags[tagDict["completeLyrics"]] = newLyricsEmbded
                    """
                elif syncEnabled :
                    createSyncedLyricsFile(enhanceLyrics(lyrics), file)
                break
        if not lyricsInFile or searchAllLyrics:
            if searchEnabled:
                if file not in verified:
                    if tagDict["artist"] in tags:
                        lyrics = searchlyrics(tag(tags, tagDict["title"]), tag(tags, tagDict["artist"]), album)
                    if tagDict["albArtist"] in tags and ('lyrics' not in locals() or lyrics is None):
                        lyrics = searchlyrics(tag(tags, tagDict["title"]), tag(tags, tagDict["albArtist"]), album)
                    if 'lyrics' in locals() and lyrics is not None:
                        betterLyrics = enhanceLyrics(lyrics)
                        """pour avoir des lyrics pas degueux, peut être encode marche mieux"""
                        f = open("tempSync.txt", "w+")
                        f.write(betterLyrics)
                        f.close()
                        with open("tempSync.txt") as f2:
                            listLyrics = f2.read()
                        
                        if ".mp3" in file:
                            tags[tagDict["completeLyrics"]] = USLT(lang='eng', text=listLyrics)
                        elif ".m4a" in file:
                            tags[tagDict["completeLyrics"]] = listLyrics
                        newLyrics += 1
                        print("   Lyrics Found   ", sep=' ', end='', flush=True)
                        """
                        verified.append(file)
                        with open(MUSIC_FOLDER+'/verifList.txt', "a") as f:
                            f.write(file +"\n")
                        """
                        if syncEnabled:
                            createSyncedLyricsFile(betterLyrics, file)
                    else:
                        print("   Not Found",sep=' ', end='',flush=True)
                        verified.append(file)
                        with open(MUSIC_FOLDER+'/verifList.txt', "a") as f:
                            f.write(file +"\n")
                else :
                    print("   Already Searched", sep=' ', end='', flush=True)
            else:
                print("   Internet Search disabled", sep=' ', end='', flush=True)
    else:
        print("   Error:No Title", sep=' ', end='', flush=True)
        errors += 1
    """on reencode les titre (samsung player n'aime que uft8)"""
    if tagDict["title"] in tags:
        if ".mp3" in file:
            tags[tagDict["title"]] = TIT2(encoding=3, text=tag(tags, tagDict["title"]))
        elif ".m4a" in file:
            tags[tagDict["title"]] = tag(tags, tagDict["title"])
    tags.save(file)

def findLyricsFile(file):
    if os.path.isdir(file):
        list = os.listdir(file)
        for element in list:
            findLyricsFile(file + "/" + element)
    else:
        if ".mp3" in file or ".m4a" in file:
            if ".mp3" in file:
                tags = ID3(file)
                completeTags(tags, file)
            elif ".m4a" in file:
                tags = MP4(file).tags
                completeTags(tags, file)

def tag(tags, label):
    if type(tags).__name__ == "ID3":
        return str(tags[label].text)[2:-2]
    elif type(tags).__name__ == "MP4Tags":
        return str(tags[label])[2:-2]
    return None

def searchlyrics(title, artist, album):
    #Filter name music
    new_title = title
    delete_char = False
    for k in range(len(title) - 1, 0, -1):
        if title[k] in [')', ']']:
            delete_char = True
        if delete_char:
            new_title = new_title[:k] + new_title[(k + 1):]
        if title[k] in ['(', '[']:
            delete_char = False
    remote_song_info = getSongInfo(new_title, artist, artist)
    if not remote_song_info:
        remote_song_info = getSongInfo(new_title, artist, album)
    if not remote_song_info:
        remote_song_info = getSongInfo(new_title, artist, "")
    # Extract lyrics from URL if song was found
    if remote_song_info:
        song_url = remote_song_info['result']['url']
        lyrics = scrap_song_url(song_url)
        if lyrics != SEARCH_FAIL:
            return lyrics
    return None

countfiles(MUSIC_FOLDER)
findLyricsFile(MUSIC_FOLDER)
print("\nTotal Music found    :     " + str(totalFiles))
print("Total old Lyrics     :     " + str(lyricsFound))
print("Total new Lyrics     :     " + str(newLyrics))
print("Total lyrics synced  :     " + str(lyricsSynced))
print("Total errors         :     " + str(errors))

