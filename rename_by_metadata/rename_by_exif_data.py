from pathlib import Path
from argparse import ArgumentParser
import exifread # https://pypi.org/project/ExifRead/
import json
import mimetypes
import os
import re
import subprocess

parser = ArgumentParser()

parser.add_argument("-e", "--execute", action="store_true")
parser.add_argument("-s", "--suffixes", default="jpg,jpeg,nef,NEF,mp4,avi,mov")
parser.add_argument("-f", "--file")

args = parser.parse_args()




class MediaFileRenamer:
    def __init__(self, cliArgs):
        self.cliArgs = cliArgs

    def renameFile(self, fileInfo):
        metaData = self.extractMetaData(fileInfo)
        comps = self.prepareDateString(metaData)
        renameCommand = self.makeRenameCommand(*comps, fileInfo.stem, fileInfo.suffix)
        print(renameCommand)
        if args.execute:
            os.system(renameCommand)

    def makeRenameCommand(self, *comps):
        return self.__class__.makeRenameCommand(*comps)

    @staticmethod
    def makeRenameCommand(year, month, day, hour, minute, second, origName, origExtension):
        return f"move {origName}{origExtension} {year}{month}{day}_{hour}{minute}{second}-{origName}{origExtension}"

    @staticmethod
    def fileType(path):
        mime, _ = mimetypes.guess_type(path)
        if mime:
            if mime.startswith("image/"):
                return "image"
            if mime.startswith("video/"):
                return "video"
        return "unknown"


class VideoFileRenamer(MediaFileRenamer):
    datePattern = "(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    timePattern = "(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    dateTimePatter = f"{datePattern}[T ]{timePattern}"
    dateTimeRegex = re.compile(rf"{dateTimePatter}")

    def getMetadataVideo(path):
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            # "-show_streams",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)


    def extractMetaData(self, fileInfo):
        # print("VideoFileRenamer.extractMetaData")
        return self.__class__.getMetadataVideo(fileInfo.name)

    def prepareDateString(self, metaData):
        # print("VideoFileRenamer.prepareDateString")
        datetimeSrc = metaData["format"]["tags"]["creation_time"]

        for m in re.finditer(self.__class__.dateTimeRegex, datetimeSrc):
            return (m["year"], m["month"], m["day"],
                    m["hour"], m["minute"], m["second"])

        raise Exception(f"VideoFileRenamer - no date/time recognized in {datetimeSrc}")



class ImageFileRenamer(MediaFileRenamer):
    dataPattern = "(?P<year>[0-9]{4}):(?P<month>[0-9]{2}):(?P<day>[0-9]{2})"
    timePattern = "(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    regex = re.compile(rf"{dataPattern} {timePattern}")


    def extractMetaData(self, fileInfo):
        # print("ImageFileRenamer.extractMetaData")
        with open(fileInfo, 'rb') as imageFile:
            exifData = exifread.process_file(imageFile, extract_thumbnail=False)
            if len(exifData) == 0:
                raise Exception(f"ImageFileRenamer.extractMetaData - rem No exif data in {fileInfo.name}")

        return exifData


    def prepareDateString(self, metaData):
        # print(f"ImageFileRenamer.prepareDateString - {metaData}")

        if "Image DateTime" in metaData:
            datetime = f'{metaData["Image DateTime"]}'
        elif "EXIF DateTimeOriginal" in metaData:
            datetime = f'{metaData["EXIF DateTimeOriginal"]}'

        datetime_digitized = f'{metaData["EXIF DateTimeDigitized"]}'

        # print(f"datetime          : {myImage.datetime_digitized}")
        # print(f"datetime_digitized: {myImage.datetime_digitized}")
        # print(f"datetime_original : {myImage.datetime_original}")

        datetimeSrc = datetime
        if datetime != datetime_digitized:
            older = datetime if datetime < datetime_digitized else datetime_digitized
            datetimeSrc = older
            print("[WARNING]")
            print(f"    datetime          : '{datetime}' {"*" if older==datetime else ""}")
            print(f"    datetime_digitized: '{datetime_digitized}' {"*" if older==datetime_digitized else ""}")
            print(f"                taking: *")

        for m in re.finditer(self.__class__.regex, datetimeSrc):
            return (m["year"], m["month"], m["day"],
                    m["hour"], m["minute"], m["second"])

        raise Exception(f"ImageFileRenamer.prepareDateString - no date/time recognized in {datetimeSrc}")



suffixes = args.suffixes.replace(',', '|')
if args.file is None:
    regex = re.compile(rf".*\.({suffixes})$", re.IGNORECASE)
else:
    regex = re.compile(rf"{args.file}")

vren = VideoFileRenamer(args)
iren = ImageFileRenamer(args)

for fileInfo in Path(".").iterdir():

    if regex.match(fileInfo.name):

        try:
            if MediaFileRenamer.fileType(fileInfo.name) == 'video':
                vren.renameFile(fileInfo)

            elif MediaFileRenamer.fileType(fileInfo.name) == 'image':
                iren.renameFile(fileInfo)

        except Exception as e:
            print(f"[WARNING] - {fileInfo.name} - {type(e).__name__}: {e}")
            continue

