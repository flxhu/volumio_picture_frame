#! /usr/bin/python

import os
import subprocess
import threading
import time
import pygame
import signal
import shlex
import socket
import random
from PIL import Image, ExifTags
from collections import deque

SHOW_AFTER_SECS=60
NEXT_IMAGE_AFTER_SECS=20
IMAGE_DIR="/home/volumio/Wallpaper/"
EXTENSIONS=['.jpg', '.jpeg', '.png']
MPD_ENDPOINT=("127.0.0.1", 6600)

class ActivityDetector(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.daemon = True
    self.last_activity = 0

  def run(self):
    f = open("/dev/input/event0", "r")
    while True:
      f.read(1)
      self.last_activity = time.time()

def get_mpd_status():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    s.connect(MPD_ENDPOINT)
    s.recv(100)  # read version banner
    s.send("status\n")
    status = s.recv(1000)
    return "state: play" in status
  except Exception as e:
    print s, e
  finally:
    s.close()

def get_next_image():
  dirs = deque()
  dirs.append(IMAGE_DIR)
  found_files = []
  while dirs:
    current_dir = dirs.pop()
    for root, subdirs, files in os.walk(current_dir):
      for subdir in subdirs:
         dirs.append(os.path.join(root, subdir))
      for filename in files:
        if os.path.splitext(filename)[1].lower() in EXTENSIONS:
          found_files.append(os.path.join(root, filename))
  file_no = random.randint(0, len(found_files) - 1)
  print "Found", len(found_files), "files, returning no", file_no
  return found_files[file_no]

def get_orientation(filename):
  """
  :return: 3 180deg, 6 270deg, 8 90deg
  """
  image=None
  try:
    image=Image.open(filename)
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation]=='Orientation':
            break
    exif=dict(image._getexif().items())
    if exif[orientation] == 3:
      return 180
    if exif[orientation] == 6:
      return 270
    if exif[orientation] == 8:
      return 90
    return 0
  except (AttributeError, KeyError, IndexError):
    return None
  finally:
    if image:
      image.close()

def display_next_image():
  filename = get_next_image()
  angle = get_orientation(filename)
  print filename, angle
  screen_width = pygame.display.Info().current_w 
  screen_height = pygame.display.Info().current_h
  picture = pygame.image.load(filename)
  if angle > 0:
    picture = pygame.transform.rotate(picture, angle)

  pic_width = picture.get_width()
  pic_height = picture.get_height()
  width = screen_width
  height = screen_width * pic_height / pic_width

  if height > screen_height:
    width = width * screen_height / height
    height = screen_height

  picture = pygame.transform.smoothscale(picture, (width, height))

  position = ((screen_width - width) / 2, (screen_height - height) / 2)

  screen.fill((0, 0, 0))
  screen.blit(picture, position) 
  pygame.display.flip() 

if __name__ == "__main__":
  pygame.init()
  os.putenv('SDL_VIDEO_DRIVER', 'directfb')
  pygame.display.init()
  pygame.mouse.set_visible(False)
  width = pygame.display.Info().current_w 
  height = pygame.display.Info().current_h
  screen = pygame.display.set_mode((width, height))

  a = ActivityDetector()
  a.start()

  last_image_switch_secs = time.time()
  last_mpd_activity = time.time()
  while True:
    time.sleep(1)

    now = time.time()
    idle_for_secs = min(now - a.last_activity, now - last_mpd_activity)

    if idle_for_secs < SHOW_AFTER_SECS:
      continue

    mpd_is_playing = get_mpd_status()
    if mpd_is_playing:
      last_mpd_activity = time.time()
      print "MPD is playing"
      continue   

    if now - last_image_switch_secs > NEXT_IMAGE_AFTER_SECS:
      last_image_switch_secs = now
      display_next_image()
