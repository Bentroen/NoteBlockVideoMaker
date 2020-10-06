#import moviepy.editor as mpy
import hitfilm
import json
import os
import pynbs
import xml.etree.ElementTree as ET
import uuid


INPUT = "input.nbs"
OUTPUT = "output.mp4"
TRACK = "track.mp3"
WIDTH = 1920
HEIGHT = 1080

DELAY = 0.2


def seconds_to_frames(s, fps=60):
	return int(round(s * 60))

def frames_to_seconds(s, fps=60):
	return s / 60

def setup_clip(filename, name):
	asset = project.add_media(file, name)
	track_id = project.add_track(name=name, type='video')
	return asset, track_id

def enforce_section_time(start, asset_start, duration, min_time, max_time):
	if start < min_time:
		start = min_time
		asset_start += (min_time - start)
		duration -= (min_time - start)

	if start + duration >= max_time:
		end = max_time - start
	else:
		end = duration
		
	return start, asset_start, end

with open("settings.json") as f:
	config = json.load(f)
	
song = pynbs.read(INPUT)
length = song.header.song_length / song.header.tempo + 1


'''
project = hitfilm.Project()
asset_id = project.add_media("clips/drums/crash.mp4", "Crash")
track = project.add_track("Wood Click")
clip = hitfilm.Clip(track_id, asset_id, start=240, end=280, asset_start=0, posx=0, posy=0, scalex=0, scaley=0, speed=1)
project.add_clip(clip, track_id, asset_id)

project.save("test.hfp")
'''

project = hitfilm.Project()

# Prepare clips for use in the video
clips = {}
for name, clip in config["clips"].items():
	print("Loading clip {}".format(name))
	path = clip["source"]
	instrument = clip["instrument"]
	start = clip.get("start", 0)
	attack = clip.get("attack", 0)
	end = clip.get("end")
	
	file = os.path.join("clips", path)
	asset, track_id = setup_clip(file, name)
	if not end:
		end = asset.duration
	clips[name] = (instrument, start, attack, end, asset, track_id)
	

# Prepare tracks for use in the video
tracks = {}
for name, track in config["tracks"].items():
	path = track["source"]
	file = os.path.join("clips", path)
	instrument = track["instrument"]
	segments = []
	asset, track_id = setup_clip(file, name)
	for i, section in enumerate(track["segments"]):
		print("Loading section {} of track {}".format(i+1, name))
		start = section.get("start", 0)
		end = section.get("end")
		if not end:
			end = asset.duration
		segments.append((start, end))
	tracks[name] = [instrument, 0, asset, track_id, segments]


# Place clips into final video for each section
video = []
last_tick = 0

for section in config["sections"]:

	print("Starting render of section at tick {}".format(start))
	
	section_start = section["start"]
	section_end = section["end"]
	last_tick = section_end
	grid_size = section["grid_size"]
	
	if section_start > song.header.song_length - 1:
		break
	
	cellw = WIDTH / grid_size
	cellh = HEIGHT / grid_size
	
	for item in section["clips"]:
		
		# Figure out if a clip or a track
		name = item["name"]
		if name in clips:
			ins, inpoint, attack, outpoint, asset, track_id = clips[name]
			type = "clip"
		elif name in tracks:
			ins, current_segment, asset, track_id, segments = tracks[name]
			# loop back to the first segment when running out
			if current_segment > len(segments) - 1:
				current_segment = 0
			inpoint, outpoint = segments[current_segment]
			type = "track"
			tracks[name][1] = current_segment + 1 # increase next segment to be used
		else:
			print("Skipping undefined clip: {}".format(name))
			continue
		
		# Calculate this clip's size and position on the frame
		size = item["size"]
		pos = item["pos"]
		
		x = pos[0] * cellw
		y = pos[1] * cellh
		w = int(cellw * size)
		h = int(cellh * size)
		
		min_time = section_start / song.header.tempo
		max_time = section_end / song.header.tempo
		
		# Get the clip's appearance times from the notes in song
		chunk = filter(lambda x: x.tick >= section_start and x.tick < section_end, song.notes)
		dirty_notes = sorted(filter(lambda y: y.instrument == ins, chunk), key=lambda z: z.tick)
		previous_tick = -1
		notes = dirty_notes
		notes = []
		# remove repeated instruments in the same tick
		for note in dirty_notes:
			if note.tick > previous_tick:
				notes.append(note)
			previous_tick = note.tick
				
		times = []
		
		if type == "clip":
			last_attack = -1
			for i, note in enumerate(notes):
				tick = note.tick
				
				# set clip to start exactly at the attack point
				start = tick / song.header.tempo
				asset_start = attack
				duration = outpoint - attack
				
				print(last_attack, start)
				time_from_last_attack = start - last_attack
				attack_time = attack - inpoint

				# Use 1/4 of the last clip's "release" for the start of
				# the current clip, the time from the start to the attack
				# of the clip, or 1/4 of a second (whatever is smaller).
				advance = min(max(time_from_last_attack / 4, 0), attack_time, 0.25)
				
				choices = [max(time_from_last_attack / 4, 0), attack_time, 0.25]
				print("time from last: {} / attack time: {} / max: {}".format(*choices))
				print("picking: {}".format(min(choices)))
				
				# move clip forward by the calculated start position
				asset_start -= advance
				start -= advance
				duration += advance
				
				# prevent clip from exceeding section time
				start, asset_start, end = enforce_section_time(start, asset_start, duration, min_time, max_time)
				
				times.append((start, asset_start, end))
				last_attack = start + attack_time
				
		elif type == "track":
			try:
				note = notes[0]
			except IndexError as e:
				raise ValueError("Couldn't add track '{}' on section at tick {}: No note blocks with instrument {} were found".format(name, section_start, ins)) from None
			
			tick = note.tick
			
			start = tick / song.header.tempo
			asset_start = inpoint
			duration = outpoint - inpoint
			start, asset_start, end = enforce_section_time(start, asset_start, duration, min_time, max_time)
			times.append((start, asset_start, end))
		
		# Add clip to the video
		for start, asset_start, end in times:
			clip = hitfilm.Clip(track_id, asset, start, duration=end)
			clip.set_position(x, y)
			clip.set_size(w, h)
			clip.subclip(asset_start)
			
			project.add_clip(clip)
			
			# TWO OPTIONS HERE: 1) Either make Clip completely independent of the project,
			# and only generate a UUID on project.add_clip(), or require a new instance of
			# Clip everytime a new clip is added.

			print("Rendering {} '{}' at {:.1f} seconds".format(type, name, start))


project.save("output.hfp")
