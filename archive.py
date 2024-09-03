from datetime import datetime, timedelta
import os

IMAGEPATH = './images'
ARCHIVEPATH = os.path.join(IMAGEPATH, 'archive')
AVAILABLEWEEKS = 4

def get_first_day_of_week(date: datetime, weeksBackInTime: int = 0):
    date = date - timedelta(weeksBackInTime * 7)
    firstDay = date - timedelta((date.weekday() + 1) % 7)
    return firstDay

def get_archive_path(year: str, channel: str, username: str):
    path = os.path.join(ARCHIVEPATH, year, channel, username)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_next_image_name(path: str, username: str):
    filecount = len(os.listdir(path))
    return f'{username}-{str(filecount)}'

for root, dirs, files in os.walk(IMAGEPATH):
    today = datetime.today()
    keepWeeks = [get_first_day_of_week(today, x).strftime('%Y-%m-%d') for x in range(AVAILABLEWEEKS)]

    if files:
        split = root.replace('\\', '/').split('/')
        year = split[2][:4]
        channel = split[3]
        username = split[4]
        path = get_archive_path(year, channel, username)
        for file in files:
            imageName = get_next_image_name(path, username)
            extension = file[file.rfind('.') + 1:]
            os.rename(os.path.join(root, file), os.path.join(path, f'{imageName}.{extension}'))
        os.rmdir(root)
    for week in keepWeeks:
        if week in dirs:
            dirs.remove(week) # ignore folders within the range of weeks to keep available
    if 'archive' in dirs:
        dirs.remove('archive') # ignore the archive directory

# Loop back through the folders and clear out empty ones
for root, dirs, files in os.walk(IMAGEPATH, topdown=False):
    if not dirs and not files:
        print('Removing path', root)
        os.removedirs(root)